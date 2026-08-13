"""Ingress-only daily control surface built on the existing engine boundaries."""

from __future__ import annotations

import json
import hmac
import logging
import sqlite3
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Callable
from urllib.parse import urlsplit

from application_paths import ApplicationPaths
from application_storage import ApplicationStorage
from runtime_config import RuntimeConfig
from workflow import PlaylistWorkflow


INGRESS_PORT = 8098
APP_DIR = Path(__file__).parent
LOGGER = logging.getLogger("playlist_assistant.control_panel")


class SettingsError(ValueError):
    """A settings error that the Ingress client can attach to one field."""

    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.field = field


class ControlPanel:
    """Read and change only persistent app state under the selected data path."""

    def __init__(self, paths: ApplicationPaths, *, spotify_available: Callable[[], bool], workflow=None,
                 schedule_changed=None):
        self.paths = paths
        self.storage = ApplicationStorage(paths.database_path)
        self.spotify_available = spotify_available
        self.workflow = workflow or PlaylistWorkflow(paths, storage=self.storage)
        self.schedule_changed = schedule_changed or (lambda _config: None)

    def state(self) -> dict:
        config = self.storage.load_runtime_config()
        target_name, target_id = self.storage.get_target_playlist()
        history = self.storage.get_job_status("history")
        today = self.storage.get_job_status("today")
        tracks = self._today_tracks()
        # The first Ingress request must always be JSON serializable.  Keep the
        # service-owned callbacks at this API boundary constrained to the
        # documented primitive values the frontend consumes.
        available = bool(self.spotify_available())
        return {
            "spotify": {"state": "connected" if available else "not_connected", "available": available},
            "settings": {**config.__dict__, "long_weight": config.long_weight, "target_playlist_name": target_name},
            "target_playlist_id": target_id,
            "jobs": {"history": history.to_dict() if history else None, "today": today.to_dict() if today else None},
            "schedule": {"history_interval_minutes": config.history_poll_minutes, "daily_enabled": config.today_schedule_enabled, "daily_time": config.today_schedule_time},
            "preview": {"state": self.workflow.preview_state()},
            "today": {"count": len(tracks), "tracks": tracks},
        }

    def save_settings(self, values: dict) -> dict:
        current = self.storage.load_runtime_config()
        try:
            config = RuntimeConfig(
                today_size=int(values.get("today_size", current.today_size)),
                rare_weight=int(values.get("rare_weight", current.rare_weight)),
                artist_gap=int(values.get("artist_gap", current.artist_gap)),
                history_poll_minutes=int(values.get("history_poll_minutes", current.history_poll_minutes)),
                today_schedule_enabled=_as_bool(values.get("today_schedule_enabled", current.today_schedule_enabled)),
                today_schedule_time=str(values.get("today_schedule_time", current.today_schedule_time)),
            )
        except (TypeError, ValueError) as error:
            raise SettingsError(str(error), _settings_field(str(error))) from error
        _require_limits(config)
        target_name = str(values.get("target_playlist_name", self.storage.get_target_playlist()[0])).strip()
        if not target_name:
            raise SettingsError("Target playlist name must not be blank.", "target_playlist_name")
        old_target_name, old_target_id = self.storage.get_target_playlist()
        try:
            self.storage.save_runtime_config(config)
            self.storage.save_target_playlist(target_name)
            self.schedule_changed(config)
        except Exception as error:
            # A schedule request that HA rejects must not look saved in the UI
            # or survive as a configuration which HA never activated.
            self.storage.save_runtime_config(current)
            self.storage.save_target_playlist(old_target_name, old_target_id)
            LOGGER.warning("settings_save_failed error_type=%s", type(error).__name__)
            raise SettingsError(str(error), "today_schedule_time") from error
        active_daily = config.today_schedule_time if config.today_schedule_enabled else "disabled"
        LOGGER.info("settings_saved active_daily_schedule=%s", active_daily)
        return self.state()

    def run_action(self, action: str) -> dict:
        if not self.spotify_available():
            raise RuntimeError("Spotify is not connected. Authorization is required for this action.")
        actions = {"sync": self.workflow.sync, "preview": self.workflow.preview, "publish": self.workflow.publish, "run": self.workflow.run}
        try:
            actions[action]()
        except KeyError as error:
            raise ValueError("Unknown action.") from error
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


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    raise ValueError("today_schedule_enabled must be true or false.")


def _settings_field(message: str) -> str | None:
    return next((name for name in ("today_size", "rare_weight", "artist_gap", "history_poll_minutes", "today_schedule_enabled", "today_schedule_time") if name in message), None)


