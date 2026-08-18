"""Isolation checks for the parallel historical Home Assistant test package."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock


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
            'client.prepare_private_playlist(target_playlist["id"], target_name)',
            publish,
        )
        self.assertIn("client.replace_playlist_items(", publish)
        self.assertIn('def playlist(self, playlist_id): return self._call("playlist"', client)
        self.assertIn('def get_playlist(self, playlist_id: str) -> dict:', client)
        self.assertIn('"playlist": ("GET", "/playlists/{playlist_id}")', api)

    def test_checkpoint_two_directly_resolves_omitted_private_target(self):
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

        self.assertFalse(changed)
        client.get_playlist.assert_called_once_with("target")
        client.prepare_private_playlist.assert_not_called()

    def test_installation_uses_a_local_app_not_a_nested_repository_app(self):
        readme = (VARIANT / "README.md").read_text(encoding="utf-8")

        self.assertIn(
            "`/addons/playlist_assistant_historical_test/`", readme
        )
        self.assertIn("Home Assistant's local app mechanism", readme)
        self.assertIn("**Local apps** section", readme)
        self.assertNotIn("Add this repository as a local/custom add-on repository", readme)


if __name__ == "__main__":
    unittest.main()
