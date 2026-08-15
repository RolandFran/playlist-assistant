"""Narrow Supervisor-authenticated boundary from the add-on to HA OAuth."""
from __future__ import annotations

from homeassistant.components.http import HomeAssistantView
from .const import DOMAIN
from .spotify import SpotifyApi, SpotifyAuthError, SpotifyConnectionError, SpotifyRequestError

_OPERATIONS = {
    "recently_played": ("GET", "/me/player/recently-played"), "user_playlists": ("GET", "/me/playlists"),
    "playlist": ("GET", "/playlists/{playlist_id}"), "playlist_items": ("GET", "/playlists/{playlist_id}/items"), "current_user": ("GET", "/me"),
    "create_playlist": ("POST", "/me/playlists"), "playlist_details": ("PUT", "/playlists/{playlist_id}"),
    "replace_items": ("PUT", "/playlists/{playlist_id}/items"), "append_items": ("POST", "/playlists/{playlist_id}/items"),
}

class SpotifyProxyView(HomeAssistantView):
    url = "/api/playlist_assistant/spotify"
    name = "api:playlist_assistant:spotify"
    requires_auth = True
    def __init__(self, hass): self.hass = hass
    async def post(self, request):
        try:
            body = await request.json(); method, template = _OPERATIONS[body["operation"]]
            # Reuse the authenticated session established by the integration.
            # Creating a new OAuth2Session here caused direct playlist metadata
            # requests to lose the connection that the running integration had
            # already proved usable.
            api = next(item["spotify"] for item in self.hass.data.get(DOMAIN, {}).values() if item.get("spotify"))
            return self.json(await api.async_request(method, template.format(**body.get("path", {})), params=body.get("params"), json=body.get("json")))
        except SpotifyRequestError as error:
            headers = {"Retry-After": error.retry_after} if error.retry_after else None
            payload = {"error": error.detail}
            if error.reason:
                payload["reason"] = error.reason
            return self.json(payload, status_code=error.status, headers=headers)
        except (KeyError, StopIteration, SpotifyAuthError, SpotifyConnectionError):
            return self.json({"error": "Spotify connection is unavailable."}, status_code=400)

def async_register_api(hass): hass.http.register_view(SpotifyProxyView(hass))