def _require_limits(config: RuntimeConfig) -> None:
    limits = {"today_size": (1, 1000), "artist_gap": (0, 100), "history_poll_minutes": (1, 1440)}
    for name, (minimum, maximum) in limits.items():
        value = getattr(config, name)
        if not minimum <= value <= maximum:
            raise SettingsError(f"{name} must be between {minimum} and {maximum}.", name)

def start_ingress(panel: ControlPanel, *, bridge_token: str, port: int = INGRESS_PORT,
                  ingress_client_address: str = "172.30.32.2") -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def _allow_ingress(self, *, api=False):
            if self.client_address[0] != ingress_client_address:
                if api:
                    self._api_error(HTTPStatus.FORBIDDEN, "Ingress access is required.")
                else:
                    self.send_error(HTTPStatus.FORBIDDEN)
                return False
            return True
        def _allow_bridge(self):
            supplied = self.headers.get("X-Playlist-Assistant-Bridge", "")
            if not hmac.compare_digest(supplied, bridge_token):
                self.send_error(HTTPStatus.FORBIDDEN)
                return False
            return True
        def _json(self, status, value):
            data = json.dumps(value).encode("utf-8")
            self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
        def _api_error(self, status, message):
            self._json(status, {"error": message})
        def _ingress_base_path(self):
            path = self.headers.get("X-Ingress-Path", "/")
            if not path.startswith("/") or path.startswith("//"):
                return "/"
            return path.rstrip("/") + "/"
        def do_GET(self):  # noqa: N802
            path = urlsplit(self.path).path
            if path == "/bridge/state":
                if self._allow_bridge(): self._json(200, panel.state())
                return
            if not self._allow_ingress(api=path.startswith("/api/")): return
            if path == "/api/state":
                return self._json(200, panel.state())
            if path in ("/api/i18n/de", "/api/i18n/en"):
                lang = path.rsplit("/", 1)[-1]
                return self._json(200, json.loads((APP_DIR / "ui" / "i18n" / f"{lang}.json").read_text(encoding="utf-8")))
            if path.startswith("/api/"):
                return self._api_error(HTTPStatus.NOT_FOUND, "Unknown API endpoint.")
            if path == "/":
                return self._file("index.html", "text/html; charset=utf-8", ingress_base_path=self._ingress_base_path())
            if path == "/app.js": return self._file("app.js", "application/javascript; charset=utf-8")
            if path == "/app.css": return self._file("app.css", "text/css; charset=utf-8")
            if path == "/polish.css": return self._file("polish.css", "text/css; charset=utf-8")
            self.send_error(404)
        def do_POST(self):  # noqa: N802
            path = urlsplit(self.path).path
            if path.startswith("/bridge/actions/"):
                if not self._allow_bridge(): return
                try: return self._json(200, panel.run_action(path.rsplit("/", 1)[-1]))
                except (ValueError, RuntimeError) as error: return self._json(400, {"error": str(error)})
            if not self._allow_ingress(api=path.startswith("/api/")): return
            try:
                # Actions are server-side triggers. The Ingress UI deliberately
                # posts no payload, so body validation applies only to settings.
                if path.startswith("/api/actions/"):
                    return self._json(200, panel.run_action(path.rsplit("/", 1)[-1]))
                size = int(self.headers.get("Content-Length", "0"))
                if size < 1 or size > 64 * 1024: raise ValueError("Invalid upload size.")
                data = json.loads(self.rfile.read(size) or b"{}")
                if not isinstance(data, dict):
                    raise ValueError("JSON request body must be an object.")
                if path == "/api/settings":
                    return self._json(200, {"ok": True, "message": "Settings saved.", "state": panel.save_settings(data)})
                if path.startswith("/api/"): return self._api_error(HTTPStatus.NOT_FOUND, "Unknown API endpoint.")
                self.send_error(404)
            except (ValueError, RuntimeError) as error:
                payload = {"error": str(error)}
                if isinstance(error, SettingsError) and error.field:
                    payload["field"] = error.field
                self._json(400, payload)
        def _file(self, name, content_type, ingress_base_path=None):
            data = (APP_DIR / "ui" / name).read_bytes()
            if ingress_base_path is not None:
                data = data.replace(b"{{INGRESS_BASE_PATH}}", ingress_base_path.encode("utf-8"))
            self.send_response(200); self.send_header("Content-Type", content_type); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
        def log_message(self, *_): pass
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    Thread(target=server.serve_forever, daemon=True).start()
    return server
