"""Narrow Supervisor-authenticated boundary from the add-on to HA OAuth."""
from __future__ import annotations

import logging
import re
from time import perf_counter
from uuid import uuid4

from homeassistant.components.http import HomeAssistantView
from .const import DOMAIN
from .spotify import SpotifyApi, SpotifyAuthError, SpotifyConnectionError, SpotifyRequestError

LOGGER = logging.getLogger(__name__)
_SENSITIVE_JSON_FIELDS = frozenset({
    "access_token",
    "authorization",
    "client_secret",
    "oauth_secret",
    "refresh_token",
    "supervisor_token",
})

_OPERATIONS = {
    "recently_played": ("GET", "/me/player/recently-played"), "user_playlists": ("GET", "/me/playlists"),
    "playlist": ("GET", "/playlists/{playlist_id}"), "playlist_items": ("GET", "/playlists/{playlist_id}/items"), "current_user": ("GET", "/me"),
    "create_playlist": ("POST", "/me/playlists"), "playlist_details": ("PUT", "/playlists/{playlist_id}"),
    "replace_items": ("PUT", "/playlists/{playlist_id}/items"), "append_items": ("POST", "/playlists/{playlist_id}/items"),
}


def _safe_json_metadata(payload):
    """Return diagnostic JSON structure without logging arbitrary payload values."""
    if payload is None:
        return {"present": False}
    if not isinstance(payload, dict):
        return {"present": True, "type": type(payload).__name__}

    safe_keys = [str(key) for key in payload if str(key).lower() not in _SENSITIVE_JSON_FIELDS]
    metadata = {"present": True, "keys": sorted(safe_keys)}
    if isinstance(payload.get("uris"), list):
        metadata["item_count"] = len(payload["uris"])
    for field in ("name", "public"):
        value = payload.get(field)
        if isinstance(value, (str, bool)):
            metadata[field] = value
    return metadata


def _safe_error_detail(detail):
    """Remove credential values if an upstream error unexpectedly echoes them."""
    return re.sub(
        r"(?i)(access_token|authorization|client_secret|oauth_secret|refresh_token|supervisor_token)"
        r"(\s*[:=]\s*)([^\s,}]+)",
        r"\1\2[redacted]",
        detail,
    )


class SpotifyProxyView(HomeAssistantView):
    url = "/api/playlist_assistant/spotify"
    name = "api:playlist_assistant:spotify"
    requires_auth = True
    def __init__(self, hass): self.hass = hass
    async def post(self, request):
        try:
            body = await request.json(); method, template = _OPERATIONS[body["operation"]]
            operation = body["operation"]
            path = template.format(**body.get("path", {}))
            params = body.get("params")
            payload = body.get("json")
            request_id = uuid4().hex
            started = perf_counter()
            LOGGER.debug(
                "spotify_proxy_boundary_request request_id=%s operation=%s spotify_method=%s "
                "endpoint_path=%s params_present=%s json_metadata=%s",
                request_id, operation, method, path, params is not None, _safe_json_metadata(payload),
            )
            # Reuse the authenticated session established by the integration.
            # Creating a new OAuth2Session here caused direct playlist metadata
            # requests to lose the connection that the running integration had
            # already proved usable.
            api = next(item["spotify"] for item in self.hass.data.get(DOMAIN, {}).values() if item.get("spotify"))
            result = await api.async_request(method, path, params=params, json=payload)
            LOGGER.debug(
                "spotify_proxy_boundary_success request_id=%s operation=%s duration_ms=%d success=%s",
                request_id, operation, (perf_counter() - started) * 1000, True,
            )
            return self.json(result)
        except SpotifyRequestError as error:
            LOGGER.debug(
                "spotify_proxy_boundary_request_error request_id=%s operation=%s duration_ms=%d "
                "status=%s reason=%s detail=%s",
                request_id, operation, (perf_counter() - started) * 1000,
                error.status, error.reason, _safe_error_detail(error.detail),
            )
            headers = {"Retry-After": error.retry_after} if error.retry_after else None
            payload = {"error": error.detail}
            if error.reason:
                payload["reason"] = error.reason
            return self.json(payload, status_code=error.status, headers=headers)
        except (SpotifyAuthError, SpotifyConnectionError) as error:
            LOGGER.debug(
                "spotify_proxy_boundary_connection_error request_id=%s operation=%s duration_ms=%d "
                "exception_category=%s exception_class=%s",
                request_id, operation, (perf_counter() - started) * 1000,
                "auth" if isinstance(error, SpotifyAuthError) else "connection", type(error).__name__,
            )
            return self.json({"error": "Spotify connection is unavailable."}, status_code=400)
        except (KeyError, StopIteration):
            return self.json({"error": "Spotify connection is unavailable."}, status_code=400)

def async_register_api(hass): hass.http.register_view(SpotifyProxyView(hass))
