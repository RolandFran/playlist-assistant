import json
import tempfile
import unittest

from application_paths import ApplicationPaths
from ha_app.control_panel import ControlPanel


class ControlPanelTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.paths = ApplicationPaths.from_data_dir(self.directory.name)
        self.paths.ensure_runtime_directories()
        self.panel = ControlPanel(self.paths, spotify_available=lambda: False)

    def tearDown(self):
        self.directory.cleanup()

    def test_state_is_secret_free_and_marks_spotify_actions_unavailable(self):
        state = self.panel.state()
        self.assertEqual(state["spotify"], {"state": "not_connected", "available": False})
        self.assertNotIn("secret", json.dumps(state).lower())
        self.assertEqual(state["settings"]["target_playlist_name"], "Today")

    def test_settings_are_persisted_and_blank_target_is_rejected(self):
        self.panel.storage.save_target_playlist("Today", "spotify-target-id")
        state = self.panel.save_settings({
            "today_size": 99, "rare_weight": 70, "artist_gap": 4,
            "today_schedule_enabled": False, "today_schedule_time": "05:30",
            "target_playlist_name": "Morning Today",
        })
        self.assertEqual(state["settings"]["long_weight"], 30)
        self.assertEqual(state["settings"]["target_playlist_name"], "Morning Today")
        self.assertEqual(self.panel.storage.get_target_playlist(), ("Morning Today", "spotify-target-id"))
        with self.assertRaisesRegex(ValueError, "blank"):
            self.panel.save_settings({"target_playlist_name": "  "})

    def test_spotify_actions_are_blocked_but_local_calculation_is_not_preblocked(self):
        with self.assertRaisesRegex(RuntimeError, "not connected"):
            self.panel.run_action("history")
