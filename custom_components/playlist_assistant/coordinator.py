"""Push-updated bridge state for Playlist Assistant entities."""
from __future__ import annotations
import logging
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

class PlaylistAssistantCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, bridge):
        self.bridge = bridge
        super().__init__(hass, logger=logging.getLogger(__name__), name="playlist_assistant", update_method=bridge.state)

    async def async_execute(self, action):
        data = await self.bridge.execute(action)
        self.async_set_updated_data(data)
        return data

    async def async_schedule_changed(self):
        # An Ingress save provides the new cadence in the HA event, but a
        # bridge state refresh keeps all three entities coherent too.
        await self.async_request_refresh()
