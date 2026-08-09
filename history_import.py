"""Import Spotify Extended Streaming History exports into the history database."""

import argparse
import json
import sqlite3
import sys
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional


DEFAULT_DB_PATH = "playlist_assistant.db"


@dataclass(frozen=True)
class HistoryImportResult:
    """Structured outcome of one Extended Streaming History import batch."""

    files_processed: int
    records_read: int
    plays_inserted: int
    duplicates_skipped: int
    invalid_records: int
    started_at: datetime
    ended_at: datetime
    duration_seconds: float
    success: bool
    error: Optional[str] = None


def import_extended_history(
    file_paths: Iterable[str | Path],
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
    now=None,
) -> HistoryImportResult:
    """Import an export batch transactionally without Spotify network access."""
    now = now or (lambda: datetime.now(timezone.utc))
    started_at = now()
    files_processed = 0
    records_read = 0
    plays_inserted = 0
    duplicates_skipped = 0
    invalid_records = 0

    try:
        paths = [Path(path) for path in file_paths]
        if not paths:
            raise ValueError("At least one export file is required.")

        with closing(sqlite3.connect(db_path)) as conn:
            conn.execute("BEGIN")
            ensure_history_table(conn)

            for path in paths:
                records = load_export_file(path)
                files_processed += 1
                records_read += len(records)

                for record in records:
                    values = normalize_record(record)
                    if values is None:
                        invalid_records += 1
                        continue

                    cursor = conn.execute(
                        """
                        INSERT OR IGNORE INTO history (
                            played_at,
                            track_id,
                            track_uri,
                            track_name,
                            artist_name,
                            album_name,
                            duration_ms,
                            ms_played,
                            skipped,
                            reason_start,
                            reason_end,
                            offline,
                            data_source,
                            isrc
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        values,
                    )

                    if cursor.rowcount == 1:
                        plays_inserted += 1
                    else:
                        duplicates_skipped += 1

            conn.commit()
    except (OSError, json.JSONDecodeError, sqlite3.Error, TypeError, ValueError) as error:
        return make_result(
            files_processed,
            records_read,
            plays_inserted,
            duplicates_skipped,
            invalid_records,
            started_at,
            now(),
            success=False,
            error=str(error),
        )

    return make_result(
        files_processed,
        records_read,
        plays_inserted,
        duplicates_skipped,
        invalid_records,
        started_at,
        now(),
        success=True,
    )


def ensure_history_table(conn: sqlite3.Connection) -> None:
    """Create the collector-compatible history table when it is absent."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            played_at TEXT NOT NULL,
            track_id TEXT NOT NULL,
            track_uri TEXT NOT NULL,
            track_name TEXT NOT NULL,
            artist_name TEXT NOT NULL,
            album_name TEXT,
            duration_ms INTEGER,
            ms_played INTEGER,
            skipped INTEGER,
            reason_start TEXT,
            reason_end TEXT,
            offline INTEGER,
            data_source TEXT,
            isrc TEXT,
            PRIMARY KEY (played_at, track_id)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_history_track_id ON history(track_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_history_played_at ON history(played_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_history_isrc ON history(isrc)"
    )


def load_export_file(path: Path) -> list[dict]:
    """Load one Spotify export file and validate its top-level structure."""
    if not path.is_file():
        raise ValueError(f"Export file does not exist: {path}")

    with path.open("r", encoding="utf-8") as export_file:
        records = json.load(export_file)

    if not isinstance(records, list):
        raise ValueError(f"Export file must contain a JSON array: {path}")

    return records


def normalize_record(record) -> tuple | None:
    """Map one supported music-play record to the existing history schema."""
    if not isinstance(record, dict):
        return None

    played_at = record.get("ts")
    track_uri = record.get("spotify_track_uri")
    track_name = record.get("master_metadata_track_name")
    artist_name = record.get("master_metadata_album_artist_name")

    if (
        not isinstance(played_at, str)
        or not isinstance(track_uri, str)
        or not track_uri.startswith("spotify:track:")
        or not isinstance(track_name, str)
        or not track_name
        or not isinstance(artist_name, str)
        or not artist_name
    ):
        return None

    track_id = track_uri.rsplit(":", maxsplit=1)[-1]
    if not track_id:
        return None

    return (
        played_at,
        track_id,
        track_uri,
        track_name,
        artist_name,
        record.get("master_metadata_album_album_name"),
        None,
        record.get("ms_played"),
        bool_to_int(record.get("skipped")),
        record.get("reason_start"),
        record.get("reason_end"),
        bool_to_int(record.get("offline")),
        "extended",
        None,
    )


def bool_to_int(value):
    """Convert optional export booleans to the database representation."""
    if value is None:
        return None
    return 1 if value else 0


def make_result(
    files_processed,
    records_read,
    plays_inserted,
    duplicates_skipped,
    invalid_records,
    started_at,
    ended_at,
    *,
    success,
    error=None,
) -> HistoryImportResult:
    """Build a result with duration derived from injected timestamps."""
    return HistoryImportResult(
        files_processed=files_processed,
        records_read=records_read,
        plays_inserted=plays_inserted,
        duplicates_skipped=duplicates_skipped,
        invalid_records=invalid_records,
        started_at=started_at,
        ended_at=ended_at,
        duration_seconds=(ended_at - started_at).total_seconds(),
        success=success,
        error=error,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import Spotify Extended Streaming History export files."
    )
    parser.add_argument("files", nargs="+", metavar="EXPORT_JSON")
    parser.add_argument("--db", default=DEFAULT_DB_PATH, metavar="DATABASE")
    args = parser.parse_args()

    result = import_extended_history(args.files, db_path=args.db)

    print(f"Files processed:    {result.files_processed}")
    print(f"Records read:       {result.records_read}")
    print(f"New plays inserted: {result.plays_inserted}")
    print(f"Duplicates skipped: {result.duplicates_skipped}")
    print(f"Invalid records:    {result.invalid_records}")

    if result.success:
        return 0

    print(f"Import failed: {result.error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
