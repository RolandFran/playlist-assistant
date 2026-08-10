"""Thin HA integration: private bridge, HA services, schedules and entities."""
from __future__ import annotations
from .const import DOMAIN, PLATFORMS
from .native import NativeSchedule

async def async_setup_entry(hass, entry):
    from homeassistant.components import persistent_notification
    from homeassistant.helpers.aiohttp_client import async_get_clientsession
    from homeassistant.helpers.event import async_track_time_change, async_track_time_interval
    from .bridge import AddonBridge
    bridge = AddonBridge(async_get_clientsession(hass), entry.data["url"], entry.data["bridge_token"])
    async def execute(action):
        try: return await bridge.execute(action)
        except Exception as error:
            persistent_notification.async_create(hass, f"Playlist Assistant: {error}", title="Playlist Assistant")
            raise
    async def sync(_now=None): return await execute("sync")
    async def run(_now=None): return await execute("run")
    schedule = NativeSchedule(lambda interval, callback: async_track_time_interval(hass, callback, interval),
        lambda hour, minute, callback: async_track_time_change(hass, callback, hour=hour, minute=minute), sync, run)
    async def configure(values=None):
        values = values or await bridge.schedule()
        schedule.configure(values["history_interval_minutes"], values["daily_enabled"], values["daily_time"])
    await bridge.state(); await configure()
    async def schedule_changed(event): await configure(event.data)
    unsubscribe_event = hass.bus.async_listen("playlist_assistant_schedule_changed", schedule_changed)
    async def handler(call): await execute(call.service)
    for action in ("sync", "preview", "publish", "run"): hass.services.async_register(DOMAIN, action, handler)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"bridge": bridge, "schedule": schedule, "event": unsubscribe_event}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass, entry):
    data = hass.data[DOMAIN].pop(entry.entry_id)
    data["schedule"].stop(); data["event"]()
    for action in ("sync", "preview", "publish", "run"): hass.services.async_remove(DOMAIN, action)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
