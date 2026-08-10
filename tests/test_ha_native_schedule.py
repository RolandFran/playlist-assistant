from datetime import datetime, timedelta, timezone
import unittest

from custom_components.playlist_assistant.native import NativeSchedule, history_gap


class NativeScheduleTests(unittest.TestCase):
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

    def test_history_gap_is_unknown_before_first_success_and_uses_grace_period(self):
        now = datetime(2026, 8, 10, tzinfo=timezone.utc)
        self.assertIsNone(history_gap(None, 90, now))
        self.assertFalse(history_gap(now - timedelta(minutes=105), 90, now))
        self.assertTrue(history_gap(now - timedelta(minutes=106), 90, now))
