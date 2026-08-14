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
        self._active_job = None

    async def _run_once(self, job_name, callback):
        """Drop overlapping HA callbacks instead of queuing another pipeline."""
        if self._running:
            LOGGER.info(
                "scheduled_run_skipped job=%s active_job=%s reason=overlap",
                job_name,
                self._active_job,
            )
            return
        self._running = True
        self._active_job = job_name
        LOGGER.info("scheduled_run_started job=%s", job_name)
        try:
            result = await callback()
        except Exception:
            LOGGER.exception("scheduled_run_failed job=%s", job_name)
            raise
        else:
            LOGGER.info("scheduled_run_completed job=%s", job_name)
            return result
        finally:
            self._running = False
            self._active_job = None

    async def _run_daily_once(self):
        """Do not lose the one daily run when a history callback overlaps it."""
        if self._running and self._active_job == "today":
            LOGGER.info("scheduled_run_skipped job=today active_job=today reason=overlap")
            return
        if self._running:
            LOGGER.info("scheduled_run_waiting job=today active_job=%s", self._active_job)
        while self._running:
            await asyncio.sleep(0.1)
        return await self._run_once("today", self._run_daily)

    async def _history_callback(self, *_):
        """Run the interval callback as a coroutine Home Assistant will await."""
        LOGGER.info("scheduled_callback_fired job=history")
        return await self._run_once("history", self._run_sync)

    async def _daily_callback(self, *_):
        """Run the daily callback as a coroutine Home Assistant will await."""
        LOGGER.info("scheduled_callback_fired job=today")
        return await self._run_daily_once()

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
        interval = timedelta(minutes=interval_minutes)
        self._unsubscribers.append(self._register_interval(interval, self._history_callback))
        LOGGER.info("history_schedule_registered interval_minutes=%s", interval_minutes)
        if daily_enabled:
            self._daily_unsubscriber = self._register_daily(hour, minute, self._daily_callback)
            LOGGER.info("daily_schedule_registered time=%s second=0", daily_time)
        else:
            LOGGER.info("daily_schedule_disabled")

    def stop(self):
        for unsubscribe in self._unsubscribers:
            unsubscribe()
            LOGGER.info("history_schedule_callback_removed")
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
