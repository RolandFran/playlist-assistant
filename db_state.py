import hashlib
import json
import sqlite3
from pathlib import Path


DB_PATH = Path("playlist_assistant.db")
SNAPSHOT_PREFIX = "playlist_snapshot:"


def _fetch_sync_state(conn, key):
    row = conn.execute(
        "SELECT value FROM sync_state WHERE key = ?",
        (key,),
    ).fetchone()
    return row[0] if row else None


def build_input_state(conn):
    """
    Build a compact representation of every DB input that can change Today.

    This intentionally uses metadata/checkpoints and counts instead of hashing
    tens of thousands of history rows on every publish.
    """
    source_ids = [
        row[0]
        for row in conn.execute(
            "SELECT playlist_id FROM source ORDER BY playlist_id"
        ).fetchall()
    ]

    source_snapshots = [
        (row[0], row[1])
        for row in conn.execute(
            """
            SELECT key, value
            FROM sync_state
            WHERE key LIKE ?
            ORDER BY key
            """,
            (SNAPSHOT_PREFIX + "%",),
        ).fetchall()
    ]

    playlist_count = conn.execute(
        "SELECT COUNT(*) FROM playlist"
    ).fetchone()[0]

    history_count = conn.execute(
        "SELECT COUNT(*) FROM history"
    ).fetchone()[0]

    newest_history = conn.execute(
        "SELECT MAX(played_at) FROM history"
    ).fetchone()[0]

    return {
        "source_ids": source_ids,
        "source_snapshots": source_snapshots,
        "playlist_count": playlist_count,
        "history_count": history_count,
        "last_played_at": _fetch_sync_state(conn, "last_played_at"),
        "newest_history": newest_history,
    }


def fingerprint_state(state):
    payload = json.dumps(
        state,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def get_current_input_fingerprint(db_path=DB_PATH):
    with sqlite3.connect(db_path) as conn:
        state = build_input_state(conn)

    return fingerprint_state(state), state
