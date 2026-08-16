"""Temporary, credential-safe Spotify playlist-details diagnostic."""
from __future__ import annotations

import logging
import re
import time
from typing import Any

from aiohttp import ClientError
from homeassistant.exceptions import OAuth2TokenRequestReauthError

from .spotify import SPOTIFY_API_URL, SpotifyApi, SpotifyAuthError, SpotifyConnectionError, SpotifyRequestError, _safe_error_detail


LOGGER = logging.getLogger(__name__)
_SAFE_HEADERS = ("Content-Type", "Accept", "Accept-Language", "User-Agent")
_SECRET_PATTERN = re.compile(r"(?i)(access[_-]?token|refresh[_-]?token|authorization|client[_-]?secret|code)=?[^\s,;&]*")


def _response_metadata(response: Any) -> dict[str, Any]:
    """Extract only request metadata that is safe for diagnostic logs."""
    request_headers = getattr(getattr(response, "request_info", None), "headers", {})
    headers = {name: request_headers[name] for name in _SAFE_HEADERS if name in request_headers}
    history = [
        {"status": item.status, "path": getattr(getattr(item, "url", None), "path", None)}
        for item in getattr(response, "history", ())
    ]
    return {"status": response.status, "headers": headers, "redirects": history}


def _log_result(variant: str, path: str, started: float, metadata: dict[str, Any], detail: str | None = None) -> None:
    """Log the bounded, non-credential result of one diagnostic request."""
    LOGGER.info(
        "playlist_details_diagnostic variant=%s method=PUT path=%s status=%s elapsed_ms=%d detail=%s outgoing_headers=%s redirects=%s",
        variant,
        path,
        metadata.get("status"),
        round((time.perf_counter() - started) * 1000),
        safe_diagnostic_detail(detail),
        metadata.get("headers", {}),
        metadata.get("redirects", []),
    )


def safe_diagnostic_detail(detail: str | None) -> str:
    """Redact credential-shaped values before exposing a diagnostic error."""
    return _SECRET_PATTERN.sub(r"\1=[REDACTED]", detail or "-")


async def _async_direct_request(session, path: str, payload: dict[str, Any], observe) -> dict:
    """Make the OAuth-session-only branch of the temporary comparison."""
    try:
        response = await session.async_request("PUT", SPOTIFY_API_URL + path, json=payload)
        async with response:
            observe(response)
            if response.status == 401:
                raise SpotifyAuthError
            if response.status >= 400:
                detail = await _safe_error_detail(response)
                raise SpotifyRequestError(response.status, detail)
            response.raise_for_status()
            return {}
    except (SpotifyAuthError, SpotifyRequestError, OAuth2TokenRequestReauthError):
        raise
    except (ClientError, TimeoutError, ValueError) as err:
        raise SpotifyConnectionError from err


async def async_diagnose_playlist_details(session, *, playlist_id: str, name: str, public: bool, variant: str) -> dict:
    """Compare direct HA OAuth with the integration SpotifyApi, without proxies.

    This is intentionally temporary instrumentation.  It never logs OAuth
    material and never invokes the HA proxy endpoint or the add-on client.
    """
    if variant not in {"direct_oauth", "spotify_api"}:
        raise ValueError("variant must be direct_oauth or spotify_api")
    path = f"/playlists/{playlist_id}"
    payload = {"name": name, "public": public}
    metadata: dict[str, Any] = {"status": None, "headers": {}, "redirects": []}
    started = time.perf_counter()

    def observe(response) -> None:
        metadata.update(_response_metadata(response))

    try:
        if variant == "direct_oauth":
            result = await _async_direct_request(session, path, payload, observe)
        else:
            result = await SpotifyApi(session).async_request("PUT", path, json=payload, response_observer=observe)
    except SpotifyRequestError as error:
        _log_result(variant, path, started, metadata, error.detail)
        raise
    except SpotifyAuthError:
        _log_result(variant, path, started, metadata, "Spotify authorization was rejected.")
        raise
    except (SpotifyConnectionError, OAuth2TokenRequestReauthError):
        _log_result(variant, path, started, metadata, "Spotify connection failed.")
        raise
    _log_result(variant, path, started, metadata)
    return result
