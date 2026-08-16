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
        self.assertIn("RUN chmod +x /app/run.sh", dockerfile)
        self.assertIn('CMD ["/app/run.sh"]', dockerfile)
        config = (ADDON / "config.yaml").read_text(encoding="utf-8")
        self.assertIn("ingress: true", config)
        self.assertIn("ingress_port: 8098", config)
        self.assertIn('version: "0.1.31"', config)
        self.assertIn('panel_icon: mdi:play', config)
        for legacy_option in ("spotify_client_id", "spotify_client_secret", "bridge_token"):
            self.assertIn(legacy_option, config)
        service = (ADDON / "service.py").read_text(encoding="utf-8")
        self.assertIn("health_endpoint_started port=%d path=/health", service)
        self.assertIn("ingress_control_panel_started port=%d path=/", service)
        panel = (ADDON / "control_panel.py").read_text(encoding="utf-8")
        self.assertIn("INGRESS_PORT = 8098", panel)
        frontend = (ADDON / "ui" / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("api('/api/", frontend)
        self.assertIn("if(!response.ok)", frontend)
        self.assertIn("target_playlist_name", frontend)
        self.assertIn("today_schedule_enabled", frontend)
        self.assertIn('type=\'range\'', frontend)
        self.assertIn("relativeDate", frontend)
        self.assertIn("reset-sorting", frontend)
        self.assertNotIn("pairing-file", frontend)
        self.assertNotIn("spotify/import", frontend)
        panel = (ADDON / "ui" / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-i18n="playlist_preview"', panel)
        self.assertIn('class="dashboard-grid"', panel)
        self.assertIn('class="playlist-preview"', panel)
        self.assertIn('id="reset-sorting"', panel)
        self.assertIn('class="dashboard-sidebar"', panel)
        self.assertLess(panel.index('class="playlist-preview"'), panel.index('class="dashboard-sidebar"'))
        self.assertNotIn('data-i18n="today"', panel)
        stylesheet = (ADDON / "ui" / "app.css").read_text(encoding="utf-8")
        self.assertIn('grid-template-columns:minmax(0,1.85fr) minmax(18rem,1fr)', stylesheet)
        self.assertIn('.playlist-preview{max-height:calc(100vh - 7rem);overflow-y:auto}', stylesheet)
        self.assertIn('.dashboard-sidebar{position:sticky', stylesheet)
        self.assertIn('@media (max-width:900px){', stylesheet)
        self.assertIn('.dashboard-grid{grid-template-columns:1fr}', stylesheet)
        polish = (ADDON / "ui" / "polish.css").read_text(encoding="utf-8")
        self.assertIn("table-layout: fixed", polish)
        self.assertIn("white-space: nowrap", polish)
        for name in (
            "requirements.txt", "service.py", "control_panel.py", "workflow.py",
            "run.py", "application_paths.py", "application_storage.py",
            "runtime.py", "runtime_config.py", "db_state.py", "collector.py",
            "sync.py", "scoring.py", "publish.py", "client.py",
        ):
            self.assertTrue((ADDON / name).is_file(), name)
