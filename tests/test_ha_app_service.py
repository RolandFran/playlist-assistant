import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from application_paths import ApplicationPaths
from ha_app.service import (
    AUTHORIZATION_STATUS_NAME,
    AppOptions,
    ServiceHost,
    clean_legacy_options,
    load_options_file,
    spotify_environment,
)
from runtime_config import RuntimeConfig


class HomeAssistantServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.paths = ApplicationPaths.from_data_dir(self.directory.name)
        self.options = AppOptions()
        self.service = ServiceHost(paths=self.paths, options=self.options)

    def tearDown(self):
        self.directory.cleanup()

    def test_configuration_contains_only_the_ha_proxy(self):
        environment = spotify_environment(self.options, self.paths)
        self.assertEqual(environment, {"PLAYLIST_ASSISTANT_SPOTIFY_PROXY": "http://supervisor/core/api/playlist_assistant/spotify"})

    def test_legacy_options_are_discarded_when_loading_old_options(self):
        options_file = Path(self.directory.name) / "options.json"
        old_options = {
            "spotify_client_id": "client-id-secret",
            "spotify_client_secret": "client-secret",
            "bridge_token": "bridge-secret",
            "log_level": "debug",
        }
        options_file.write_text(json.dumps(old_options), encoding="utf-8")

        cleaned = clean_legacy_options(old_options)
        options = load_options_file(options_file)

        self.assertEqual(cleaned, {"log_level": "debug"})
        self.assertEqual(options, AppOptions(log_level="debug"))

    def test_log_level_defaults_to_info_and_accepts_each_supported_value(self):
        self.assertEqual(AppOptions.from_mapping({}), AppOptions(log_level="info"))
        for level in ("debug", "info", "warning", "error"):
            with self.subTest(level=level):
                options = AppOptions.from_mapping({"log_level": level})
                self.assertEqual(options.log_level, level)
                self.assertEqual(options.logging_level, getattr(__import__("logging"), level.upper()))

    def test_invalid_log_level_falls_back_to_info(self):
        options = AppOptions.from_mapping({"log_level": "verbose"})
        self.assertEqual(options, AppOptions(log_level="info"))

    def test_one_tick_without_authorization_is_degraded_and_does_not_run_jobs(self):
        self.assertEqual(self.service.tick(), [])
        status = json.loads((self.paths.data_dir / AUTHORIZATION_STATUS_NAME).read_text(encoding="utf-8"))
        self.assertEqual(status, {"status": "not_connected"})

    def test_host_has_no_scheduler_policy(self):
        self.assertFalse(hasattr(self.service, "_policy"))

    def test_schedule_change_uses_blocking_integration_service_and_requires_json_list_response(self):
        requests = []
        class Response:
            status = 200
            def read(self): return b"[]"
            def __enter__(self): return self
            def __exit__(self, *_): return False
        def urlopen(request, timeout):
            requests.append((request, timeout)); return Response()

        with self.assertLogs("playlist_assistant.ha_app", "INFO") as logs, \
                patch.dict(os.environ, {"SUPERVISOR_TOKEN": "token"}, clear=True), \
                patch("ha_app.service.urllib.request.urlopen", urlopen):
            self.service._notify_schedule_changed(RuntimeConfig(today_schedule_time="17:28"))

        request, timeout = requests[0]
        self.assertEqual(timeout, 5)
        self.assertEqual(request.full_url, "http://supervisor/core/api/services/playlist_assistant/reconfigure_schedule")
        self.assertEqual(json.loads(request.data), {"history_interval_minutes": 90, "daily_enabled": True, "daily_time": "17:28"})
        self.assertIn(
            "schedule_change_sent active_daily_schedule=17:28 ha_response=[] acknowledgement_only=true",
            " ".join(logs.output),
        )

    def test_schedule_change_rejects_an_acknowledgement_with_the_wrong_shape(self):
        class Response:
            status = 200
            def read(self): return b'{"ok": true}'
            def __enter__(self): return self
            def __exit__(self, *_): return False
        with patch.dict(os.environ, {"SUPERVISOR_TOKEN": "token"}, clear=True), patch("ha_app.service.urllib.request.urlopen", return_value=Response()):
            with self.assertRaisesRegex(RuntimeError, "could not activate"):
                self.service._notify_schedule_changed(RuntimeConfig())
