"""Ingress-only daily control surface built on the existing engine boundaries."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Callable

from application_paths import ApplicationPaths
from application_storage import ApplicationStorage
from runtime_config import RuntimeConfig
from run import run_history, run_publish, run_score, run_sources


INGRESS_PORT = 8098
APP_DIR = Path(__file__).parent


class ControlPanel:
    """Read and change only persistent app state under the selected data path."""

    def __init__(self, paths: ApplicationPaths, *, spotify_available: Callable[[], bool]):
        self.paths = paths
        self.storage = ApplicationStorage(paths.database_path)
        self.spotify_available = spotify_available

    def state(self) -> dict:
        config = self.storage.load_runtime_config()
        target_name, target_id = self.storage.get_target_playlist()
        history = self.storage.get_job_status("history")
        today = self.storage.get_job_status("today")
        scheduler = self.storage.get_scheduler_state()
        tracks = self._today_tracks()
        available = self.spotify_available()
        return {
            "spotify": {"state": "connected" if available else "not_connected", "available": available},
            "settings": {**config.__dict__, "long_weight": config.long_weight, "target_playlist_name": target_name},
            "target_playlist_id": target_id,
            "jobs": {"history": history.to_dict() if history else None, "today": today.to_dict() if today else None},
            "next": self._next_runs(config, scheduler.last_history_attempt_at, scheduler.last_today_attempt_date),
            "today": {"count": len(tracks), "tracks": tracks},
        }

    def save_settings(self, values: dict) -> dict:
        current = self.storage.load_runtime_config()
        config = RuntimeConfig(
            today_size=int(values.get("today_size", current.today_size)),
            rare_weight=int(values.get("rare_weight", current.rare_weight)),
            artist_gap=int(values.get("artist_gap", current.artist_gap)),
            history_poll_minutes=current.history_poll_minutes,
            today_schedule_enabled=bool(values.get("today_schedule_enabled", current.today_schedule_enabled)),
            today_schedule_time=str(values.get("today_schedule_time", current.today_schedule_time)),
        )
        target_name = str(values.get("target_playlist_name", self.storage.get_target_playlist()[0])).strip()
        self.storage.save_runtime_config(config)
        self.storage.save_target_playlist(target_name)
        return self.state()

    def run_action(self, action: str) -> dict:
        if action == "calculate":
            run_score(config=self.storage.load_runtime_config(), paths=self.paths)
        else:
            if not self.spotify_available():
                raise RuntimeError("Spotify is not connected. Authorization is required for this action.")
            if action == "history":
                run_history(paths=self.paths)
            elif action == "sources":
                run_sources(paths=self.paths)
            elif action == "publish":
                run_publish(write=True, paths=self.paths)
            else:
                raise ValueError("Unknown action.")
        return self.state()

    def _today_tracks(self) -> list[dict]:
        try:
            payload = json.loads(self.paths.today_tracks_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return []
        tracks = [item for item in payload.get("tracks", []) if isinstance(item, dict)]
        uris = [item.get("track_uri") for item in tracks if item.get("track_uri")]
        last_played = {}
        if uris:
            try:
                with sqlite3.connect(self.paths.database_path) as conn:
                    marks = ",".join("?" for _ in uris)
                    last_played = dict(conn.execute(
                        f"SELECT track_uri, MAX(played_at) FROM history WHERE track_uri IN ({marks}) GROUP BY track_uri", uris
                    ))
            except sqlite3.Error:
                pass
        return [{key: item.get(key) for key in ("track_name", "artist_name", "combined_score", "play_count")} | {"last_played": last_played.get(item.get("track_uri"))} for item in tracks]

    @staticmethod
    def _next_runs(config, history_attempt, today_attempt_date) -> dict:
        history_next = None
        if history_attempt:
            history_next = (datetime.fromisoformat(history_attempt) + timedelta(minutes=config.history_poll_minutes)).isoformat()
        today_next = None if not config.today_schedule_enabled else config.today_schedule_time
        return {"history": history_next or "due", "today": today_next, "last_today_attempt_date": today_attempt_date}


def start_ingress(panel: ControlPanel) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def _allow_ingress(self):
            if self.client_address[0] != "172.30.32.2":
                self.send_error(HTTPStatus.FORBIDDEN)
                return False
            return True
        def _json(self, status, value):
            data = json.dumps(value).encode("utf-8")
            self.send_response(status); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
        def do_GET(self):  # noqa: N802
            if not self._allow_ingress(): return
            if self.path.startswith("/api/state"):
                return self._json(200, panel.state())
            if self.path.startswith("/api/i18n/"):
                lang = "de" if self.path.endswith("/de") else "en"
                return self._json(200, json.loads((APP_DIR / "ui" / "i18n" / f"{lang}.json").read_text(encoding="utf-8")))
            if self.path == "/" or self.path.startswith("/?"):
                return self._file("index.html", "text/html")
            if self.path == "/app.js": return self._file("app.js", "application/javascript")
            if self.path == "/app.css": return self._file("app.css", "text/css")
            self.send_error(404)
        def do_POST(self):  # noqa: N802
            if not self._allow_ingress(): return
            try:
                size = int(self.headers.get("Content-Length", "0")); data = json.loads(self.rfile.read(size) or b"{}")
                if self.path == "/api/settings": return self._json(200, panel.save_settings(data))
                if self.path.startswith("/api/actions/"): return self._json(200, panel.run_action(self.path.rsplit("/", 1)[-1]))
                self.send_error(404)
            except (ValueError, RuntimeError) as error:
                self._json(400, {"error": str(error)})
        def _file(self, name, content_type):
            data = (APP_DIR / "ui" / name).read_bytes(); self.send_response(200); self.send_header("Content-Type", content_type); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
        def log_message(self, *_): pass
    server = ThreadingHTTPServer(("0.0.0.0", INGRESS_PORT), Handler)
    Thread(target=server.serve_forever, daemon=True).start()
    return server
