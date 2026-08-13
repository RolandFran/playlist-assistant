from datetime import datetime, timezone
from threading import Event, Thread
import unittest

from runtime import DEFAULT_HISTORY_POLL_MINUTES, RuntimeOrchestrator


class RuntimeOrchestrationTests(unittest.TestCase):
    def make_runtime(self, calls, **overrides):
        def history_runner(**kwargs):
            calls.append(("history", kwargs))

        def sources_runner(**kwargs):
            calls.append(("sources", kwargs))

        def score_runner(**kwargs):
            calls.append(("score", kwargs))

        def publish_runner(**kwargs):
            calls.append(("publish", kwargs))

        runners = {
            "history_runner": history_runner,
            "sources_runner": sources_runner,
            "score_runner": score_runner,
            "publish_runner": publish_runner,
        }
        runners.update(overrides)
        return RuntimeOrchestrator(
            **runners,
            now=lambda: datetime(2026, 8, 9, tzinfo=timezone.utc),
        )

    def test_history_job_returns_result_and_forwards_recovery(self):
        calls = []
        runtime = self.make_runtime(calls)

        result = runtime.run_history(recover_after="2026-08-08T00:00:00Z")

        self.assertTrue(result.success)
        self.assertEqual(result.job_name, "history")
        self.assertEqual(result.duration_seconds, 0)
        self.assertIsNone(result.failed_step)
        self.assertEqual(
            calls,
            [("history", {"recover_after": "2026-08-08T00:00:00Z"})],
        )

    def test_today_job_runs_existing_pipeline_in_order(self):
        calls = []
        runtime = self.make_runtime(calls)
        config = object()

        result = runtime.run_today(
            write=True,
            force_full_sources=True,
            config=config,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.job_name, "today")
        self.assertEqual(
            calls,
            [
                ("history", {}),
                ("sources", {"force_full": True}),
                ("score", {"config": config}),
                ("publish", {"write": True}),
            ],
        )

    def test_failed_today_step_stops_later_steps_and_identifies_step(self):
        calls = []

        def failing_sources_runner(**kwargs):
            calls.append(("sources", kwargs))
            raise RuntimeError("source sync failed")

        runtime = self.make_runtime(
            calls,
            sources_runner=failing_sources_runner,
        )

        result = runtime.run_today()

        self.assertFalse(result.success)
        self.assertEqual(result.failed_step, "sources")
        self.assertIsInstance(result.error, RuntimeError)
        self.assertEqual(
            calls,
            [
                ("history", {}),
                ("sources", {"force_full": False}),
            ],
        )

    def test_reentrant_same_job_is_rejected(self):
        calls = []
        nested_results = []
        runtime = None

        def history_runner(**kwargs):
            calls.append(("history", kwargs))
            nested_results.append(runtime.run_history())

        runtime = self.make_runtime(calls, history_runner=history_runner)

        result = runtime.run_history()

        self.assertTrue(result.success)
        self.assertEqual(len(nested_results), 1)
        self.assertFalse(nested_results[0].success)
        self.assertEqual(nested_results[0].failed_step, "history")
        self.assertIn("already running", str(nested_results[0].error))

    def test_concurrent_same_job_is_rejected_before_entering_runner(self):
        calls = []
        runner_started = Event()
        release_runner = Event()

        def blocking_history_runner(**kwargs):
            calls.append(("history", kwargs))
            runner_started.set()
            release_runner.wait(timeout=1)

        runtime = self.make_runtime(calls, history_runner=blocking_history_runner)
        results = []

        first = Thread(target=lambda: results.append(runtime.run_history()))
        first.start()
        self.assertTrue(runner_started.wait(timeout=1))

        second = Thread(target=lambda: results.append(runtime.run_history()))
        second.start()
        second.join(timeout=1)

        self.assertFalse(second.is_alive())
        self.assertEqual(calls, [("history", {"recover_after": None})])

        release_runner.set()
        first.join(timeout=1)

        self.assertFalse(first.is_alive())
        self.assertEqual(len(results), 2)
        self.assertEqual(sum(result.success for result in results), 1)
        rejected = next(result for result in results if not result.success)
        self.assertEqual(rejected.failed_step, "history")
        self.assertIn("already running", str(rejected.error))

    def test_concurrent_different_jobs_are_also_rejected(self):
        calls = []
        runner_started = Event()
        release_runner = Event()

        def blocking_history_runner(**kwargs):
            calls.append(("history", kwargs))
            runner_started.set()
            release_runner.wait(timeout=1)

        runtime = self.make_runtime(calls, history_runner=blocking_history_runner)
        first = Thread(target=runtime.run_history)
        first.start()
        self.assertTrue(runner_started.wait(timeout=1))
        second = runtime.run_today()
        release_runner.set()
        first.join(timeout=1)

        self.assertFalse(second.success)
        self.assertIn("already running", str(second.error))
        self.assertEqual(calls, [("history", {"recover_after": None})])

    def test_history_cadence_default_is_ninety_minutes(self):
        self.assertEqual(DEFAULT_HISTORY_POLL_MINUTES, 90)
