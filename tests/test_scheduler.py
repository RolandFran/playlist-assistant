from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zoneinfo import ZoneInfo

from application_storage import ApplicationStorage
from runtime import JobResult, RuntimeOrchestrator
from runtime_config import RuntimeConfig
from scheduler import SchedulerPolicy


BERLIN = ZoneInfo("Europe/Berlin")


class FakeRuntime:
    def __init__(self, *, fail_history=False, fail_today=False):
        self.calls = []
        self.fail_history = fail_history
        self.fail_today = fail_today

    def run_history(self):
        self.calls.append(("history", {}))
        return _result("history", not self.fail_history)

    def run_today(self, *, write=False, config=None):
        self.calls.append(("today", {"write": write, "config": config}))
        return _result("today", not self.fail_today)


def _result(job_name, success):
    now = datetime(2026, 8, 9, tzinfo=BERLIN)
    return JobResult(job_name, success, now, now, 0.0)


class SchedulerPolicyTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.storage = ApplicationStorage(Path(self.directory.name) / "playlist_assistant.db")
        self.current_time = datetime(2026, 8, 9, 3, 59, tzinfo=BERLIN)
        self.runtime = FakeRuntime()
        self.policy = SchedulerPolicy(
            runtime=self.runtime,
            storage=self.storage,
            now=lambda: self.current_time,
        )

    def tearDown(self):
        self.directory.cleanup()

    def test_today_disabled_leaves_only_history_cadence(self):
        config = RuntimeConfig(today_schedule_enabled=False)
        self.current_time = self.current_time.replace(hour=5)

        self.policy.run_due(config)

        self.assertEqual(self.runtime.calls, [("history", {})])

    def test_today_slot_runs_existing_pipeline_with_write(self):
        self.current_time = self.current_time.replace(hour=4)

        self.policy.run_due(RuntimeConfig())

        self.assertEqual(len(self.runtime.calls), 1)
        name, kwargs = self.runtime.calls[0]
        self.assertEqual(name, "today")
        self.assertTrue(kwargs["write"])

    def test_today_slot_is_caught_up_once_after_its_time(self):
        self.current_time = self.current_time.replace(hour=8)

        self.policy.run_due(RuntimeConfig())
        self.policy.run_due(RuntimeConfig())

        self.assertEqual([name for name, _ in self.runtime.calls], ["today"])

    def test_history_cadence_catches_up_once_and_survives_restart(self):
        config = RuntimeConfig(today_schedule_enabled=False, history_poll_minutes=90)
        self.policy.run_due(config)
        restarted = SchedulerPolicy(
            runtime=self.runtime, storage=self.storage, now=lambda: self.current_time
        )
        restarted.run_due(config)
        self.current_time += timedelta(minutes=90)
        restarted.run_due(config)

        self.assertEqual([name for name, _ in self.runtime.calls], ["history", "history"])

    def test_failed_history_waits_until_next_regular_interval(self):
        self.runtime.fail_history = True
        config = RuntimeConfig(today_schedule_enabled=False, history_poll_minutes=90)

        self.policy.run_due(config)
        self.current_time += timedelta(minutes=89)
        self.policy.run_due(config)
        self.current_time += timedelta(minutes=1)
        self.policy.run_due(config)

        self.assertEqual([name for name, _ in self.runtime.calls], ["history", "history"])

    def test_failed_run_is_booked_before_the_runner_can_return(self):
        observed_attempts = []

        class InspectingRuntime(FakeRuntime):
            def run_history(inner):
                observed_attempts.append(self.storage.get_scheduler_state().last_history_attempt_at)
                return super().run_history()

        self.runtime = InspectingRuntime(fail_history=True)
        self.policy = SchedulerPolicy(runtime=self.runtime, storage=self.storage, now=lambda: self.current_time)
        config = RuntimeConfig(today_schedule_enabled=False, history_poll_minutes=90)

        self.policy.run_due(config)
        self.policy.run_due(config)

        self.assertEqual(len(self.runtime.calls), 1)
        self.assertEqual(observed_attempts, [self.current_time.isoformat()])

    def test_failed_today_waits_until_next_daily_slot(self):
        self.runtime.fail_today = True
        self.current_time = self.current_time.replace(hour=4)

        self.policy.run_due(RuntimeConfig())
        self.current_time += timedelta(hours=12)
        self.policy.run_due(RuntimeConfig())
        self.current_time += timedelta(days=1)
        self.policy.run_due(RuntimeConfig())

        self.assertEqual(
            [name for name, _ in self.runtime.calls if name == "today"],
            ["today", "today"],
        )

    def test_manual_runs_do_not_change_scheduler_attempt_state(self):
        manual_runtime = RuntimeOrchestrator(
            history_runner=lambda **kwargs: None,
            sources_runner=lambda **kwargs: None,
            score_runner=lambda **kwargs: None,
            publish_runner=lambda **kwargs: None,
            status_store=self.storage,
            now=lambda: self.current_time,
        )
        manual_runtime.run_history()
        manual_runtime.run_today(write=False, config=RuntimeConfig())

        self.assertIsNone(self.storage.get_scheduler_state().last_history_attempt_at)
        self.assertIsNone(self.storage.get_scheduler_state().last_today_attempt_date)
        self.assertTrue(self.storage.get_job_status("history").success)
        self.assertTrue(self.storage.get_job_status("today").success)

    def test_scheduler_requires_an_aware_clock(self):
        policy = SchedulerPolicy(
            runtime=self.runtime,
            storage=self.storage,
            now=lambda: datetime(2026, 8, 9, 4, 0),
        )

        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            policy.run_due(RuntimeConfig())
