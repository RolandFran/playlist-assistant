import json
import logging
import os
import time
import urllib.error
import urllib.request
from urllib.parse import parse_qs, urlparse
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Iterable, Optional

import spotipy
from dotenv import load_dotenv
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyOAuth


PLAYLIST_READ_PAGE_SIZE = 50
RECENTLY_PLAYED_PAGE_SIZE = 50
PLAYLIST_WRITE_BATCH_SIZE = 100

REQUEST_TIMEOUT_SECONDS = 30

SHORT_RATE_LIMIT_MAX_SECONDS = 60
SHORT_RATE_LIMIT_RETRIES = 1

SERVER_ERROR_RETRIES = 2
SERVER_ERROR_BACKOFF_SECONDS = (1, 2)

DEFAULT_SCOPE = " ".join(
    [
        "user-read-recently-played",
        "playlist-read-private",
        "playlist-read-collaborative",
        "playlist-modify-private",
        "playlist-modify-public",
    ]
)

DEFAULT_CACHE_PATH = ".cache-playlist-assistant"

logger = logging.getLogger("playlist_assistant.spotify")

class _ProxySpotify:
    """Spotipy-shaped adapter; credentials remain in Home Assistant Core."""
    def __init__(self, endpoint, token): self.endpoint, self.token = endpoint, token
    def _call(self, operation, *, path=None, params=None, json_body=None):
        payload = json.dumps({"operation": operation, "path": path or {}, "params": params, "json": json_body}).encode()
        request = urllib.request.Request(self.endpoint, data=payload, method="POST", headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                return json.loads(response.read() or b"{}")
        except urllib.error.HTTPError as error:
            raise SpotifyApiError("Spotify proxy request failed.", http_status=error.code) from error
    def current_user_playlists(self, **params): return self._call("user_playlists", params=params)
    def playlist_items(self, playlist_id, **params): return self._call("playlist_items", path={"playlist_id": playlist_id}, params=params)
    def current_user_recently_played(self, **params): return self._call("recently_played", params=params)
    def current_user(self): return self._call("current_user")
    def user_playlist_create(self, user_id, name, **kwargs): return self._call("create_playlist", path={"user_id": user_id}, json_body={"name": name, **kwargs})
    def playlist_change_details(self, playlist_id, **kwargs): return self._call("playlist_details", path={"playlist_id": playlist_id}, json_body=kwargs)
    def playlist_replace_items(self, playlist_id, uris): return self._call("replace_items", path={"playlist_id": playlist_id}, json_body={"uris": uris})
    def playlist_add_items(self, playlist_id, uris): return self._call("append_items", path={"playlist_id": playlist_id}, json_body={"uris": uris})
    def next(self, result):
        next_url = result.get("next")
        parsed = urlparse(next_url or "")
        query = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
        if parsed.path == "/v1/me/playlists": return self._call("user_playlists", params=query)
        if parsed.path.startswith("/v1/playlists/") and parsed.path.endswith("/tracks"):
            return self._call("playlist_items", path={"playlist_id": parsed.path.split("/")[3]}, params=query)
        if parsed.path == "/v1/me/player/recently-played": return self._call("recently_played", params=query)
        raise SpotifyApiError("Spotify proxy returned an unsupported page.")


class SpotifyClientError(RuntimeError):
    pass


class SpotifyRateLimited(SpotifyClientError):
    def __init__(
        self,
        message: str,
        *,
        retry_after: Optional[int] = None,
        reason: Optional[str] = None,
        operation: Optional[str] = None,
    ):
        super().__init__(message)
        self.retry_after = retry_after
        self.reason = reason
        self.operation = operation


class SpotifyQuotaExceeded(SpotifyRateLimited):
    pass


class SpotifyApiError(SpotifyClientError):
    def __init__(
        self,
        message: str,
        *,
        http_status: Optional[int] = None,
        operation: Optional[str] = None,
    ):
        super().__init__(message)
        self.http_status = http_status
        self.operation = operation


@dataclass(frozen=True)
class SpotifyClientStats:
    requests: int


@dataclass(frozen=True)
class RecentlyPlayedBatch:
    items: list[dict]
    gap_possible: bool
    oldest_played_at: Optional[str]
    newest_played_at: Optional[str]
    pages: int


def _chunked(items: list[str], size: int) -> Iterable[list[str]]:
    for start in range(0, len(items), size):
        yield items[start:start + size]


def _played_at_to_unix_ms(value: str) -> int:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return int(dt.timestamp() * 1000)


def _header_value(headers: Any, name: str) -> Optional[str]:
    if not headers:
        return None
    try:
        value = headers.get(name)
        if value is None:
            value = headers.get(name.lower())
        if value is None:
            value = headers.get(name.upper())
    except AttributeError:
        return None
    return None if value is None else str(value)


def _parse_retry_after(headers: Any) -> Optional[int]:
    raw = _header_value(headers, "Retry-After")
    if raw is None:
        return None
    try:
        return max(0, int(float(raw)))
    except (TypeError, ValueError):
        return None


def _extract_reason(exc: SpotifyException) -> Optional[str]:
    reason = getattr(exc, "reason", None)
    if reason:
        return str(reason)

    for candidate in (getattr(exc, "msg", None), str(exc)):
        if not candidate:
            continue

        text = str(candidate)

        if "QUOTA_EXCEEDED" in text:
            return "QUOTA_EXCEEDED"

        try:
            payload = json.loads(text)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue

        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict) and error.get("reason"):
                return str(error["reason"])

    return None


