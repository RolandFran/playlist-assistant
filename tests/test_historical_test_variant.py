"""Isolation checks for the parallel historical Home Assistant test package."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
VARIANT = ROOT / "historical_test"
ADDON = VARIANT / "playlist_assistant_historical_test"
INTEGRATION = VARIANT / "custom_components" / "playlist_assistant_historical_test"


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

    def test_publish_path_keeps_historical_operations_and_safe_target_default(self):
        publish = (ADDON / "publish.py").read_text(encoding="utf-8")
        storage = (ADDON / "application_storage.py").read_text(encoding="utf-8")

        self.assertIn('"Playlist Assistant Historical Test"', publish)
        self.assertIn('"Playlist Assistant Historical Test"', storage)
        self.assertIn("client.prepare_private_playlist(playlist_id, target_name)", publish)
        self.assertIn("client.replace_playlist_items(", publish)


if __name__ == "__main__":
    unittest.main()
