from datetime import datetime
from homeassistant.components.binary_sensor import BinarySensorEntity
from .const import DOMAIN
from .native import history_gap

async def async_setup_entry(hass, entry, async_add_entities): async_add_entities([HistoryGap(hass, entry)])

class HistoryGap(BinarySensorEntity):
    _attr_name = "Playlist Assistant history gap"
    _attr_unique_id = "playlist_assistant_history_gap"
    _attr_has_entity_name = True
    def __init__(self, hass, entry): self._bridge = hass.data[DOMAIN][entry.entry_id]["bridge"]
    @property
    def is_on(self):
        details = self._bridge.data
        last = details.get("jobs", {}).get("history", {}).get("last_success_at")
        interval = details.get("schedule", {}).get("history_interval_minutes", 90)
        return history_gap(datetime.fromisoformat(last) if last else None, interval, datetime.now().astimezone())
