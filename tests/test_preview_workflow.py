from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from application_paths import ApplicationPaths
from workflow import PlaylistWorkflow, PreviewRequiredError


class PreviewWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(); self.paths = ApplicationPaths.from_data_dir(self.temp.name)
        self.calls = []
        self.value = "one"
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
