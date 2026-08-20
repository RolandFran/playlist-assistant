import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from application_paths import ApplicationPaths
from history_import import ensure_history_table
from ha_app.control_panel import ControlPanel, start_ingress


class HistoryDataManagementIngressTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.paths = ApplicationPaths.from_data_dir(self.directory.name)
        self.paths.ensure_runtime_directories()
        with closing(sqlite3.connect(self.paths.database_path)) as conn:
            ensure_history_table(conn)
            conn.execute("""INSERT INTO history (played_at, track_id, track_uri, track_name, artist_name) VALUES (?, ?, ?, ?, ?)""", ("2026-08-04T00:00:00Z", "id", "spotify:track:id", "Track", "Artist"))
            conn.commit()
        self.server = start_ingress(ControlPanel(self.paths, spotify_available=lambda: False), bridge_token="bridge", port=0, ingress_client_address="127.0.0.1")
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.directory.cleanup()

    def _request(self, path, *, data=None, headers=None):
        return urlopen(Request(self.base + path, data=data, headers=headers or {}))

    def _multipart(self, files):
        boundary = "history-boundary"
        body = b""
        for name, value in files:
            body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"files\"; filename=\"{name}\"\r\nContent-Type: application/json\r\n\r\n".encode()
            body += value + b"\r\n"
        return body + f"--{boundary}--\r\n".encode(), {"Content-Type": f"multipart/form-data; boundary={boundary}"}

    def test_export_download_is_utf8_json_and_accepts_the_inclusive_date_boundary(self):
        with self._request("/api/history/export?from_date=2026-08-04") as response:
            records = json.loads(response.read().decode("utf-8"))
            disposition = response.headers["Content-Disposition"]

        self.assertEqual(records[0]["ts"], "2026-08-04T00:00:00Z")
        self.assertEqual(records[0]["spotify_track_uri"], "spotify:track:id")
        self.assertIn("attachment", disposition)
        self.assertIn("2026-08-04", disposition)

    def test_import_reports_summary_and_rolls_back_a_failed_multi_file_batch(self):
        valid = json.dumps([{"ts": "2026-08-06T12:00:00Z", "spotify_track_uri": "spotify:track:new", "master_metadata_track_name": "New", "master_metadata_album_artist_name": "Artist"}]).encode()
        body, headers = self._multipart([("valid.json", valid), ("broken.json", b"{invalid")])

        with self._request("/api/history/import", data=body, headers=headers) as response:
            result = json.loads(response.read())["result"]

        self.assertFalse(result["success"])
        self.assertIn("Expecting", result["error"])
        with closing(sqlite3.connect(self.paths.database_path)) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM history").fetchone()[0], 1)

    def test_import_rejects_non_multipart_payloads(self):
        with self.assertRaises(HTTPError) as caught:
            self._request("/api/history/import", data=b"[]", headers={"Content-Type": "application/json"})
        self.assertEqual(caught.exception.code, 400)


class HistoryDataManagementUiTests(unittest.TestCase):
    def test_data_management_ui_has_separate_export_and_multi_file_import_controls(self):
        root = Path(__file__).resolve().parents[1] / "ha_app" / "ui"
        html = (root / "index.html").read_text(encoding="utf-8")
        app = (root / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="data-management-section"', html)
        self.assertIn("dataManagement()", app)
        self.assertIn("files.multiple=true", app)
        self.assertIn("FormData", app)
        self.assertIn("api/history/export", app)
        self.assertIn("api/history/import", app)
