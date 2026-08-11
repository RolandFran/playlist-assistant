"""Push-updated bridge state for Playlist Assistant entities."""
from __future__ import annotations
import logging
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .spotify import SpotifyApi, SpotifyAuthError, SpotifyConnectionError

class PlaylistAssistantCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, bridge=None, spotify: SpotifyApi | None = None, entry=None):
        self._hass = hass
        self.bridge = bridge
        self.spotify = spotify
        self.entry = entry
        super().__init__(hass, logger=logging.getLogger(__name__), name="playlist_assistant", update_method=self._async_update_data)

    async def _async_update_data(self):
        """Expose only the non-sensitive result of Spotify's /v1/me check."""
        data = await self.bridge.state() if self.bridge else {"preview": {}, "schedule": {}, "jobs": {}}
        if not self.spotify:
            return data
        try:
            profile = await self.spotify.async_get_profile()
        except SpotifyAuthError:
            if self.entry is not None:
                self.entry.async_start_reauth(self._hass)
            data["spotify"] = {"state": "reauth_required"}
        except SpotifyConnectionError:
            data["spotify"] = {"state": "not_connected"}
        else:
            data["spotify"] = {"state": "connected", **profile}
        return data

    async def async_execute(self, action):
        if self.bridge is None:
            raise RuntimeError("Playlist actions are not part of the Spotify connection proof")
        data = await self.bridge.execute(action)
        self.async_set_updated_data(data)
        return data

    async def async_schedule_changed(self):
        # An Ingress save provides the new cadence in the HA event, but a
        # bridge state refresh keeps all three entities coherent too.
        await self.async_request_refresh()
