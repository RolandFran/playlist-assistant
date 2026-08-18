from datetime import datetime, timedelta, timezone
import asyncio
import inspect
import unittest

from custom_components.playlist_assistant.native import NativeSchedule, history_gap


class NativeScheduleTests(unittest.TestCase):
    def test_registered_callbacks_are_async_and_log_the_full_daily_lifecycle(self):
        callbacks = {}
        runs = []

        def interval(value, callback):
            callbacks["history"] = callback
            return lambda: callbacks.pop("history", None)

        def daily(hour, minute, callback):
            callbacks["today"] = callback
            return lambda: callbacks.pop("today", None)

        async def run_daily():
            runs.append("today")

        async def run_history():
            runs.append("history")

        schedule = NativeSchedule(interval, daily, run_history, run_daily)
        with self.assertLogs("custom_components.playlist_assistant.native", "INFO") as logs:
            schedule.configure(90, True, "17:22")
            self.assertTrue(inspect.iscoroutinefunction(callbacks["history"]))
            self.assertTrue(inspect.iscoroutinefunction(callbacks["today"]))
            async def invoke_scheduled_callbacks():
                await callbacks["history"]()
                await callbacks["today"]()

            asyncio.run(invoke_scheduled_callbacks())
            schedule.stop()

        output = " ".join(logs.output)
        self.assertEqual(runs, ["history", "today"])
        self.assertIn("daily_schedule_callback_registered hour=17 minute=22 second=0", output)
        self.assertIn("daily_schedule_callback_wrapper_entered", output)
        self.assertIn("daily_run_callback_invoking", output)
        self.assertIn("daily_schedule_callback_removed", output)

    def test_reconfiguration_unregisters_old_callbacks_before_registering_new_ones(self):
        calls = []
        def interval(value, callback):
            calls.append(("interval", value)); return lambda: calls.append(("stop_interval", value))
        def daily(hour, minute, callback):
            calls.append(("daily", hour, minute)); return lambda: calls.append(("stop_daily", hour, minute))
        schedule = NativeSchedule(interval, daily, lambda: None, lambda: None)
        schedule.configure(90, True, "04:00")
        schedule.configure(30, False, "05:30")
        self.assertEqual(calls[2:4], [("stop_interval", timedelta(minutes=90)), ("stop_daily", 4, 0)])
        self.assertEqual(calls[-1], ("interval", timedelta(minutes=30)))

    def test_changed_daily_time_runs_only_new_callback_once_without_overlap(self):
        active_daily = {}
        runs = []

        def interval(value, callback):
            return lambda: None

        def daily(hour, minute, callback):
            key = f"{hour:02d}:{minute:02d}"
            active_daily[key] = callback
            return lambda: active_daily.pop(key, None)

        async def run_daily():
            runs.append("daily")
            await asyncio.sleep(0)

        schedule = NativeSchedule(interval, daily, lambda: None, run_daily)
        schedule.configure(90, True, "16:40")
        old_callback = active_daily["16:40"]
        schedule.configure(90, True, "16:45")

        self.assertNotIn("16:40", active_daily)
        self.assertIn("16:45", active_daily)
        asyncio.run(active_daily["16:45"]())
        self.assertEqual(runs, ["daily"])
        self.assertIsNot(active_daily["16:45"], old_callback)

    def test_disabled_schedule_has_no_daily_callback_and_reactivation_registers_one(self):
        active_daily = {}
        def interval(value, callback): return lambda: None
        def daily(hour, minute, callback):
            key = f"{hour:02d}:{minute:02d}"; active_daily[key] = callback
            return lambda: active_daily.pop(key, None)

        schedule = NativeSchedule(interval, daily, lambda: None, lambda: None)
        schedule.configure(90, False, "16:40")
        self.assertEqual(active_daily, {})
        schedule.configure(90, True, "16:45")
        self.assertEqual(set(active_daily), {"16:45"})

    def test_daily_callback_drops_a_parallel_run(self):
        callbacks, started, release, runs = {}, asyncio.Event(), asyncio.Event(), []
        def interval(value, callback): return lambda: None
        def daily(hour, minute, callback):
            callbacks["daily"] = callback
            return lambda: callbacks.pop("daily", None)
        async def run_daily():
            runs.append("daily"); started.set(); await release.wait()

        schedule = NativeSchedule(interval, daily, lambda: None, run_daily)
        schedule.configure(90, True, "16:45")

        async def exercise():
            first = asyncio.create_task(callbacks["daily"]())
            await started.wait()
            await callbacks["daily"]()
            release.set()
            await first
        asyncio.run(exercise())
        self.assertEqual(runs, ["daily"])

    def test_daily_callback_waits_for_an_overlapping_history_run(self):
        callbacks, started, release, runs = {}, asyncio.Event(), asyncio.Event(), []
        def interval(value, callback): callbacks["history"] = callback; return lambda: None
        def daily(hour, minute, callback): callbacks["daily"] = callback; return lambda: None
        async def history(): started.set(); await release.wait(); runs.append("history")
        async def daily_run(): runs.append("daily")
        schedule = NativeSchedule(interval, daily, history, daily_run)
        schedule.configure(90, True, "16:45")
        async def exercise():
            first = asyncio.create_task(callbacks["history"]())
            await started.wait()
            queued = asyncio.create_task(callbacks["daily"]())
            await asyncio.sleep(0)
            self.assertFalse(queued.done())
            release.set()
            await first
            await queued
        asyncio.run(exercise())
        self.assertEqual(runs, ["history", "daily"])

    def test_history_gap_is_unknown_before_first_success_and_uses_grace_period(self):
        now = datetime(2026, 8, 10, tzinfo=timezone.utc)
        self.assertIsNone(history_gap(None, 90, now))
        self.assertFalse(history_gap(now - timedelta(minutes=105), 90, now))
        self.assertTrue(history_gap(now - timedelta(minutes=106), 90, now))