class SpotifyClient:
    def __init__(
        self,
        *,
        scope: str = DEFAULT_SCOPE,
        cache_path: str | None = None,
        open_browser: bool | None = None,
    ):
        proxy_endpoint = os.getenv("PLAYLIST_ASSISTANT_SPOTIFY_PROXY")
        proxy_token = os.getenv("SUPERVISOR_TOKEN")
        if proxy_endpoint:
            if not proxy_token:
                raise RuntimeError("Home Assistant Supervisor authorization is unavailable.")
            self._sp = _ProxySpotify(proxy_endpoint, proxy_token)
            self._request_count = 0
            return
        raise RuntimeError("The Home Assistant Spotify proxy is unavailable.")

    @property
    def request_count(self) -> int:
        return self._request_count

    def stats(self) -> SpotifyClientStats:
        return SpotifyClientStats(requests=self._request_count)

    def reset_request_count(self) -> None:
        self._request_count = 0

    def _call(
        self,
        operation: str,
        fn: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        rate_limit_attempt = 0
        server_attempt = 0

        while True:
            self._request_count += 1

            logger.debug(
                "spotify_request operation=%s request=%d",
                operation,
                self._request_count,
            )

            try:
                return fn(*args, **kwargs)

            except SpotifyException as exc:
                status = getattr(exc, "http_status", None)
                headers = getattr(exc, "headers", None)
                reason = _extract_reason(exc)
                retry_after = _parse_retry_after(headers)

                if status == 429:
                    if reason == "QUOTA_EXCEEDED":
                        logger.warning(
                            "spotify_quota_exceeded operation=%s retry_after=%s",
                            operation,
                            retry_after,
                        )
                        raise SpotifyQuotaExceeded(
                            "Spotify Development-Mode-Quota ist erschoepft.",
                            retry_after=retry_after,
                            reason=reason,
                            operation=operation,
                        ) from exc

                    if (
                        retry_after is not None
                        and retry_after <= SHORT_RATE_LIMIT_MAX_SECONDS
                        and rate_limit_attempt < SHORT_RATE_LIMIT_RETRIES
                    ):
                        rate_limit_attempt += 1
                        logger.warning(
                            "spotify_rate_limit_short operation=%s "
                            "retry_after=%s retry=%d/%d",
                            operation,
                            retry_after,
                            rate_limit_attempt,
                            SHORT_RATE_LIMIT_RETRIES,
                        )
                        time.sleep(retry_after)
                        continue

                    logger.warning(
                        "spotify_rate_limited operation=%s retry_after=%s",
                        operation,
                        retry_after,
                    )
                    raise SpotifyRateLimited(
                        "Spotify Rate Limit erreicht.",
                        retry_after=retry_after,
                        reason=reason,
                        operation=operation,
                    ) from exc

                if status in {500, 502, 503, 504} and server_attempt < SERVER_ERROR_RETRIES:
                    wait_seconds = SERVER_ERROR_BACKOFF_SECONDS[
                        min(server_attempt, len(SERVER_ERROR_BACKOFF_SECONDS) - 1)
                    ]
                    server_attempt += 1
                    logger.warning(
                        "spotify_server_retry operation=%s status=%s wait=%s retry=%d/%d",
                        operation,
                        status,
                        wait_seconds,
                        server_attempt,
                        SERVER_ERROR_RETRIES,
                    )
                    time.sleep(wait_seconds)
                    continue

                raise SpotifyApiError(
                    f"Spotify API Fehler bei {operation}: {exc}",
                    http_status=status,
                    operation=operation,
                ) from exc

    @staticmethod
    def _normalize_playlist_summary(playlist: dict) -> dict:
        normalized = dict(playlist)

        items_info = playlist.get("items")
        if not isinstance(items_info, dict):
            items_info = playlist.get("tracks")
        if not isinstance(items_info, dict):
            items_info = {}

        normalized["item_total"] = items_info.get("total")
        return normalized

    def get_all_user_playlists(self) -> list[dict]:
        playlists: list[dict] = []

        result = self._call(
            "current_user_playlists",
            self._sp.current_user_playlists,
            limit=PLAYLIST_READ_PAGE_SIZE,
        )

        while True:
            playlists.extend(
                self._normalize_playlist_summary(item)
                for item in result.get("items", [])
            )

            if not result.get("next"):
                break

            result = self._call(
                "current_user_playlists.next",
                self._sp.next,
                result,
            )

        return playlists

    def get_playlist_items(self, playlist_id: str) -> list[dict]:
        items: list[dict] = []

        result = self._call(
            "playlist_items",
            self._sp.playlist_items,
            playlist_id,
            limit=PLAYLIST_READ_PAGE_SIZE,
            offset=0,
        )

        while True:
            items.extend(result.get("items", []))

            if not result.get("next"):
                break

            result = self._call(
                "playlist_items.next",
                self._sp.next,
                result,
            )

        return items

    def get_recently_played_since(
        self,
        after_ms: Optional[int],
    ) -> RecentlyPlayedBatch:
        """
        Fetch all currently available plays newer than after_ms.

        Spotify documents Recently Played as cursor-paginated. In practice,
        our account tests can still stop at exactly 50 available items even
        though the persisted checkpoint is older. That condition is surfaced
        as gap_possible instead of being silently treated as complete.
        """
        collected: list[dict] = []
        seen: set[tuple[str, Optional[str]]] = set()
        pages = 0

        kwargs: dict[str, Any] = {
            "limit": RECENTLY_PLAYED_PAGE_SIZE,
        }

        if after_ms is not None:
            kwargs["after"] = after_ms

        result = self._call(
            "recently_played",
            self._sp.current_user_recently_played,
            **kwargs,
        )

        first_page_count = len(result.get("items", []))

        while True:
            pages += 1
            items = result.get("items", [])

            for item in items:
                played_at = item.get("played_at")

                if not played_at:
                    continue

                played_ms = _played_at_to_unix_ms(played_at)

                if after_ms is not None and played_ms <= after_ms:
                    continue

                track = item.get("track") or {}
                key = (played_at, track.get("id"))

                if key in seen:
                    continue

                seen.add(key)
                collected.append(item)

            next_url = result.get("next")

            logger.debug(
                "recently_played_page page=%d items=%d next=%s total_collected=%d",
                pages,
                len(items),
                bool(next_url),
                len(collected),
            )

            if not next_url:
                break

            result = self._call(
                "recently_played.next",
                self._sp.next,
                result,
            )

        collected.sort(key=lambda item: item["played_at"])

        oldest_played_at = collected[0]["played_at"] if collected else None
        newest_played_at = collected[-1]["played_at"] if collected else None

        gap_possible = False

        if (
            after_ms is not None
            and first_page_count >= RECENTLY_PLAYED_PAGE_SIZE
            and collected
        ):
            oldest_ms = _played_at_to_unix_ms(oldest_played_at)
            gap_possible = oldest_ms > after_ms

        return RecentlyPlayedBatch(
            items=collected,
            gap_possible=gap_possible,
            oldest_played_at=oldest_played_at,
            newest_played_at=newest_played_at,
            pages=pages,
        )

    def find_owned_playlist_by_name(self, name: str) -> Optional[dict]:
        matches = [
            playlist
            for playlist in self.get_all_user_playlists()
            if (playlist.get("name") or "") == name
        ]

        if len(matches) > 1:
            ids = ", ".join(playlist.get("id", "?") for playlist in matches)
            raise SpotifyClientError(
                f"Mehrere eigene Playlists heissen exakt {name!r}: {ids}. "
                "Abbruch, damit nicht die falsche Playlist geaendert wird."
            )

        return matches[0] if matches else None

    def create_private_playlist(
        self,
        name: str,
        *,
        description: str = "Generated by Playlist Assistant",
    ) -> dict:
        user = self._call(
            "current_user",
            self._sp.current_user,
        )
        user_id = user["id"]

        return self._call(
            "user_playlist_create",
            self._sp.user_playlist_create,
            user_id,
            name,
            public=False,
            collaborative=False,
            description=description,
        )

    def set_playlist_private(self, playlist_id: str) -> None:
        self._call(
            "playlist_change_details",
            self._sp.playlist_change_details,
            playlist_id,
            public=False,
        )

    def rename_playlist(self, playlist_id: str, name: str) -> None:
        """Rename the persisted target playlist without creating a new one."""
        self._call(
            "playlist_change_details",
            self._sp.playlist_change_details,
            playlist_id,
            name=name,
        )

    def replace_playlist_items(
        self,
        playlist_id: str,
        uris: list[str],
    ) -> None:
        if not uris:
            raise SpotifyClientError(
                "Die Today-Auswahl enthaelt keine Tracks."
            )

        first_chunk = uris[:PLAYLIST_WRITE_BATCH_SIZE]

        self._call(
            "playlist_replace_items",
            self._sp.playlist_replace_items,
            playlist_id,
            first_chunk,
        )

        for chunk in _chunked(
            uris[PLAYLIST_WRITE_BATCH_SIZE:],
            PLAYLIST_WRITE_BATCH_SIZE,
        ):
            self._call(
                "playlist_add_items",
                self._sp.playlist_add_items,
                playlist_id,
                chunk,
            )
