import argparse
import logging
import sqlite3
from datetime import datetime, timezone

from application_paths import add_data_dir_argument, application_paths_from_args
from client import SpotifyClient, SpotifyClientError


DEFAULT_HISTORY_POLL_MINUTES = 90

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("playlist_assistant.collector")


def init_db(conn):
    conn.execute("""
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
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_history_track_id
        ON history(track_id)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_history_played_at
        ON history(played_at)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_history_isrc
        ON history(isrc)
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sync_state (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    conn.commit()


def get_sync_value(conn, key):
    row = conn.execute(
        "SELECT value FROM sync_state WHERE key = ?",
        (key,),
    ).fetchone()

    return row[0] if row else None


def set_sync_value(conn, key, value):
    conn.execute("""
        INSERT INTO sync_state (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, value))


def iso_to_unix_ms(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return int(dt.timestamp() * 1000)


def save_item(conn, item):
    track = item["track"]

    artists = ", ".join(
        artist["name"] for artist in track["artists"]
    )

    cursor = conn.execute("""
        INSERT OR IGNORE INTO history (
            played_at,
            track_id,
            track_uri,
            track_name,
            artist_name,
            album_name,
            duration_ms,
            data_source
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        item["played_at"],
        track["id"],
        track["uri"],
        track["name"],
        artists,
        track["album"]["name"],
        track["duration_ms"],
        "recent",
    ))

    return cursor.rowcount == 1


def collect_new_plays(client, conn, *, recover_after=None):
    stored_checkpoint = get_sync_value(conn, "last_played_at")
    effective_checkpoint = recover_after or stored_checkpoint
    after_ms = (
        iso_to_unix_ms(effective_checkpoint)
        if effective_checkpoint
        else None
    )

    if recover_after:
        logger.info(
            "history_sync recovery=true recover_after=%s stored_checkpoint=%s",
            recover_after,
            stored_checkpoint,
        )
    elif stored_checkpoint:
        logger.info("history_sync checkpoint=%s", stored_checkpoint)
    else:
        logger.info("history_sync first_run=true")

    # Fetch everything first. SQLite is untouched if Spotify fails.
    batch = client.get_recently_played_since(after_ms)
    items = batch.items

    total_received = len(items)
    total_inserted = 0

    if batch.gap_possible:
        logger.warning(
            "history_gap_possible checkpoint=%s oldest_returned=%s "
            "newest_returned=%s received=%d pages=%d",
            effective_checkpoint,
            batch.oldest_played_at,
            batch.newest_played_at,
            total_received,
            batch.pages,
        )

    # Recovery must never move the persistent checkpoint backwards.
    newest_played_at = stored_checkpoint

    try:
        for item in items:
            if save_item(conn, item):
                total_inserted += 1

            played_at = item["played_at"]

            if newest_played_at is None or played_at > newest_played_at:
                newest_played_at = played_at

        if newest_played_at:
            set_sync_value(conn, "last_played_at", newest_played_at)

        set_sync_value(
            conn,
            "last_sync_at",
            datetime.now(timezone.utc).isoformat(),
        )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    return total_received, total_inserted, batch.gap_possible


def print_stats(conn):
    total_plays = conn.execute(
        "SELECT COUNT(*) FROM history"
    ).fetchone()[0]

    unique_tracks = conn.execute(
        "SELECT COUNT(DISTINCT track_id) FROM history"
    ).fetchone()[0]

    oldest = conn.execute(
        "SELECT MIN(played_at) FROM history"
    ).fetchone()[0]

    newest = conn.execute(
        "SELECT MAX(played_at) FROM history"
    ).fetchone()[0]

    print()
    print("Datenbank:")
    print(f"  Wiedergaben:        {total_plays}")
    print(f"  verschiedene Titel: {unique_tracks}")
    print(f"  aeltester Eintrag:  {oldest}")
    print(f"  neuester Eintrag:   {newest}")


def main():
    parser = argparse.ArgumentParser(
        description="Synchronisiert Spotify Recently Played mit der History-DB."
    )
    parser.add_argument(
        "--recover-after",
        metavar="ISO_TIMESTAMP",
        help=(
            "Gezielter Recovery-Lauf ab einem frueheren played_at-Zeitpunkt. "
            "Bereits gespeicherte Plays werden nicht doppelt angelegt."
        ),
    )
    add_data_dir_argument(parser)
    args = parser.parse_args()
    paths = application_paths_from_args(args)
    paths.ensure_runtime_directories()

    if args.recover_after:
        iso_to_unix_ms(args.recover_after)

    client = SpotifyClient()

    with sqlite3.connect(paths.database_path) as conn:
        init_db(conn)

        logger.info("history_sync started")

        received, inserted, gap_possible = collect_new_plays(
            client,
            conn,
            recover_after=args.recover_after,
        )

        logger.info(
            "history_sync finished received=%d inserted=%d "
            "spotify_requests=%d recovery=%s gap_possible=%s",
            received,
            inserted,
            client.request_count,
            bool(args.recover_after),
            gap_possible,
        )

        print()
        print(f"Von Spotify erhalten: {received}")
        print(f"Neu gespeichert:      {inserted}")
        print(f"Spotify-Requests:      {client.request_count}")
        print(f"History-Luecke moegl.: {'JA' if gap_possible else 'nein'}")

        if args.recover_after:
            print(f"Recovery ab:           {args.recover_after}")

        print_stats(conn)


if __name__ == "__main__":
    try:
        main()
    except SpotifyClientError as exc:
        logger.error("history_sync failed error=%s", exc)
        raise SystemExit(1)
