from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest

from application_storage import ApplicationStorage
from runtime import JobResult, RuntimeOrchestrator
from runtime_config import RuntimeConfig, RuntimeConfigError


class ApplicationStorageTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.database = Path(self.directory.name) / "playlist_assistant.db"
        self.storage = ApplicationStorage(self.database)

    def tearDown(self):
        self.directory.cleanup()

    def test_fresh_database_uses_runtime_config_defaults(self):
        config = self.storage.load_runtime_config()

        self.assertEqual(config, RuntimeConfig())
        self.assertEqual(config.history_poll_minutes, 90)

    def test_valid_settings_round_trip_without_storing_long_weight(self):
        self.storage.save_runtime_config(
            RuntimeConfig(
                today_size=125,
                rare_weight=70,
                artist_gap=4,
                history_poll_minutes=45,
            )
        )

        config = self.storage.load_runtime_config()
        self.assertEqual(config.rare_weight, 70)
        self.assertEqual(config.long_weight, 30)
        self.assertEqual(config.history_poll_minutes, 45)
        conn = sqlite3.connect(self.database)
        try:
            names = {
                row[0]
                for row in conn.execute(
                    "SELECT setting_name FROM application_setting"
                )
            }
        finally:
            conn.close()
        self.assertNotIn("long_weight", names)
        self.assertIn("artist_gap", names)
        self.assertNotIn("artist_min_gap", names)

    def test_invalid_settings_use_runtime_config_validation(self):
        with self.assertRaises(RuntimeConfigError):
            self.storage.save_runtime_config(RuntimeConfig(rare_weight=101))

        conn = sqlite3.connect(self.database)
        try:
            conn.execute(
                "CREATE TABLE application_setting (setting_name TEXT PRIMARY KEY, setting_value INTEGER NOT NULL)"
            )
            conn.execute(
                "INSERT INTO application_setting VALUES ('today_size', 0)"
            )
            conn.commit()
        finally:
            conn.close()
        with self.assertRaises(RuntimeConfigError):
            self.storage.load_runtime_config()

    def test_status_round_trip_preserves_last_success_after_later_failure(self):
        started = datetime(2026, 8, 9, 10, 0, tzinfo=timezone.utc)
        successful = JobResult(
            "history", True, started, started, 0.0
        )
        self.storage.record_job_result(successful)
        failed_at = datetime(2026, 8, 9, 11, 0, tzinfo=timezone.utc)
        self.storage.record_job_result(
            JobResult(
                "history", False, failed_at, failed_at, 0.0,
                failed_step="history", error=RuntimeError("Spotify unavailable"),
            )
        )

        status = self.storage.get_job_status("history")
        self.assertFalse(status.success)
        self.assertEqual(status.failed_step, "history")
        self.assertEqual(status.error_type, "RuntimeError")
        self.assertEqual(status.error_message, "Spotify unavailable")
        self.assertEqual(status.last_success_at, started.isoformat())
        self.assertIsInstance(status.to_dict(), dict)

    def test_runtime_persists_completed_today_job_without_altering_pipeline(self):
        calls = []
        runtime = RuntimeOrchestrator(
            history_runner=lambda **kwargs: calls.append("history"),
            sources_runner=lambda **kwargs: calls.append("sources"),
            score_runner=lambda **kwargs: calls.append("score"),
            publish_runner=lambda **kwargs: calls.append("publish"),
            status_store=self.storage,
            now=lambda: datetime(2026, 8, 9, tzinfo=timezone.utc),
        )

        result = runtime.run_today()

        self.assertTrue(result.success)
        self.assertEqual(calls, ["history", "sources", "score", "publish"])
        self.assertTrue(self.storage.get_job_status("today").success)

    def test_status_write_failure_does_not_change_a_job_result(self):
        class FailingStore:
            def record_job_result(self, result):
                raise sqlite3.OperationalError("database is unavailable")

        runtime = RuntimeOrchestrator(
            history_runner=lambda **kwargs: None,
            sources_runner=lambda **kwargs: None,
            score_runner=lambda **kwargs: None,
            publish_runner=lambda **kwargs: None,
            status_store=FailingStore(),
            now=lambda: datetime(2026, 8, 9, tzinfo=timezone.utc),
        )

        self.assertTrue(runtime.run_history().success)

    def test_schema_creation_keeps_existing_history_data(self):
        conn = sqlite3.connect(self.database)
        try:
            conn.execute("CREATE TABLE history (played_at TEXT PRIMARY KEY)")
            conn.execute("INSERT INTO history VALUES ('2026-08-09T00:00:00+00:00')")
            conn.commit()
        finally:
            conn.close()

        self.storage.load_runtime_config()

        conn = sqlite3.connect(self.database)
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM history").fetchone()[0], 1)
        finally:
            conn.close()
