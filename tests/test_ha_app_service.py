import json
import tempfile
import unittest

from application_paths import ApplicationPaths
from ha_app.service import AUTHORIZATION_CACHE_NAME, AUTHORIZATION_STATUS_NAME, AppOptions, ServiceHost, spotify_environment


class FakePolicy:
    def __init__(self, *, runtime, storage):
        self.calls = []
        self.error = None

    def run_due(self, config):
        self.calls.append(config)
        if self.error:
            raise self.error
        return []


class HomeAssistantServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.paths = ApplicationPaths.from_data_dir(self.directory.name)
        self.options = AppOptions("client-id", "client-secret")
        self.created_policy = None

        def policy_factory(**kwargs):
            self.created_policy = FakePolicy(**kwargs)
            return self.created_policy

        self.service = ServiceHost(paths=self.paths, options=self.options, policy_factory=policy_factory, runtime_factory=lambda paths: object())

    def tearDown(self):
        self.directory.cleanup()

    def test_configuration_translation_keeps_cache_in_data_and_credentials_private(self):
        environment = spotify_environment(self.options, self.paths)
        self.assertEqual(environment["SPOTIFY_CLIENT_ID"], "client-id")
        self.assertEqual(environment["SPOTIFY_CLIENT_SECRET"], "client-secret")
        self.assertEqual(environment["SPOTIFY_CACHE_PATH"], str(self.paths.data_dir / AUTHORIZATION_CACHE_NAME))
        self.assertEqual(environment["SPOTIFY_OPEN_BROWSER"], "false")

    def test_one_tick_without_authorization_is_degraded_and_does_not_run_policy(self):
        self.assertEqual(self.service.tick(), [])
        self.assertEqual(self.created_policy.calls, [])
        status = json.loads((self.paths.data_dir / AUTHORIZATION_STATUS_NAME).read_text(encoding="utf-8"))
        self.assertEqual(status, {"status": "not_connected"})

    def test_one_tick_with_authorization_invokes_existing_policy_once(self):
        (self.paths.data_dir / AUTHORIZATION_CACHE_NAME).write_text(json.dumps({"refresh_token": "test-token"}), encoding="utf-8")
        self.service.tick()
        self.assertEqual(len(self.created_policy.calls), 1)
        status = json.loads((self.paths.data_dir / AUTHORIZATION_STATUS_NAME).read_text(encoding="utf-8"))
        self.assertEqual(status, {"status": "authorization_cache_available"})

    def test_one_tick_continues_when_scheduler_raises(self):
        (self.paths.data_dir / AUTHORIZATION_CACHE_NAME).write_text(json.dumps({"access_token": "test-token"}), encoding="utf-8")
        self.created_policy.error = RuntimeError("job failure")
        self.assertEqual(self.service.tick(), [])
        self.assertEqual(len(self.created_policy.calls), 1)
