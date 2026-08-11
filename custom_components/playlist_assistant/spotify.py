"""Small, HA-owned Spotify API boundary for the connection proof."""
from __future__ import annotations

from aiohttp import ClientError
from homeassistant.exceptions import OAuth2TokenRequestReauthError
from homeassistant.helpers.config_entry_oauth2_flow import OAuth2Session

from .const import SPOTIFY_API_ME_URL


class SpotifyAuthError(Exception):
    """Spotify rejected the current authorization."""


class SpotifyConnectionError(Exception):
    """Spotify could not be reached or returned an invalid response."""


class SpotifyApi:
    """Fetch only the profile needed to prove the HA-side connection."""

    def __init__(self, session: OAuth2Session) -> None:
        self._session = session

    async def async_get_profile(self) -> dict[str, str]:
        """Call Spotify's /v1/me endpoint without logging credential material."""
        try:
            response = await self._session.async_request("GET", SPOTIFY_API_ME_URL)
            async with response:
                if response.status in (401, 403):
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
