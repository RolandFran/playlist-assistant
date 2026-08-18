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

    async def _run_once(self, callback, job_name=None):
        """Drop overlapping HA callbacks instead of queuing another pipeline."""
        if self._running:
            return
        self._running = True
        self._active_callback = callback
        try:
            if job_name == "today":
                LOGGER.info("daily_run_callback_invoking")
            return await callback()
        finally:
            self._running = False
            self._active_callback = None

    async def _run_daily_once(self, callback):
        """Do not lose the one daily run when a history callback overlaps it."""
        LOGGER.info("daily_run_once_entered")
        if self._running and self._active_callback == callback:
            return
        while self._running:
            await asyncio.sleep(0.1)
        return await self._run_once(callback, job_name="today")

    async def _interval_callback(self, *_):
        """Run the interval callback through Home Assistant's async path."""
        return await self._run_once(self._run_sync)

    async def _daily_callback(self, *_):
        """Run the daily callback as a coroutine Home Assistant will await."""
        LOGGER.info("daily_schedule_callback_wrapper_entered")
        return await self._run_daily_once(self._run_daily)

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
        self._unsubscribers.append(
            self._register_interval(
                timedelta(minutes=interval_minutes), self._interval_callback
            )
        )
        if daily_enabled:
            self._daily_unsubscriber = self._register_daily(hour, minute, self._daily_callback)
            LOGGER.info(
                "daily_schedule_callback_registered hour=%s minute=%s second=0",
                hour,
                minute,
            )
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
