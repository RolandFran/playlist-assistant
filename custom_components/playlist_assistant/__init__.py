"""Playlist Assistant setup, including the HA-owned Spotify connection proof."""
from __future__ import annotations
import logging
from .const import DOMAIN, PLATFORMS
from .native import NativeSchedule


LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry):
    from .spotify import SpotifyApi
    from homeassistant.components import persistent_notification
    from homeassistant.helpers.aiohttp_client import async_get_clientsession
    from homeassistant.helpers.event import async_track_time_change, async_track_time_interval
    from .bridge import AddonBridge, async_discover_addon_base_url
    from .coordinator import PlaylistAssistantCoordinator
    bridge = None
    spotify = None
    if "token" in entry.data:
        from homeassistant.helpers import config_entry_oauth2_flow
        from .diagnostics import async_diagnose_playlist_details, safe_diagnostic_detail
        from .spotify import SpotifyRequestError
        implementation = await config_entry_oauth2_flow.async_get_config_entry_implementation(hass, entry)
        spotify = SpotifyApi(config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation))
        # The add-on listener is private to the HA add-on network; Spotify
        # authorization itself is never delegated to it.
        bridge = AddonBridge(
            async_get_clientsession(hass),
            await async_discover_addon_base_url(async_get_clientsession(hass)),
            "",
        )
    elif "url" in entry.data and "bridge_token" in entry.data:
        # Existing add-on entries remain untouched while the HA OAuth proof is added.
        bridge = AddonBridge(async_get_clientsession(hass), entry.data["url"], entry.data["bridge_token"])
    else:
        return False
    if spotify and not hass.data.get(f"{DOMAIN}_api_registered"):
        from .api import async_register_api
        async_register_api(hass)
        hass.data[f"{DOMAIN}_api_registered"] = True
    coordinator = PlaylistAssistantCoordinator(hass, bridge, spotify, entry)
    async def execute(action):
        try: return await coordinator.async_execute(action)
        except Exception as error:
            persistent_notification.async_create(hass, f"Playlist Assistant: {error}", title="Playlist Assistant")
            raise
    async def sync(_now=None): return await execute("sync")
    async def run(_now=None): return await execute("run")
    schedule = NativeSchedule(lambda interval, callback: async_track_time_interval(hass, callback, interval),
        # Without second=0 HA matches every second of the configured minute.
        lambda hour, minute, callback: async_track_time_change(hass, callback, hour=hour, minute=minute, second=0), sync, run)
    async def configure(values=None):
        if values is None:
            await coordinator.async_request_refresh()
            values = coordinator.data["schedule"]
        schedule.configure(values["history_interval_minutes"], values["daily_enabled"], values["daily_time"])
    await coordinator.async_config_entry_first_refresh()
    if bridge:
        await configure(coordinator.data["schedule"])
    async def reconfigure_schedule(call):
        values = call.data
        LOGGER.info(
            "schedule_change_received history_interval_minutes=%s daily_time=%s daily_enabled=%s",
            values.get("history_interval_minutes"),
            values.get("daily_time"),
            values.get("daily_enabled"),
        )
        await configure(values)
        await coordinator.async_schedule_changed(values)
        LOGGER.info(
            "schedule_change_applied history_interval_minutes=%s daily_time=%s daily_enabled=%s",
            values.get("history_interval_minutes"),
            values.get("daily_time"),
            values.get("daily_enabled"),
        )
    async def handler(call): await execute(call.service)
    async def diagnose_playlist_details(call):
        """Temporary comparison of the direct OAuth and SpotifyApi request paths."""
        session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)
        try:
            return await async_diagnose_playlist_details(
                session,
                playlist_id=call.data["playlist_id"],
                name=call.data["name"],
                public=call.data["public"],
                variant=call.data["variant"],
            )
        except SpotifyRequestError as error:
            raise RuntimeError(
                f"Spotify request failed: HTTP {error.status}: {safe_diagnostic_detail(error.detail)}"
            ) from None
    if bridge:
        hass.services.async_register(DOMAIN, "reconfigure_schedule", reconfigure_schedule)
    for action in ("sync", "preview", "publish", "run"):
        hass.services.async_register(DOMAIN, action, handler)
    if spotify:
        hass.services.async_register(DOMAIN, "diagnose_playlist_details", diagnose_playlist_details)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"entry": entry, "bridge": bridge, "spotify": spotify, "coordinator": coordinator, "schedule": schedule}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass, entry):
    data = hass.data[DOMAIN].pop(entry.entry_id)
    data["schedule"].stop()
    for action in ("sync", "preview", "publish", "run", "reconfigure_schedule", "diagnose_playlist_details"): hass.services.async_remove(DOMAIN, action)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
