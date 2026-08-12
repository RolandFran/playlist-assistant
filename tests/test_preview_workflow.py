from datetime import datetime, timezone
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from application_paths import ApplicationPaths
from sync import create_tables
from workflow import PlaylistWorkflow, PreviewRequiredError, SourceSyncRequiredError


class PreviewWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(); self.paths = ApplicationPaths.from_data_dir(self.temp.name)
        self.calls = []
        self.value = "one"
        conn = sqlite3.connect(self.paths.database_path)
        try:
            create_tables(conn)
            conn.commit()
        finally:
            conn.close()
        self.flow = PlaylistWorkflow(self.paths, runners={
            "history": lambda: self.calls.append("history"), "sources": lambda: self.calls.append("sources"),
            "score": lambda config: self.calls.append("score"), "publish": lambda: self.calls.append("publish"),
        }, now=lambda: datetime(2026, 8, 10, tzinfo=timezone.utc))
        self.patch = patch.object(self.flow, "fingerprint", side_effect=lambda: self.value); self.patch.start()

    def tearDown(self): self.patch.stop(); self.temp.cleanup()

    def test_preview_is_persisted_then_stale_when_inputs_change(self):
        self.flow.preview()
        self.assertEqual(self.flow.preview_state(), "preview_ready")
        self.value = "two"
        self.assertEqual(self.flow.preview_state(), "preview_stale")

    def test_publish_requires_current_preview(self):
        with self.assertRaises(PreviewRequiredError): self.flow.publish()
        self.flow.preview(); self.flow.publish()
        self.assertEqual(self.calls, ["score", "publish"])

    def test_run_performs_the_complete_ordered_pipeline(self):
        self.flow.run()
        self.assertEqual(self.calls, ["history", "sources", "score", "publish"])

    def test_sync_performs_history_and_source_sync(self):
        self.flow.sync()
        self.assertEqual(self.calls, ["history", "sources"])

    def test_preview_on_a_fresh_database_explains_that_sync_is_required(self):
        fresh = TemporaryDirectory()
        self.addCleanup(fresh.cleanup)
        paths = ApplicationPaths.from_data_dir(fresh.name)
        calls = []
        flow = PlaylistWorkflow(paths, runners={
            "history": lambda: calls.append("history"),
            "sources": lambda: calls.append("sources"),
            "score": lambda config: calls.append("score"),
            "publish": lambda: calls.append("publish"),
        })

        with self.assertRaisesRegex(SourceSyncRequiredError, "Select Sync first"):
            flow.preview()

        self.assertEqual(calls, [])
