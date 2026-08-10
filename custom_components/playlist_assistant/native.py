"""HA-independent native scheduling and state rules, kept easy to test."""
from __future__ import annotations
from datetime import timedelta

from .const import HISTORY_GRACE_MINUTES

class NativeSchedule:
    def __init__(self, register_interval, register_daily, run_sync, run_daily):
        self._register_interval, self._register_daily = register_interval, register_daily
        self._run_sync, self._run_daily = run_sync, run_daily
        self._unsubscribers = []

    def configure(self, interval_minutes, daily_enabled, daily_time):
        self.stop()
        self._unsubscribers.append(self._register_interval(timedelta(minutes=interval_minutes), self._run_sync))
        if daily_enabled:
            hour, minute = map(int, daily_time.split(":"))
            self._unsubscribers.append(self._register_daily(hour, minute, self._run_daily))

    def stop(self):
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers = []

def history_gap(last_success, interval_minutes, now):
    """None is HA unknown; a first run must not look like a fault."""
    if last_success is None:
        return None
    return now > last_success + timedelta(minutes=interval_minutes + HISTORY_GRACE_MINUTES)
