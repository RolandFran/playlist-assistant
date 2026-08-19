"""Playlist Assistant setup, including the HA-owned Spotify connection proof."""
from __future__ import annotations
import logging
from .const import DOMAIN, PLATFORMS
from .native import NativeSchedule


LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry):
    setup = {"stage": "entry"}
    LOGGER.info(
        "playlist_assistant_config_entry_loaded entry_source=%s token_present=%s",
        getattr(entry, "source", None),
        "token" in entry.data,
    )
    try:
        return await _async_setup_entry(hass, entry, setup)
    except Exception as error:
        LOGGER.info(
            "playlist_assistant_setup_failed stage=%s exception_type=%s",
            setup["stage"],
            type(error).__name__,
        )
        raise


async def _async_setup_entry(hass, entry, setup):
    from .spotify import SpotifyApi
    from homeassistant.components import persistent_notification
    from homeassistant.helpers.aiohttp_client import async_get_clientsession
    from homeassistant.helpers.event import async_track_time_change, async_track_time_interval
    from .bridge import AddonBridge, async_discover_addon_base_url
    from .coordinator import PlaylistAssistantCoordinator
    bridge = None
    spotify = None
    if "token" in entry.data:
        setup["stage"] = "oauth_implementation_resolution"
        from homeassistant.helpers import config_entry_oauth2_flow
        implementation = await config_entry_oauth2_flow.async_get_config_entry_implementation(hass, entry)
        LOGGER.info("playlist_assistant_oauth_implementation_resolved")
        setup["stage"] = "oauth_session_construction"
        session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)
        LOGGER.info("playlist_assistant_oauth_session_constructed")
        setup["stage"] = "spotify_api_construction"
        spotify = SpotifyApi(session)
        LOGGER.info("playlist_assistant_spotify_api_constructed")
        # The add-on listener is private to the HA add-on network; Spotify
        # authorization itself is never delegated to it.
        setup["stage"] = "addon_bridge_discovery"
        bridge = AddonBridge(
            async_get_clientsession(hass),
            await async_discover_addon_base_url(async_get_clientsession(hass)),
            "",
        )
        LOGGER.info("playlist_assistant_addon_bridge_discovered")
    elif "url" in entry.data and "bridge_token" in entry.data:
        # Existing add-on entries remain untouched while the HA OAuth proof is added.
        bridge = AddonBridge(async_get_clientsession(hass), entry.data["url"], entry.data["bridge_token"])
        LOGGER.info("playlist_assistant_legacy_bridge_entry_loaded")
    else:
        LOGGER.info("playlist_assistant_setup_rejected reason=unsupported_entry_data")
        return False
    if spotify and not hass.data.get(f"{DOMAIN}_api_registered"):
        setup["stage"] = "api_registration"
        from .api import async_register_api
        async_register_api(hass)
        hass.data[f"{DOMAIN}_api_registered"] = True
        LOGGER.info("playlist_assistant_api_registered")
    coordinator = PlaylistAssistantCoordinator(hass, bridge, spotify, entry)
    async def execute(action):
        try: return await coordinator.async_execute(action)
        except Exception as error:
            persistent_notification.async_create(hass, f"Playlist Assistant: {error}", title="Playlist Assistant")
            raise
    async def sync(_now=None): return await execute("sync")
    async def run(_now=None):
        LOGGER.info("daily_run_callback_entered")
        return await execute("run")
    schedule = NativeSchedule(lambda interval, callback: async_track_time_interval(hass, callback, interval),
        # Without second=0 HA matches every second of the configured minute.
        lambda hour, minute, callback: async_track_time_change(hass, callback, hour=hour, minute=minute, second=0), sync, run)
    async def configure(values=None):
        if values is None:
            await coordinator.async_request_refresh()
            values = coordinator.data["schedule"]
        LOGGER.info(
            "daily_schedule_configure_before daily_enabled=%s daily_time=%s",
            values["daily_enabled"],
            values["daily_time"],
        )
        schedule.configure(values["history_interval_minutes"], values["daily_enabled"], values["daily_time"])
        LOGGER.info(
            "daily_schedule_configure_completed daily_enabled=%s daily_time=%s",
            values["daily_enabled"],
            values["daily_time"],
        )
    setup["stage"] = "initial_coordinator_refresh"
    await coordinator.async_config_entry_first_refresh()
    if bridge:
        await configure(coordinator.data["schedule"])
    async def reconfigure_schedule(call):
        values = call.data
        LOGGER.info(
            "daily_schedule_reconfigure_requested daily_enabled=%s daily_time=%s",
            values.get("daily_enabled"),
            values.get("daily_time"),
        )
        await configure(values)
        await coordinator.async_schedule_changed(values)
    async def handler(call): await execute(call.service)
    if bridge:
        hass.services.async_register(DOMAIN, "reconfigure_schedule", reconfigure_schedule)
    for action in ("sync", "preview", "publish", "run"):
        hass.services.async_register(DOMAIN, action, handler)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"entry": entry, "bridge": bridge, "spotify": spotify, "coordinator": coordinator, "schedule": schedule}
    setup["stage"] = "platform_forwarding"
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    LOGGER.info("playlist_assistant_setup_completed")
    return True

async def async_unload_entry(hass, entry):
    data = hass.data[DOMAIN].pop(entry.entry_id)
    data["schedule"].stop()
    for action in ("sync", "preview", "publish", "run", "reconfigure_schedule"): hass.services.async_remove(DOMAIN, action)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
