"""Supervised Ingress host; scheduling is owned by the HA integration."""

from __future__ import annotations

import argparse
import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Event, Thread
from typing import Callable, Mapping

from application_paths import ApplicationPaths
from application_storage import ApplicationStorage
try:  # Direct execution inside the add-on image.
    from control_panel import ControlPanel, start_ingress
except ModuleNotFoundError:  # Repository imports used by local tests.
    from ha_app.control_panel import ControlPanel, start_ingress
from run import create_runtime_orchestrator

LOGGER = logging.getLogger("playlist_assistant.ha_app")
DEFAULT_TICK_SECONDS = 60
DEFAULT_HEALTH_PORT = 8099
AUTHORIZATION_STATUS_NAME = "spotify-authorization-status.json"
CASE_C_URL = "http://supervisor/core/api/playlist_assistant/spotify"
CASE_C_TIMEOUT_SECONDS = 30


def run_case_c_diagnostic(playlist_id: str, temporary_name: str) -> str:
    """Send the fixed Case C request without entering the Spotify client proxy."""
    try:
        token = os.environ["SUPERVISOR_TOKEN"]
    except KeyError:
        raise RuntimeError("Supervisor authorization is unavailable.") from None

    payload = json.dumps({
        "operation": "playlist_details",
        "path": {"playlist_id": playlist_id},
        "params": None,
        "json": {"name": temporary_name, "public": False},
    }).encode("utf-8")
    request = urllib.request.Request(
        CASE_C_URL,
        data=payload,
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=CASE_C_TIMEOUT_SECONDS) as response:
            return f"Case C: HTTP {response.status} — request completed."
    except urllib.error.HTTPError as error:
        # Never relay response headers or bodies: they are not needed to locate
        # this boundary and could contain implementation-sensitive information.
        return f"Case C: HTTP {error.code} — Home Assistant returned an error response."
    except OSError:
        return "Case C: request could not reach Home Assistant."


@dataclass(frozen=True)
class AppOptions:
    """The add-on has no Spotify credentials or application options."""

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> "AppOptions":
        return cls()


def spotify_environment(options: AppOptions, paths: ApplicationPaths) -> dict[str, str]:
    """Return the private engine environment without printing credentials."""
    return {
        "PLAYLIST_ASSISTANT_SPOTIFY_PROXY": "http://supervisor/core/api/playlist_assistant/spotify",
    }




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
    def authorization_status_path(self) -> Path:
        return self.paths.data_dir / AUTHORIZATION_STATUS_NAME

    def tick(self) -> list[object]:
        """Refresh only the non-secret connection state (no jobs are run)."""
        self.paths.ensure_runtime_directories()
        try:
            token = os.environ["SUPERVISOR_TOKEN"]
            request = urllib.request.Request("http://supervisor/core/api/playlist_assistant/spotify", data=b'{"operation":"current_user"}', method="POST", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
            urllib.request.urlopen(request, timeout=5).close()
            connected = True
        except (KeyError, OSError):
            connected = False
        if not connected:
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
        self._write_authorization_status("connected")
        return []

    def _write_authorization_status(self, status: str) -> None:
        self.paths.data_dir.mkdir(parents=True, exist_ok=True)
        self.authorization_status_path.write_text(json.dumps({"status": status}) + "\n", encoding="utf-8")

    def serve_forever(self, stop_event: Event | None = None) -> None:
        stop_event = stop_event or Event()
        LOGGER.info("service_started tick_seconds=%d data_dir=%s", self.tick_seconds, self.paths.data_dir)
        health_server = _start_health_server(lambda: self._connected)
        ingress_server = start_ingress(
            ControlPanel(self.paths, spotify_available=lambda: self._connected,
                         schedule_changed=self._notify_schedule_changed,
                         case_c_diagnostic=run_case_c_diagnostic),
            bridge_token="",
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

    def _notify_schedule_changed(self, config) -> None:
        """Tell HA Core to replace native callbacks; no browser/LAN path."""
        token = os.getenv("SUPERVISOR_TOKEN")
        if not token:
            LOGGER.warning("schedule_change_not_sent supervisor token unavailable")
            raise RuntimeError("Home Assistant could not activate the new schedule.")
        data = json.dumps({"history_interval_minutes": config.history_poll_minutes,
                           "daily_enabled": config.today_schedule_enabled,
                           "daily_time": config.today_schedule_time}).encode()
        request = urllib.request.Request("http://supervisor/core/api/services/playlist_assistant/reconfigure_schedule", data=data,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                if response.status < 200 or response.status >= 300:
                    raise OSError(f"Home Assistant event response was {response.status}")
                payload = json.loads(response.read())
            # Core's service endpoint commonly returns []; it is only an HTTP
            # acknowledgement, never proof that a schedule callback exists.
            # Handler/registration failures are surfaced by Core as non-2xx.
            if not isinstance(payload, list):
                raise OSError("Home Assistant schedule service returned an invalid response.")
            active_daily = config.today_schedule_time if config.today_schedule_enabled else "disabled"
            LOGGER.info("schedule_change_sent active_daily_schedule=%s ha_response=%s acknowledgement_only=true", active_daily, payload)
        except (OSError, ValueError, json.JSONDecodeError):
            LOGGER.exception("schedule_change_notification_failed")
            raise RuntimeError("Home Assistant could not activate the new schedule.") from None


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
