"""Thin HA integration: private bridge, HA services, schedules and entities."""
from __future__ import annotations
from .const import DOMAIN, PLATFORMS
from .native import NativeSchedule

async def async_setup_entry(hass, entry):
    from homeassistant.components import persistent_notification
    from homeassistant.helpers.aiohttp_client import async_get_clientsession
    from homeassistant.helpers.event import async_track_time_change, async_track_time_interval
    from .bridge import AddonBridge
    from .coordinator import PlaylistAssistantCoordinator
    bridge = AddonBridge(async_get_clientsession(hass), entry.data["url"], entry.data["bridge_token"])
    coordinator = PlaylistAssistantCoordinator(hass, bridge)
    async def execute(action):
        try: return await coordinator.async_execute(action)
        except Exception as error:
            persistent_notification.async_create(hass, f"Playlist Assistant: {error}", title="Playlist Assistant")
            raise
    async def sync(_now=None): return await execute("sync")
    async def run(_now=None): return await execute("run")
    schedule = NativeSchedule(lambda interval, callback: async_track_time_interval(hass, callback, interval),
        lambda hour, minute, callback: async_track_time_change(hass, callback, hour=hour, minute=minute), sync, run)
    async def configure(values=None):
        if values is None:
            await coordinator.async_request_refresh()
            values = coordinator.data["schedule"]
        schedule.configure(values["history_interval_minutes"], values["daily_enabled"], values["daily_time"])
    await coordinator.async_config_entry_first_refresh(); await configure(coordinator.data["schedule"])
    async def schedule_changed(event):
        await configure(event.data)
        await coordinator.async_schedule_changed()
    unsubscribe_event = hass.bus.async_listen("playlist_assistant_schedule_changed", schedule_changed)
    async def handler(call): await execute(call.service)
    for action in ("sync", "preview", "publish", "run"): hass.services.async_register(DOMAIN, action, handler)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"bridge": bridge, "coordinator": coordinator, "schedule": schedule, "event": unsubscribe_event}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass, entry):
    data = hass.data[DOMAIN].pop(entry.entry_id)
    data["schedule"].stop(); data["event"]()
    for action in ("sync", "preview", "publish", "run"): hass.services.async_remove(DOMAIN, action)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
