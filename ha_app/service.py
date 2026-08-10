"""Supervised Ingress host; scheduling is owned by the HA integration."""

from __future__ import annotations

import argparse
import json
import logging
import os
import tempfile
import urllib.request
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Event, Thread
from typing import Callable, Mapping
from spotipy.oauth2 import SpotifyOAuth

from application_paths import ApplicationPaths
from application_storage import ApplicationStorage
try:  # Direct execution inside the add-on image.
    from control_panel import ControlPanel, start_ingress
except ModuleNotFoundError:  # Repository imports used by local tests.
    from ha_app.control_panel import ControlPanel, start_ingress
from run import create_runtime_orchestrator
from spotify_pairing import PairingSession

LOGGER = logging.getLogger("playlist_assistant.ha_app")
DEFAULT_TICK_SECONDS = 60
DEFAULT_HEALTH_PORT = 8099
AUTHORIZATION_CACHE_NAME = "spotify-oauth-cache.json"
AUTHORIZATION_STATUS_NAME = "spotify-authorization-status.json"
SPOTIFY_SCOPE = " ".join((
    "user-read-recently-played", "playlist-read-private", "playlist-read-collaborative",
    "playlist-modify-private", "playlist-modify-public",
))


@dataclass(frozen=True)
class AppOptions:
    """Spotify credentials supplied by the Supervisor, never logged or stored."""

    spotify_client_id: str
    spotify_client_secret: str
    bridge_token: str = ""

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> "AppOptions":
        return cls(
            spotify_client_id=_required_option(values, "spotify_client_id"),
            spotify_client_secret=_required_option(values, "spotify_client_secret"),
            bridge_token=_required_option(values, "bridge_token"),
        )


def _required_option(values: Mapping[str, object], name: str) -> str:
    value = values.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Home Assistant app option {name!r} must be a non-empty string.")
    return value


def spotify_environment(options: AppOptions, paths: ApplicationPaths) -> dict[str, str]:
    """Return the private engine environment without printing credentials."""
    return {
        "SPOTIFY_CLIENT_ID": options.spotify_client_id,
        "SPOTIFY_CLIENT_SECRET": options.spotify_client_secret,
        "SPOTIFY_CACHE_PATH": str(paths.data_dir / AUTHORIZATION_CACHE_NAME),
        "SPOTIFY_OPEN_BROWSER": "false",
    }


def has_usable_authorization(cache_path: Path) -> bool:
    """Check for token material without exposing it."""
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and bool(payload.get("access_token") or payload.get("refresh_token"))


class SpotifyPairing:
    """Owns one in-memory encrypted token import session."""
    def __init__(self, options: AppOptions, cache_path: Path, on_connected: Callable[[], None]):
        self._options, self._cache_path, self._on_connected = options, cache_path, on_connected
        self._session: PairingSession | None = None
    def prepare(self) -> dict:
        self._session = PairingSession(self._options.spotify_client_id, SPOTIFY_SCOPE)
        LOGGER.info("spotify_pairing_prepared")
        return self._session.public_document()
    def state(self) -> str:
        if self._session is None: return "not_connected"
        if self._session.expired:
            self._session = None; return "expired"
        return "awaiting_import"
    def import_document(self, document: dict) -> None:
        session = self._session
        if session is None: raise ValueError("No active pairing session exists.")
        payload = session.decrypt_import(document)
        try:
            token = SpotifyOAuth(client_id=self._options.spotify_client_id, client_secret=self._options.spotify_client_secret,
                redirect_uri="http://127.0.0.1/callback", scope=SPOTIFY_SCOPE, open_browser=False).refresh_access_token(payload["refresh_token"])
            if not isinstance(token, dict) or not token.get("access_token"): raise RuntimeError("invalid Spotify response")
            token["refresh_token"] = payload["refresh_token"]
            self._write_cache(token)
        except Exception as error:
            LOGGER.warning("spotify_token_import_failed error_type=%s", type(error).__name__)
            raise RuntimeError("Spotify could not verify the imported connection.") from error
        self._session = None
        self._on_connected()
        LOGGER.info("spotify_token_imported")
    def _write_cache(self, token: dict) -> None:
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self._cache_path.parent, prefix=".spotify-oauth-", delete=False) as file:
            temp_path = Path(file.name); os.chmod(file.name, 0o600); json.dump(token, file); file.write("\n")
        try: os.replace(temp_path, self._cache_path)
        finally:
            if temp_path.exists(): temp_path.unlink(missing_ok=True)


