"""Scheduler-ready orchestration for Playlist Assistant jobs.

This module intentionally executes explicit, finite jobs only. Scheduling and
Home Assistant integration can invoke it later without duplicating pipeline
ordering or overlap protection.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Callable, Optional

from runtime_config import DEFAULT_HISTORY_POLL_MINUTES


@dataclass(frozen=True)
class JobResult:
    """Outcome metadata for one runtime job invocation."""

    job_name: str
    success: bool
    started_at: datetime
    ended_at: datetime
    duration_seconds: float
    failed_step: Optional[str] = None
    error: Optional[Exception] = None


class RuntimeOrchestrator:
    """Run finite jobs while preventing same-job overlap in one process."""

    def __init__(
        self,
        *,
        history_runner: Callable[..., None],
        sources_runner: Callable[..., None],
        score_runner: Callable[..., None],
        publish_runner: Callable[..., None],
        now: Callable[[], datetime] | None = None,
        status_store=None,
    ):
        self._history_runner = history_runner
        self._sources_runner = sources_runner
        self._score_runner = score_runner
        self._publish_runner = publish_runner
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._status_store = status_store
        self._active_jobs: set[str] = set()
        self._active_jobs_lock = Lock()
        self._pipeline_lock = Lock()

    def run_history(self, *, recover_after=None) -> JobResult:
        """Run one history synchronization pass."""
        return self._run_job(
            "history",
            (("history", lambda: self._history_runner(recover_after=recover_after)),),
        )

    def run_today(
        self,
        *,
        write=False,
        force_full_sources=False,
        config=None,
    ) -> JobResult:
        """Run the ordered History → Sources → Scoring → Publish pipeline."""
        return self._run_job(
            "today",
            (
                ("history", lambda: self._history_runner()),
                ("sources", lambda: self._sources_runner(force_full=force_full_sources)),
                ("score", lambda: self._score_runner(config=config)),
                ("publish", lambda: self._publish_runner(write=write)),
            ),
        )

    def _run_job(self, job_name: str, steps) -> JobResult:
        started_at = self._now()

        with self._active_jobs_lock:
            if self._active_jobs:
                active = next(iter(self._active_jobs))
                error = RuntimeError(f"Job {active!r} is already running.")
                return self._complete(self._result(
                    job_name,
                    False,
                    started_at,
                    failed_step=job_name,
                    error=error,
                ))

            self._active_jobs.add(job_name)

        try:
            for step_name, step in steps:
                try:
                    step()
                except Exception as error:
                    return self._complete(self._result(
                        job_name,
                        False,
                        started_at,
                        failed_step=step_name,
                        error=error,
                    ))

            return self._complete(self._result(job_name, True, started_at))
        finally:
            with self._active_jobs_lock:
                self._active_jobs.remove(job_name)

    def _complete(self, result: JobResult) -> JobResult:
        """Optionally persist the result without changing job execution behavior."""
        if self._status_store is not None:
            try:
                self._status_store.record_job_result(result)
            except Exception:
                # Status is observational; a storage failure must not change
                # the finite job's existing result or overlap behavior.
                pass
        return result

    def _result(
        self,
        job_name: str,
        success: bool,
        started_at: datetime,
        *,
        failed_step: Optional[str] = None,
        error: Optional[Exception] = None,
    ) -> JobResult:
        ended_at = self._now()
        return JobResult(
            job_name=job_name,
            success=success,
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=(ended_at - started_at).total_seconds(),
            failed_step=failed_step,
            error=error,
        )
