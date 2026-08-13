import json
import tempfile
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from application_paths import ApplicationPaths
from ha_app.control_panel import ControlPanel, start_ingress


class _Workflow:
    def __init__(self):
        self.calls = []

    def preview_state(self):
        return "idle"

    def sync(self):
        self.calls.append("sync")

    def preview(self):
        self.calls.append("preview")

    def publish(self):
        self.calls.append("publish")

    def run(self):
        self.calls.append("run")


class ControlPanelTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.paths = ApplicationPaths.from_data_dir(self.directory.name)
        self.paths.ensure_runtime_directories()
        self.panel = ControlPanel(self.paths, spotify_available=lambda: False)

    def tearDown(self):
        self.directory.cleanup()

    def request_ingress(self, path, *, headers=None, data=None, method=None):
        headers = headers or {}
        request = Request(f"http://127.0.0.1:{self.ingress.server_address[1]}{path}", headers=headers, data=data,
                          method=method or ("POST" if data is not None else "GET"))
        return urlopen(request)

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

    def test_ingress_serves_a_prefixed_panel_and_json_api_responses(self):
        self.ingress = start_ingress(self.panel, bridge_token="bridge-secret", port=0,
                                     ingress_client_address="127.0.0.1")
        self.addCleanup(self.ingress.server_close)
        self.addCleanup(self.ingress.shutdown)

        with self.request_ingress("/", headers={"X-Ingress-Path": "/api/hassio_ingress/example"}) as response:
            page = response.read().decode("utf-8")
            self.assertIn('<base href="/api/hassio_ingress/example/">', page)

        with self.request_ingress("/api/state") as response:
            self.assertEqual(response.headers.get_content_type(), "application/json")
            self.assertIn("spotify", json.loads(response.read()))

        with self.assertRaises(HTTPError) as caught:
            self.request_ingress("/api/missing")
        self.assertEqual(caught.exception.code, 404)
        self.assertEqual(caught.exception.headers.get_content_type(), "application/json")
        self.assertEqual(json.loads(caught.exception.read()), {"error": "Unknown API endpoint."})

    def test_initial_ingress_state_is_json_when_pairing_is_unavailable(self):
        self.ingress = start_ingress(self.panel, bridge_token="bridge-secret", port=0,
                                     ingress_client_address="127.0.0.1")
        self.addCleanup(self.ingress.server_close)
        self.addCleanup(self.ingress.shutdown)

        with self.request_ingress("/api/state") as response:
            self.assertEqual(response.status, 200)
            state = json.loads(response.read())

        self.assertEqual(state["spotify"], {"state": "not_connected", "available": False})
        self.assertNotIn("secret", json.dumps(state).lower())

    def test_initial_ingress_state_has_no_pairing_mode(self):
        self.ingress = start_ingress(self.panel, bridge_token="bridge-secret", port=0,
                                     ingress_client_address="127.0.0.1")
        self.addCleanup(self.ingress.server_close)
        self.addCleanup(self.ingress.shutdown)

        with self.request_ingress("/api/state") as response:
            self.assertEqual(response.status, 200)
            state = json.loads(response.read())

        self.assertEqual(state["spotify"], {"state": "not_connected", "available": False})

    def test_settings_api_returns_save_feedback_and_persists_values(self):
        self.ingress = start_ingress(self.panel, bridge_token="bridge-secret", port=0,
                                     ingress_client_address="127.0.0.1")
        self.addCleanup(self.ingress.server_close)
        self.addCleanup(self.ingress.shutdown)
        payload = json.dumps({"today_size": 77, "rare_weight": 60, "artist_gap": 3,
                              "history_poll_minutes": 120, "today_schedule_enabled": True,
                              "today_schedule_time": "07:30", "target_playlist_name": "Morning"}).encode()
        with self.assertLogs("playlist_assistant.control_panel", "INFO") as logs:
            with self.request_ingress("/api/settings", headers={"Content-Type": "application/json"}, data=payload) as response:
                result = json.loads(response.read())
        self.assertEqual(result["message"], "Settings saved.")
        self.assertEqual(result["state"]["settings"], {
            "today_size": 77, "rare_weight": 60, "artist_gap": 3,
            "history_poll_minutes": 120, "today_schedule_enabled": True,
            "today_schedule_time": "07:30", "long_weight": 40,
            "target_playlist_name": "Morning",
        })
        self.assertIn("settings_saved active_daily_schedule=07:30", logs.output[0])

    def test_scheduler_failure_rolls_back_settings_and_does_not_log_saved(self):
        panel = ControlPanel(self.paths, spotify_available=lambda: False,
                             schedule_changed=lambda _: (_ for _ in ()).throw(RuntimeError("schedule unavailable")))
        with self.assertLogs("playlist_assistant.control_panel", "WARNING") as logs:
            with self.assertRaisesRegex(ValueError, "schedule unavailable"):
                panel.save_settings({"today_schedule_time": "07:30"})
        self.assertEqual(panel.state()["settings"]["today_schedule_time"], "04:00")
        self.assertNotIn("settings_saved", " ".join(logs.output))

    def test_ingress_action_accepts_empty_post_body_as_a_server_side_trigger(self):
        workflow = _Workflow()
        self.panel = ControlPanel(self.paths, spotify_available=lambda: True, workflow=workflow)
        self.ingress = start_ingress(self.panel, bridge_token="bridge-secret", port=0,
                                     ingress_client_address="127.0.0.1")
        self.addCleanup(self.ingress.server_close)
        self.addCleanup(self.ingress.shutdown)

        with self.request_ingress("/api/actions/sync", data=b"", method="POST") as response:
            result = json.loads(response.read())

        self.assertEqual(response.status, 200)
        self.assertEqual(workflow.calls, ["sync"])
        self.assertEqual(result["spotify"]["state"], "connected")

    def test_pairing_download_is_not_available(self):
        self.ingress = start_ingress(self.panel, bridge_token="bridge-secret", port=0,
                                     ingress_client_address="127.0.0.1")
        self.addCleanup(self.ingress.server_close)
        self.addCleanup(self.ingress.shutdown)
        with self.assertRaises(HTTPError): self.request_ingress("/api/spotify/pairing-file")