class ServiceHost:
    """Run Ingress and connection reporting, never an app scheduler."""

    def __init__(self, *, paths: ApplicationPaths, options: AppOptions,
                 tick_seconds: int = DEFAULT_TICK_SECONDS,
                 policy_factory=None,
                 runtime_factory: Callable[[ApplicationPaths], object] = create_runtime_orchestrator):
        if tick_seconds <= 0:
            raise ValueError("tick_seconds must be positive.")
        self.paths = paths
        self.options = options
        self.tick_seconds = tick_seconds
        self._storage = ApplicationStorage(paths.database_path)
        self._connected = False

    @property
    def authorization_cache_path(self) -> Path:
        return self.paths.data_dir / AUTHORIZATION_CACHE_NAME

    @property
    def authorization_status_path(self) -> Path:
        return self.paths.data_dir / AUTHORIZATION_STATUS_NAME

    def tick(self) -> list[object]:
        """Refresh only the non-secret connection state (no jobs are run)."""
        self.paths.ensure_runtime_directories()
        if not has_usable_authorization(self.authorization_cache_path):
            if self._connected:
                LOGGER.warning("spotify_status=not_connected authorization cache is unavailable")
            elif not self.authorization_status_path.exists():
                LOGGER.warning("spotify_status=not_connected no usable authorization cache exists")
            self._connected = False
            self._write_authorization_status("not_connected")
            return []

        if not self._connected:
            LOGGER.info("spotify_status=authorization_cache_available")
        self._connected = True
        self._write_authorization_status("authorization_cache_available")
        return []

    def _write_authorization_status(self, status: str) -> None:
        self.paths.data_dir.mkdir(parents=True, exist_ok=True)
        self.authorization_status_path.write_text(json.dumps({"status": status}) + "\n", encoding="utf-8")

    def serve_forever(self, stop_event: Event | None = None) -> None:
        stop_event = stop_event or Event()
        LOGGER.info("service_started tick_seconds=%d data_dir=%s", self.tick_seconds, self.paths.data_dir)
        health_server = _start_health_server(lambda: self._connected)
        pairing = SpotifyPairing(self.options, self.authorization_cache_path, self._mark_connected)
        ingress_server = start_ingress(
            ControlPanel(self.paths, spotify_available=lambda: self._connected,
                         schedule_changed=self._notify_schedule_changed,
                         pairing_prepare=pairing.prepare, pairing_state=pairing.state,
                         pairing_import=pairing.import_document),
            bridge_token=self.options.bridge_token,
        )
        LOGGER.info("ingress_control_panel_started port=%d path=/", ingress_server.server_address[1])
        try:
            self.tick()
            stop_event.wait()
        finally:
            health_server.shutdown()
            health_server.server_close()
            ingress_server.shutdown()
            ingress_server.server_close()
            LOGGER.info("service_stopped")

    def _mark_connected(self) -> None:
        self._connected = has_usable_authorization(self.authorization_cache_path)
        self._write_authorization_status("authorization_cache_available" if self._connected else "not_connected")

    def _notify_schedule_changed(self, config) -> None:
        """Tell HA Core to replace native callbacks; no browser/LAN path."""
        token = os.getenv("SUPERVISOR_TOKEN")
        if not token:
            LOGGER.warning("schedule_change_not_sent supervisor token unavailable")
            return
        data = json.dumps({"history_interval_minutes": config.history_poll_minutes,
                           "daily_enabled": config.today_schedule_enabled,
                           "daily_time": config.today_schedule_time}).encode()
        request = urllib.request.Request("http://supervisor/core/api/events/playlist_assistant_schedule_changed", data=data,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, method="POST")
        try:
            urllib.request.urlopen(request, timeout=5).close()
        except OSError:
            LOGGER.exception("schedule_change_notification_failed")


def _start_health_server(connected: Callable[[], bool]) -> ThreadingHTTPServer:
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if self.path != "/health":
                self.send_error(404)
                return
            payload = json.dumps({"status": "connected" if connected() else "not_connected"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format, *args):
            LOGGER.debug("health_request " + format, *args)

    server = ThreadingHTTPServer(("0.0.0.0", DEFAULT_HEALTH_PORT), HealthHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    LOGGER.info("health_endpoint_started port=%d path=/health", DEFAULT_HEALTH_PORT)
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Playlist Assistant Home Assistant app service")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--options-file", required=True)
    parser.add_argument("--tick-seconds", type=int, default=DEFAULT_TICK_SECONDS)
    args = parser.parse_args()
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")
    options = AppOptions.from_mapping(json.loads(Path(args.options_file).read_text(encoding="utf-8")))
    paths = ApplicationPaths.from_data_dir(args.data_dir)
    os.environ.update(spotify_environment(options, paths))
    ServiceHost(paths=paths, options=options, tick_seconds=args.tick_seconds).serve_forever()


if __name__ == "__main__":
    main()
