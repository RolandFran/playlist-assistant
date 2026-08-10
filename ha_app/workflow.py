"""Application-owned Preview/Publish workflow.

This is deliberately usable by the Ingress app and the HA bridge alike.  It
contains the Spotify pipeline; Home Assistant only decides when to call it.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from threading import Lock

from application_storage import ApplicationStorage
from db_state import get_current_input_fingerprint
from run import run_history, run_publish, run_score, run_sources


class PreviewRequiredError(RuntimeError):
    """Raised when Publish has no current persisted preview."""


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
        return self._execute("syncing", lambda: self.runners["history"]())

    def preview(self):
        def work():
            self.runners["score"](self.storage.load_runtime_config())
            self.storage.save_preview(self.fingerprint(), self.now())
        return self._execute("previewing", work)

    def publish(self):
        def work():
            if self.preview_state() != "preview_ready":
                raise PreviewRequiredError("Publish requires a current preview. Select Preview again after changing settings or synced data.")
            self.runners["publish"]()
        return self._execute("publishing", work)

    def run(self):
        def work():
            self.runners["history"]()
            self.runners["sources"]()
            self.runners["score"](self.storage.load_runtime_config())
            self.storage.save_preview(self.fingerprint(), self.now())
            self.runners["publish"]()
        return self._execute("running", work)

    def _execute(self, _state, work):
        # Blocking is intentional: every caller shares this one lock, so a
        # manual action cannot race a scheduled Spotify operation.
        with self._lock:
            return work()
