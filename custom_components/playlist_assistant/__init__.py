"""Thin Home Assistant bridge: services, native schedules and entities only."""
from __future__ import annotations
from .const import DOMAIN
from .native import NativeSchedule

async def async_setup_entry(hass, entry):
    bridge = hass.data[DOMAIN]["bridge"]  # deployment supplies the private add-on bridge
    async def sync(_now=None): await bridge.execute("sync")
    async def run(_now=None): await bridge.execute("run")
    schedule = NativeSchedule(
        lambda interval, callback: hass.helpers.event.async_track_time_interval(callback, interval),
        lambda hour, minute, callback: hass.helpers.event.async_track_time_change(callback, hour=hour, minute=minute),
        sync, run,
    )
    async def configure():
        values = await bridge.schedule()
        schedule.configure(values["history_interval_minutes"], values["daily_enabled"], values["daily_time"])
    await configure()
    hass.data[DOMAIN][entry.entry_id] = {"bridge": bridge, "schedule": schedule, "configure": configure}
    async def handler(call):
        await bridge.execute(call.service)
    for action in ("sync", "preview", "publish", "run"):
        hass.services.async_register(DOMAIN, action, handler)
    return True

async def async_unload_entry(hass, entry):
    data = hass.data[DOMAIN].pop(entry.entry_id)
    data["schedule"].stop()
    for action in ("sync", "preview", "publish", "run"):
        hass.services.async_remove(DOMAIN, action)
    return True
