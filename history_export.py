"""Export Playlist Assistant history as Spotify Extended Streaming History JSON."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path


SPOTIFY_HISTORY_PLACEHOLDERS = {
    "platform": None,
    "conn_country": None,
    "ip_addr": None,
    "episode_name": None,
    "episode_show_name": None,
    "spotify_episode_uri": None,
    "audiobook_title": None,
    "audiobook_uri": None,
    "audiobook_chapter_uri": None,
    "audiobook_chapter_title": None,
    "shuffle": None,
    "offline_timestamp": None,
    "incognito_mode": None,
}


def export_extended_history(db_path: str | Path, *, from_date: str | None = None) -> list[dict]:
    """Return history rows in Spotify Extended Streaming History-compatible form.

    ``from_date`` is a local-independent UTC calendar date (``YYYY-MM-DD``)
    and is inclusive from midnight UTC.  This function never creates or
    changes the database.
    """
    boundary = _parse_from_date(from_date)
    database = Path(db_path)
    if not database.is_file():
        return []

    with closing(sqlite3.connect(database)) as conn:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'history'"
        ).fetchone()
        if not exists:
            return []
        rows = conn.execute(
            """
            SELECT played_at, track_uri, track_name, artist_name, album_name,
                   ms_played, skipped, reason_start, reason_end, offline
            FROM history
            ORDER BY julianday(played_at) ASC, track_id ASC
            """
        ).fetchall()

    return [
        _spotify_record(row)
        for row in rows
        if boundary is None or _parse_timestamp(row[0]) >= boundary
    ]


def _parse_from_date(value: str | None) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        return datetime.combine(date.fromisoformat(value), datetime.min.time(), timezone.utc)
    except (TypeError, ValueError) as error:
        raise ValueError("From date must use YYYY-MM-DD.") from error


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise ValueError(f"History contains an invalid timestamp: {value!r}") from error
    if parsed.tzinfo is None:
        raise ValueError(f"History contains a timezone-free timestamp: {value!r}")
    return parsed.astimezone(timezone.utc)


def _spotify_record(row: tuple) -> dict:
    played_at, track_uri, track_name, artist_name, album_name, ms_played, skipped, reason_start, reason_end, offline = row
    return {
        "ts": played_at,
        **SPOTIFY_HISTORY_PLACEHOLDERS,
        "ms_played": ms_played,
        "master_metadata_track_name": track_name,
        "master_metadata_album_artist_name": artist_name,
        "master_metadata_album_album_name": album_name,
        "spotify_track_uri": track_uri,
        "reason_start": reason_start,
        "reason_end": reason_end,
        "skipped": _nullable_bool(skipped),
        "offline": _nullable_bool(offline),
    }


def _nullable_bool(value):
    return None if value is None else bool(value)
