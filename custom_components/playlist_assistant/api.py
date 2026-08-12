"""Narrow Supervisor-authenticated boundary from the add-on to HA OAuth."""
from __future__ import annotations

from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers import config_entry_oauth2_flow
from .const import DOMAIN
from .spotify import SpotifyApi, SpotifyAuthError, SpotifyConnectionError

_OPERATIONS = {
    "recently_played": ("GET", "/me/player/recently-played"), "user_playlists": ("GET", "/me/playlists"),
    "playlist_items": ("GET", "/playlists/{playlist_id}/tracks"), "current_user": ("GET", "/me"),
    "create_playlist": ("POST", "/users/{user_id}/playlists"), "playlist_details": ("PUT", "/playlists/{playlist_id}/details"),
    "replace_items": ("PUT", "/playlists/{playlist_id}/tracks"), "append_items": ("POST", "/playlists/{playlist_id}/tracks"),
}

class SpotifyProxyView(HomeAssistantView):
    url = "/api/playlist_assistant/spotify"
    name = "api:playlist_assistant:spotify"
    requires_auth = True
    def __init__(self, hass): self.hass = hass
    async def post(self, request):
        try:
            body = await request.json(); method, template = _OPERATIONS[body["operation"]]
            entry = next(item["entry"] for item in self.hass.data.get(DOMAIN, {}).values() if item.get("spotify"))
            implementation = await config_entry_oauth2_flow.async_get_config_entry_implementation(self.hass, entry)
            api = SpotifyApi(config_entry_oauth2_flow.OAuth2Session(self.hass, entry, implementation))
            return self.json(await api.async_request(method, template.format(**body.get("path", {})), params=body.get("params"), json=body.get("json")))
        except (KeyError, StopIteration, SpotifyAuthError, SpotifyConnectionError):
            return self.json({"error": "Spotify connection is unavailable."}, status_code=400)

def async_register_api(hass): hass.http.register_view(SpotifyProxyView(hass))
