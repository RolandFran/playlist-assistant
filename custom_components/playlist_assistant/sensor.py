from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([PlaylistStatus(hass, entry), PlaylistConnection(hass, entry)])

class _BridgeEntity(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    def __init__(self, hass, entry): super().__init__(hass.data[DOMAIN][entry.entry_id]["coordinator"])

class PlaylistStatus(_BridgeEntity):
    _attr_name = "Playlist Assistant status"
    _attr_unique_id = "playlist_assistant_status"
    @property
    def native_value(self): return self.coordinator.data.get("preview", {}).get("state", "idle")

class PlaylistConnection(_BridgeEntity):
    _attr_name = "Playlist Assistant connection"
    _attr_unique_id = "playlist_assistant_connection"
    @property
    def native_value(self): return self.coordinator.data.get("spotify", {}).get("state", "not_connected")
