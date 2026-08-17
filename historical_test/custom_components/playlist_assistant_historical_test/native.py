"""HA-independent native scheduling and state rules, kept easy to test."""
from __future__ import annotations
from datetime import timedelta
import asyncio
import logging


LOGGER = logging.getLogger(__name__)

from .const import HISTORY_GRACE_MINUTES

class NativeSchedule:
    def __init__(self, register_interval, register_daily, run_sync, run_daily):
        self._register_interval, self._register_daily = register_interval, register_daily
        self._run_sync, self._run_daily = run_sync, run_daily
        self._unsubscribers = []
        self._daily_unsubscriber = None
        self._running = False
        self._active_callback = None

    async def _run_once(self, callback):
        """Drop overlapping HA callbacks instead of queuing another pipeline."""
        if self._running:
            return
        self._running = True
        self._active_callback = callback
        try:
            return await callback()
        finally:
            self._running = False
            self._active_callback = None

    async def _run_daily_once(self, callback):
        """Do not lose the one daily run when a history callback overlaps it."""
        if self._running and self._active_callback == callback:
            return
        while self._running:
            await asyncio.sleep(0.1)
        return await self._run_once(callback)

    def configure(self, interval_minutes, daily_enabled, daily_time):
        """Replace callbacks immediately when persisted cadence changes."""
        # Validate before removing the working callback, so malformed service
        # data cannot silently leave scheduling disabled.
        if interval_minutes <= 0:
            raise ValueError("history_interval_minutes must be positive")
        if daily_enabled:
            hour, minute = map(int, daily_time.split(":"))
            if not 0 <= hour <= 23 or not 0 <= minute <= 59:
                raise ValueError("daily_time must be HH:MM")
        self.stop()
        self._unsubscribers.append(self._register_interval(timedelta(minutes=interval_minutes), lambda *_: self._run_once(self._run_sync)))
        if daily_enabled:
            self._daily_unsubscriber = self._register_daily(hour, minute, lambda *_: self._run_daily_once(self._run_daily))
            LOGGER.info("daily_schedule_registered time=%s second=0", daily_time)
        else:
            LOGGER.info("daily_schedule_disabled")

    def stop(self):
        for unsubscribe in self._unsubscribers:
            unsubscribe()
        self._unsubscribers = []
        if self._daily_unsubscriber is not None:
            self._daily_unsubscriber()
            LOGGER.info("daily_schedule_callback_removed")
        self._daily_unsubscriber = None

def history_gap(last_success, interval_minutes, now):
    """None is HA unknown; a first run must not look like a fault."""
    if last_success is None:
        return None
    return now > last_success + timedelta(minutes=interval_minutes + HISTORY_GRACE_MINUTES)
