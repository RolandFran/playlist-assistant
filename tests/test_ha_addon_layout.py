from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "ha_app"


class HomeAssistantAddonLayoutTests(unittest.TestCase):
    def test_addon_build_context_contains_runtime_and_dependencies(self):
        dockerfile = (ADDON / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("FROM ghcr.io/home-assistant/base:latest", dockerfile)
        self.assertIn("COPY requirements.txt /tmp/requirements.txt", dockerfile)
        self.assertNotIn("../", dockerfile)
        self.assertIn('CMD ["/app/run.sh"]', dockerfile)
        for name in (
            "requirements.txt", "service.py", "control_panel.py", "workflow.py",
            "run.py", "application_paths.py", "application_storage.py",
            "runtime.py", "runtime_config.py", "db_state.py", "collector.py",
            "sync.py", "scoring.py", "publish.py", "client.py",
        ):
            self.assertTrue((ADDON / name).is_file(), name)
