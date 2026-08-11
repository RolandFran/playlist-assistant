"""HA-shaped integration tests without requiring a full Core installation."""
import asyncio
import sys
import types
import unittest
from datetime import timedelta


class _Coordinator:
    def __init__(self, hass, logger, name, update_method):
        self.update_method = update_method; self.data = None; self.listeners = 0
    async def async_config_entry_first_refresh(self): self.data = await self.update_method()
    async def async_request_refresh(self): self.data = await self.update_method(); return self.data
    def async_set_updated_data(self, data): self.data = data; self.listeners += 1


class _Bridge:
    def __init__(self, *_): self.calls = []; self.version = 0
    async def state(self):
        return {"schedule": {"history_interval_minutes": 90, "daily_enabled": True, "daily_time": "04:00"}, "preview": {"state": f"state-{self.version}"}, "spotify": {"state": "connected"}}
    async def execute(self, action): self.calls.append(action); self.version += 1; return await self.state()


class _Services:
    def __init__(self): self.handlers = {}
    def async_register(self, domain, name, handler): self.handlers[(domain, name)] = handler
    def async_remove(self, domain, name): self.handlers.pop((domain, name), None)


class _Bus:
    def __init__(self): self.listeners = {}
    def async_listen(self, event, callback):
        self.listeners[event] = callback
        return lambda: self.listeners.pop(event, None)


class _Entries:
    def __init__(self): self.forwarded = []; self.unloaded = []
    async def async_forward_entry_setups(self, entry, platforms): self.forwarded.extend(platforms)
    async def async_unload_platforms(self, entry, platforms): self.unloaded.extend(platforms); return True


class _Hass:
    def __init__(self): self.data = {}; self.services = _Services(); self.bus = _Bus(); self.config_entries = _Entries(); self.tracks = []


def _install_ha_stubs():
    homeassistant = types.ModuleType("homeassistant"); helpers = types.ModuleType("homeassistant.helpers")
    exceptions = types.ModuleType("homeassistant.exceptions")
    exceptions.OAuth2TokenRequestReauthError = type("OAuth2TokenRequestReauthError", (Exception,), {})
    components = types.ModuleType("homeassistant.components"); notification = types.SimpleNamespace(async_create=lambda *args, **kwargs: None)
    aiohttp = types.ModuleType("homeassistant.helpers.aiohttp_client"); aiohttp.async_get_clientsession = lambda hass: object()
    event = types.ModuleType("homeassistant.helpers.event")
    def interval(hass, callback, value): hass.tracks.append(("interval", value, callback)); return lambda: hass.tracks.remove(("interval", value, callback))
    def daily(hass, callback, hour, minute): hass.tracks.append(("daily", hour, minute, callback)); return lambda: hass.tracks.remove(("daily", hour, minute, callback))
    event.async_track_time_interval, event.async_track_time_change = interval, daily
    update = types.ModuleType("homeassistant.helpers.update_coordinator"); update.DataUpdateCoordinator = _Coordinator
    oauth2 = types.ModuleType("homeassistant.helpers.config_entry_oauth2_flow")
    oauth2.OAuth2Session = object
    components.persistent_notification = notification
    sys.modules.update({"homeassistant": homeassistant, "homeassistant.exceptions": exceptions, "homeassistant.helpers": helpers, "homeassistant.components": components,
        "homeassistant.helpers.aiohttp_client": aiohttp, "homeassistant.helpers.event": event, "homeassistant.helpers.update_coordinator": update,
        "homeassistant.helpers.config_entry_oauth2_flow": oauth2})


class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        _install_ha_stubs()
        import custom_components.playlist_assistant.bridge as bridge
        bridge.AddonBridge = _Bridge
        import custom_components.playlist_assistant as integration
        cls.integration = integration

    async def asyncSetUp(self):
        self.hass = _Hass(); self.entry = types.SimpleNamespace(entry_id="entry", data={"url": "http://playlist_assistant:8098", "bridge_token": "x"})
        await self.integration.async_setup_entry(self.hass, self.entry)
        self.data = self.hass.data["playlist_assistant"]["entry"]

    async def test_setup_actions_and_coordinator_refresh(self):
        self.assertEqual(self.data["coordinator"].data["preview"]["state"], "state-0")
        for action in ("sync", "preview", "publish", "run"):
            await self.hass.services.handlers[("playlist_assistant", action)](types.SimpleNamespace(service=action))
        self.assertEqual(self.data["bridge"].calls, ["sync", "preview", "publish", "run"])
        self.assertEqual(self.data["coordinator"].data["preview"]["state"], "state-4")
        self.assertGreaterEqual(self.data["coordinator"].listeners, 4)

    async def test_schedule_event_replaces_callbacks_and_unload_cleans_everything(self):
        old_tracks = list(self.hass.tracks)
        await self.hass.bus.listeners["playlist_assistant_schedule_changed"](types.SimpleNamespace(data={"history_interval_minutes": 30, "daily_enabled": False, "daily_time": "05:30"}))
        self.assertNotEqual(self.hass.tracks, old_tracks)
        self.assertEqual(self.hass.tracks[0][1], timedelta(minutes=30))
        self.assertTrue(await self.integration.async_unload_entry(self.hass, self.entry))
        self.assertEqual(self.hass.tracks, [])
        self.assertEqual(self.hass.services.handlers, {})
        self.assertEqual(self.hass.bus.listeners, {})
        self.assertEqual(set(self.hass.config_entries.unloaded), {"sensor", "binary_sensor"})

    async def test_native_callbacks_route_through_bridge_and_refresh_coordinator(self):
        interval_callback = next(track[2] for track in self.hass.tracks if track[0] == "interval")
        daily_callback = next(track[3] for track in self.hass.tracks if track[0] == "daily")
        await interval_callback()
        await daily_callback()
        self.assertEqual(self.data["bridge"].calls, ["sync", "run"])
        self.assertEqual(self.data["coordinator"].data["preview"]["state"], "state-2")
        self.assertGreaterEqual(self.data["coordinator"].listeners, 2)
