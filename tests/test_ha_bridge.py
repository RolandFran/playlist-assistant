import json
import tempfile
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from application_paths import ApplicationPaths
from ha_app.control_panel import ControlPanel, start_ingress


class _Workflow:
    def __init__(self): self.calls = []
    def preview_state(self): return "idle"
    def sync(self): self.calls.append("sync")
    def preview(self): self.calls.append("preview")
    def publish(self): self.calls.append("publish")
    def run(self): self.calls.append("run")

class AddonBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); paths = ApplicationPaths.from_data_dir(self.temp.name); paths.ensure_runtime_directories()
        self.workflow = _Workflow(); self.changes = []
        self.panel = ControlPanel(paths, spotify_available=lambda: True, workflow=self.workflow, schedule_changed=self.changes.append)
        self.server = start_ingress(self.panel, bridge_token="bridge-secret")
        self.base = f"http://127.0.0.1:{self.server.server_port}"
    def tearDown(self): self.server.shutdown(); self.server.server_close(); self.temp.cleanup()
    def request(self, path, method="GET", body=None, token="bridge-secret"):
        request = Request(self.base + path, data=body, method=method, headers={"X-Playlist-Assistant-Bridge": token})
        return json.loads(urlopen(request).read())
    def test_private_bridge_actions_reach_the_existing_workflow(self):
        self.request("/bridge/actions/run", "POST")
        self.assertEqual(self.workflow.calls, ["run"])
        self.assertEqual(self.request("/bridge/state")["spotify"]["state"], "connected")
    def test_bridge_rejects_wrong_secret_and_ingress_save_notifies_ha(self):
        with self.assertRaises(HTTPError): self.request("/bridge/state", token="wrong")
        self.panel.save_settings({"history_poll_minutes": 30, "today_schedule_time": "05:30"})
        self.assertEqual(self.changes[-1].history_poll_minutes, 30)
