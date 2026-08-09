"""Persistent policy for explicitly invoked Playlist Assistant scheduling.

This module decides which finite runtime job is due.  It intentionally owns no
background loop, thread, service, or Home Assistant integration.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable

from application_storage import ApplicationStorage
from runtime_config import RuntimeConfig


@dataclass(frozen=True)
class ScheduledRun:
    """One job started by the scheduler policy."""

    job_name: str
    result: object


class SchedulerPolicy:
    """Run due finite jobs using persisted attempts and an injectable clock."""

    def __init__(
        self,
        *,
        runtime,
        storage: ApplicationStorage,
        now: Callable[[], datetime] | None = None,
    ):
        self._runtime = runtime
        self._storage = storage
        self._now = now or (lambda: datetime.now().astimezone())

    def run_due(self, config: RuntimeConfig | None = None) -> list[ScheduledRun]:
        """Run each due scheduled slot at most once and return its outcomes.

        ``now`` must return an aware datetime in the host's local timezone.
        Attempt state is written after execution, so a completed failure waits
        for the next normal history interval or the next daily Today slot.
        """
        local_now = self._now()
        _require_aware_datetime(local_now)
        config = config or self._storage.load_runtime_config()
        state = self._storage.get_scheduler_state()
        today_due = config.today_schedule_enabled and _today_is_due(
            local_now, config.today_schedule_time, state.last_today_attempt_date
        )
        history_due = _history_is_due(
            local_now, config.history_poll_minutes, state.last_history_attempt_at
        )

        runs = []
        if today_due:
            # The existing Today pipeline begins with History.  Recording both
            # attempts avoids scheduling a second History pass beside it.
            result = self._runtime.run_today(write=True, config=config)
            self._storage.record_scheduler_attempts(
                history_attempt_at=local_now,
                today_attempt_date=local_now.date().isoformat(),
            )
            runs.append(ScheduledRun("today", result))
            return runs

        if history_due:
            result = self._runtime.run_history()
            self._storage.record_scheduler_attempts(history_attempt_at=local_now)
            runs.append(ScheduledRun("history", result))
        return runs


def _history_is_due(now: datetime, interval_minutes: int, last_attempt: str | None) -> bool:
    if last_attempt is None:
        return True
    previous = datetime.fromisoformat(last_attempt)
    _require_aware_datetime(previous)
    return now >= previous + timedelta(minutes=interval_minutes)


def _today_is_due(now: datetime, schedule_time: str, last_attempt_date: str | None) -> bool:
    hour, minute = (int(part) for part in schedule_time.split(":"))
    return (
        now.date().isoformat() != last_attempt_date
        and (now.hour, now.minute) >= (hour, minute)
    )


def _require_aware_datetime(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Scheduler time must be timezone-aware.")
