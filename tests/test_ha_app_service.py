import json
import tempfile
import unittest
from unittest.mock import patch

from application_paths import ApplicationPaths
from ha_app.service import AUTHORIZATION_STATUS_NAME, AppOptions, ServiceHost, spotify_environment


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

    def test_one_tick_without_authorization_is_degraded_and_does_not_run_jobs(self):
        self.assertEqual(self.service.tick(), [])
        status = json.loads((self.paths.data_dir / AUTHORIZATION_STATUS_NAME).read_text(encoding="utf-8"))
        self.assertEqual(status, {"status": "not_connected"})

    def test_host_has_no_scheduler_policy(self):
        self.assertFalse(hasattr(self.service, "_policy"))
