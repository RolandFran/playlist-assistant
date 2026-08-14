"""Application-owned Preview/Publish workflow.

This is deliberately usable by the Ingress app and the HA bridge alike.  It
contains the Spotify pipeline; Home Assistant only decides when to call it.
"""
from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timedelta, timezone
from threading import Lock

from application_storage import ApplicationStorage
from db_state import get_current_input_fingerprint
from run import run_history, run_publish, run_score, run_sources
from client import SpotifyRateLimited
from runtime import JobResult


class PreviewRequiredError(RuntimeError):
    """Raised when Publish has no current persisted preview."""


class SourceSyncRequiredError(RuntimeError):
    """Raised when Preview is requested before source synchronization."""


class PlaylistWorkflow:
    """Serialize every Spotify/pipeline operation and own preview freshness."""

    def __init__(self, paths, *, storage=None, runners=None, now=None):
        self.paths = paths
        self.storage = storage or ApplicationStorage(paths.database_path)
        self.runners = runners or {
            "history": lambda: run_history(paths=paths),
            "sources": lambda: run_sources(paths=paths),
            "score": lambda config: run_score(config=config, paths=paths),
            "publish": lambda: run_publish(write=True, paths=paths),
        }
        self.now = now or (lambda: datetime.now(timezone.utc))
        self._lock = Lock()

    def fingerprint(self):
        data_fingerprint, _ = get_current_input_fingerprint(self.paths.database_path)
        config = self.storage.load_runtime_config()
        return hashlib.sha256((data_fingerprint + repr(config)).encode()).hexdigest()

    def preview_state(self):
        preview = self.storage.get_preview()
        if preview is None:
            return "idle"
        return "preview_ready" if preview.fingerprint == self.fingerprint() else "preview_stale"

    def sync(self):
        def work():
            self._run_history_step()
            try:
                self.runners["sources"]()
            except SpotifyRateLimited:
                raise
            except Exception as error:
                raise RuntimeError(f"Source sync failed: {error}") from error
        return self._execute("syncing", work)

    def preview(self):
        def work():
            if not self._has_source_schema():
                raise SourceSyncRequiredError(
                    "Source playlists have not been synchronized. Select Sync first."
                )
            self.runners["score"](self.storage.load_runtime_config())
            self.storage.save_preview(self.fingerprint(), self.now())
        return self._execute("previewing", work)

    def _has_source_schema(self):
        conn = sqlite3.connect(self.paths.database_path)
        try:
            return conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'playlist'"
            ).fetchone() is not None
        finally:
            conn.close()

    def publish(self):
        def work():
            if self.preview_state() != "preview_ready":
                raise PreviewRequiredError("Publish requires a current preview. Select Preview again after changing settings or synced data.")
            self.runners["publish"]()
        return self._execute("publishing", work)

    def run(self):
        def work():
            started_at = self.now()
            step = "history"
            try:
                self._run_history_step()
                step = "sources"
                self.runners["sources"]()
                step = "score"
                self.runners["score"](self.storage.load_runtime_config())
                self.storage.save_preview(self.fingerprint(), self.now())
                step = "publish"
                self.runners["publish"]()
            except Exception as error:
                self._record_job("today", False, started_at, failed_step=step, error=error)
                raise
            self._record_job("today", True, started_at)
        return self._execute("running", work)

    def _run_history_step(self):
        """Run History and persist its existing finite-job status contract."""
        started_at = self.now()
        try:
            self.runners["history"]()
        except Exception as error:
            self._record_job("history", False, started_at, failed_step="history", error=error)
            if isinstance(error, SpotifyRateLimited):
                raise
            raise RuntimeError(f"History sync failed: {error}") from error
        self._record_job("history", True, started_at)

    def _record_job(self, job_name, success, started_at, *, failed_step=None, error=None):
        """Keep status observational if SQLite status persistence ever fails."""
        ended_at = self.now()
        try:
            self.storage.record_job_result(JobResult(
                job_name=job_name,
                success=success,
                started_at=started_at,
                ended_at=ended_at,
                duration_seconds=(ended_at - started_at).total_seconds(),
                failed_step=failed_step,
                error=error,
            ))
        except Exception:
            pass

    def _execute(self, _state, work):
        # Blocking is intentional: every caller shares this one lock, so a
        # manual action cannot race a scheduled Spotify operation.
        with self._lock:
            deadline = self.storage.get_spotify_retry_after_until()
            if deadline:
                retry_at = datetime.fromisoformat(deadline)
                if self.now() < retry_at:
                    raise RuntimeError(
                        "Spotify ist wegen eines Rate Limits bis "
                        f"{retry_at.astimezone().strftime('%H:%M:%S')} gesperrt."
                    )
            try:
                return work()
            except SpotifyRateLimited as error:
                if error.retry_after is not None:
                    retry_at = self.now() + timedelta(seconds=error.retry_after)
                    self.storage.set_spotify_retry_after_until(retry_at)
                    raise RuntimeError(
                        "Spotify Rate Limit erreicht"
                        + (" (QUOTA_EXCEEDED)" if error.reason == "QUOTA_EXCEEDED" else "")
                        + f". Erneut möglich ab {retry_at.astimezone().strftime('%H:%M:%S')}."
                    ) from error
                raise
