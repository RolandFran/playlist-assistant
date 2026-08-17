"""Small, HA-owned Spotify API boundary for the connection proof."""
from __future__ import annotations

from aiohttp import ClientError
from homeassistant.exceptions import OAuth2TokenRequestReauthError
from homeassistant.helpers.config_entry_oauth2_flow import OAuth2Session

from .const import SPOTIFY_API_ME_URL

SPOTIFY_API_URL = "https://api.spotify.com/v1"


class SpotifyAuthError(Exception):
    """Spotify rejected the current authorization."""


class SpotifyConnectionError(Exception):
    """Spotify could not be reached or returned an invalid response."""


class SpotifyRequestError(Exception):
    """A safe Spotify API failure suitable for the internal add-on proxy."""

    def __init__(self, status: int, detail: str, *, retry_after: str | None = None, reason: str | None = None) -> None:
        self.status = status
        self.detail = detail
        self.retry_after = retry_after
        self.reason = reason


async def _safe_error_detail(response) -> str:
    try:
        payload = await response.json()
    except (ClientError, ValueError):
        return "Spotify returned no readable error detail."
    if not isinstance(payload, dict):
        return "Spotify returned an invalid error response."
    error = payload.get("error")
    if isinstance(error, dict):
        detail = error.get("message")
    else:
        detail = error or payload.get("message")
    if not isinstance(detail, str) or not detail.strip():
        return "Spotify returned no error detail."
    return detail.strip()[:500]


class SpotifyApi:
    """Fetch only the profile needed to prove the HA-side connection."""

    def __init__(self, session: OAuth2Session) -> None:
        self._session = session

    async def async_get_profile(self) -> dict[str, str]:
        """Call Spotify's /v1/me endpoint without logging credential material."""
        try:
            response = await self._session.async_request("GET", SPOTIFY_API_ME_URL)
            async with response:
                if response.status == 401:
                    raise SpotifyAuthError
                response.raise_for_status()
                profile = await response.json()
        except (SpotifyAuthError, OAuth2TokenRequestReauthError):
            raise
        except (ClientError, TimeoutError, ValueError) as err:
            raise SpotifyConnectionError from err

        account_id = profile.get("id")
        if not isinstance(account_id, str) or not account_id:
            raise SpotifyConnectionError
        display_name = profile.get("display_name")
        return {
            "account_id": account_id,
            "display_name": display_name if isinstance(display_name, str) else account_id,
        }

    async def async_request(self, method: str, path: str, *, params=None, json=None) -> dict:
        """Perform one allow-listed Spotify Web API request with HA-owned OAuth."""
        try:
            response = await self._session.async_request(method, SPOTIFY_API_URL + path, params=params, json=json)
            async with response:
                if response.status == 401:
                    raise SpotifyAuthError
                if response.status >= 400:
                    detail = await _safe_error_detail(response)
                    raise SpotifyRequestError(
                        response.status,
                        detail,
                        retry_after=getattr(response, "headers", {}).get("Retry-After"),
                        reason="QUOTA_EXCEEDED" if "QUOTA_EXCEEDED" in detail else None,
                    )
                response.raise_for_status()
                # Spotify's playlist-write endpoints may reply with an empty
                # 200 body (as well as 204). A successful write must not be
                # misreported as a connection error just because there is no
                # JSON document to decode.
                if response.status == 204:
                    return {}
                try:
                    payload = await response.json()
                except (ClientError, ValueError):
                    return {}
                if payload is None:
                    return {}
        except (SpotifyAuthError, SpotifyRequestError, OAuth2TokenRequestReauthError):
            raise
        except (ClientError, TimeoutError, ValueError) as err:
            raise SpotifyConnectionError from err
        if not isinstance(payload, dict):
            raise SpotifyConnectionError
        return payload
