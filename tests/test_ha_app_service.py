import json
import tempfile
import unittest

from application_paths import ApplicationPaths
from ha_app.service import AUTHORIZATION_CACHE_NAME, AUTHORIZATION_STATUS_NAME, AppOptions, ServiceHost, spotify_environment


class HomeAssistantServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.paths = ApplicationPaths.from_data_dir(self.directory.name)
        self.options = AppOptions("client-id", "client-secret", "bridge-secret")
        self.service = ServiceHost(paths=self.paths, options=self.options)

    def tearDown(self):
        self.directory.cleanup()

    def test_configuration_translation_keeps_cache_in_data_and_credentials_private(self):
        environment = spotify_environment(self.options, self.paths)
        self.assertEqual(environment["SPOTIFY_CLIENT_ID"], "client-id")
        self.assertEqual(environment["SPOTIFY_CLIENT_SECRET"], "client-secret")
        self.assertEqual(environment["SPOTIFY_CACHE_PATH"], str(self.paths.data_dir / AUTHORIZATION_CACHE_NAME))
        self.assertEqual(environment["SPOTIFY_OPEN_BROWSER"], "false")

    def test_one_tick_without_authorization_is_degraded_and_does_not_run_jobs(self):
        self.assertEqual(self.service.tick(), [])
        status = json.loads((self.paths.data_dir / AUTHORIZATION_STATUS_NAME).read_text(encoding="utf-8"))
        self.assertEqual(status, {"status": "not_connected"})

    def test_one_tick_with_authorization_only_refreshes_connection(self):
        (self.paths.data_dir / AUTHORIZATION_CACHE_NAME).write_text(json.dumps({"refresh_token": "test-token"}), encoding="utf-8")
        self.service.tick()
        status = json.loads((self.paths.data_dir / AUTHORIZATION_STATUS_NAME).read_text(encoding="utf-8"))
        self.assertEqual(status, {"status": "authorization_cache_available"})

    def test_host_has_no_scheduler_policy(self):
        self.assertFalse(hasattr(self.service, "_policy"))
