"""Isolation checks for the parallel historical Home Assistant test package."""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import inspect
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock

from historical_test.custom_components.playlist_assistant_historical_test.native import (
    NativeSchedule,
)


ROOT = Path(__file__).resolve().parents[1]
VARIANT = ROOT / "historical_test"
ADDON = VARIANT / "playlist_assistant_historical_test"
INTEGRATION = VARIANT / "custom_components" / "playlist_assistant_historical_test"


def load_historical_publish_module():
    sys.path.insert(0, str(ADDON))
    try:
        spec = importlib.util.spec_from_file_location(
            "historical_test_publish",
            ADDON / "publish.py",
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


class HistoricalTestVariantIsolationTests(unittest.TestCase):
    def test_addon_identity_ports_and_database_are_isolated(self):
        config = (ADDON / "config.yaml").read_text(encoding="utf-8")
        paths = (ADDON / "application_paths.py").read_text(encoding="utf-8")

        self.assertIn("name: Playlist Assistant Historical Test", config)
        self.assertIn("slug: playlist_assistant_historical_test", config)
        self.assertIn("ingress_port: 8108", config)
        self.assertIn("watchdog: http://[HOST]:8109/health", config)
        self.assertIn('"playlist_assistant_historical_test.db"', paths)
        self.assertNotIn("slug: playlist_assistant\n", config)

    def test_integration_and_addon_use_only_historical_test_interfaces(self):
        manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
        const = (INTEGRATION / "const.py").read_text(encoding="utf-8")
        api = (INTEGRATION / "api.py").read_text(encoding="utf-8")
        service = (ADDON / "service.py").read_text(encoding="utf-8")

        self.assertEqual(manifest["domain"], "playlist_assistant_historical_test")
        self.assertEqual(manifest["name"], "Playlist Assistant Historical Test")
        self.assertIn('DOMAIN = "playlist_assistant_historical_test"', const)
        self.assertIn("/api/playlist_assistant_historical_test/spotify", api)
        self.assertIn("/api/playlist_assistant_historical_test/spotify", service)
        self.assertIn(
            "/api/services/playlist_assistant_historical_test/reconfigure_schedule",
            service,
        )

    def test_publish_checkpoint_two_keeps_isolated_target_and_resolves_persisted_metadata(self):
        publish = (ADDON / "publish.py").read_text(encoding="utf-8")
        storage = (ADDON / "application_storage.py").read_text(encoding="utf-8")
        client = (ADDON / "client.py").read_text(encoding="utf-8")
        api = (INTEGRATION / "api.py").read_text(encoding="utf-8")

        self.assertIn('"Playlist Assistant Historical Test"', publish)
        self.assertIn('"Playlist Assistant Historical Test"', storage)
        self.assertIn("def resolve_target_playlist(", publish)
        self.assertIn("def prepare_publish_target(", publish)
        self.assertIn('return client.get_playlist(target_playlist_id)', publish)
        self.assertIn(
            '"persisted target playlist target_playlist_name=%s target_playlist_id=%s"',
            publish,
        )
        self.assertIn(
            'client.prepare_private_playlist(target_playlist["id"], target_name)',
            publish,
        )
        self.assertIn("client.replace_playlist_items(", publish)
        self.assertIn('def playlist(self, playlist_id): return self._call("playlist"', client)
        self.assertIn('def get_playlist(self, playlist_id: str) -> dict:', client)
        self.assertIn('"playlist": ("GET", "/playlists/{playlist_id}")', api)

    def test_checkpoint_three_reuses_the_connected_historical_proxy_session(self):
        api = (INTEGRATION / "api.py").read_text(encoding="utf-8")

        self.assertNotIn("config_entry_oauth2_flow", api)
        self.assertIn(
            'api = next(item["spotify"] for item in self.hass.data.get(DOMAIN, {}).values() if item.get("spotify"))',
            api,
        )
        self.assertIn(
            "Reuse the authenticated session established by the integration.",
            api,
        )

    def test_checkpoint_three_b_always_writes_matching_target_metadata(self):
        publish = load_historical_publish_module()
        client = Mock()
        client.get_all_user_playlists.return_value = [
            {"id": "other", "name": "Other", "public": False},
        ]
        client.get_playlist.return_value = {
            "id": "target",
            "name": "Playlist Assistant Historical Test",
            "public": False,
        }

        target = publish.resolve_target_playlist(
            client,
            "Playlist Assistant Historical Test",
            "target",
        )
        changed = publish.prepare_publish_target(
            client,
            target,
            "Playlist Assistant Historical Test",
        )

        self.assertTrue(changed)
        client.get_playlist.assert_called_once_with("target")
        client.prepare_private_playlist.assert_called_once_with(
            "target", "Playlist Assistant Historical Test"
        )

    def test_installation_uses_a_local_app_not_a_nested_repository_app(self):
        readme = (VARIANT / "README.md").read_text(encoding="utf-8")

        self.assertIn(
            "`/addons/playlist_assistant_historical_test/`", readme
        )
        self.assertIn("Home Assistant's local app mechanism", readme)
        self.assertIn("**Local apps** section", readme)
        self.assertNotIn("Add this repository as a local/custom add-on repository", readme)


class HistoricalTestScheduleDiagnosticsTests(unittest.TestCase):
    def test_daily_diagnostics_preserve_second_zero_registration_and_one_run(self):
        registrations = []
        calls = []

        def interval(value, callback):
            registrations.append(("interval", value, callback))
            return lambda: None

        def daily(hour, minute, callback):
            registrations.append(("daily", hour, minute, callback))
            return lambda: None

        async def run_daily():
            calls.append("run")

        schedule = NativeSchedule(interval, daily, lambda: None, run_daily)
        with self.assertLogs(
            "historical_test.custom_components.playlist_assistant_historical_test.native",
            "INFO",
        ) as logs:
            schedule.configure(90, True, "20:30")
            daily_registration = registrations[1]
            self.assertEqual(daily_registration[:3], ("daily", 20, 30))
            callback_result = daily_registration[3]()
            self.assertTrue(inspect.isawaitable(callback_result))
            asyncio.run(callback_result)

        self.assertEqual(calls, ["run"])
        output = " ".join(logs.output)
        self.assertIn(
            "daily_schedule_callback_registered hour=20 minute=30 second=0", output
        )
        self.assertIn("daily_schedule_callback_wrapper_entered", output)
        self.assertIn("daily_run_once_entered", output)
        self.assertIn("daily_run_callback_invoking", output)


class HistoricalTestProxySessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_playlist_proxy_reuses_the_connected_historical_session(self):
        module_names = (
            "homeassistant",
            "homeassistant.components",
            "homeassistant.components.http",
            "historical_test.custom_components.playlist_assistant_historical_test.spotify",
            "historical_test.custom_components.playlist_assistant_historical_test.api",
        )
        original_modules = {name: sys.modules.get(name) for name in module_names}

        homeassistant = types.ModuleType("homeassistant")
        components = types.ModuleType("homeassistant.components")
        http = types.ModuleType("homeassistant.components.http")

        class HomeAssistantView:
            def json(self, payload, status_code=200, headers=None):
                return {"payload": payload, "status_code": status_code, "headers": headers}

        http.HomeAssistantView = HomeAssistantView
        spotify_module = types.ModuleType(
            "historical_test.custom_components.playlist_assistant_historical_test.spotify"
        )
        spotify_module.SpotifyApi = object
        spotify_module.SpotifyAuthError = type("SpotifyAuthError", (Exception,), {})
        spotify_module.SpotifyConnectionError = type("SpotifyConnectionError", (Exception,), {})
        spotify_module.SpotifyRequestError = type("SpotifyRequestError", (Exception,), {})
        sys.modules.update(
            {
                "homeassistant": homeassistant,
                "homeassistant.components": components,
                "homeassistant.components.http": http,
                "historical_test.custom_components.playlist_assistant_historical_test.spotify": spotify_module,
            }
        )
        try:
            api_module = importlib.import_module(
                "historical_test.custom_components.playlist_assistant_historical_test.api"
            )

            class ConnectedSpotify:
                def __init__(self):
                    self.requests = []

                async def async_request(self, method, path, **kwargs):
                    self.requests.append((method, path, kwargs))
                    return {"id": "persisted-target", "name": "Playlist Assistant Historical Test", "public": False}

            class Request:
                async def json(self):
                    return {
                        "operation": "playlist_details",
                        "path": {"playlist_id": "persisted-target"},
                        "json": {"name": "Playlist Assistant Historical Test", "public": False},
                    }

            spotify = ConnectedSpotify()
            hass = types.SimpleNamespace(
                data={"playlist_assistant_historical_test": {"entry": {"spotify": spotify}}}
            )

            response = await api_module.SpotifyProxyView(hass).post(Request())

            self.assertEqual(response["status_code"], 200)
            self.assertEqual(response["payload"]["id"], "persisted-target")
            self.assertEqual(
                spotify.requests,
                [
                    (
                        "PUT",
                        "/playlists/persisted-target",
                        {
                            "params": None,
                            "json": {"name": "Playlist Assistant Historical Test", "public": False},
                        },
                    )
                ],
            )
        finally:
            for name, module in original_modules.items():
                if module is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = module


if __name__ == "__main__":
    unittest.main()
