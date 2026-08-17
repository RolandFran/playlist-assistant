import argparse
import logging
import sqlite3

from application_paths import add_data_dir_argument, application_paths_from_args
from client import SpotifyClient, SpotifyClientError


SOURCE_MARKER = "#today-source"
SNAPSHOT_PREFIX = "playlist_snapshot:"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("playlist_assistant_historical_test.sync")


def create_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS source (
            playlist_id TEXT PRIMARY KEY,
            playlist_name TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS playlist (
            playlist_id TEXT NOT NULL,
            track_uri TEXT NOT NULL,
            track_name TEXT,
            artist_name TEXT,
            added_at TEXT,
            PRIMARY KEY (playlist_id, track_uri)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sync_state (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)


def find_today_sources(client):
    sources = []

    for playlist in client.get_all_user_playlists():
        playlist_id = playlist.get("id")

        if not playlist_id:
            continue

        description = playlist.get("description") or ""

        if SOURCE_MARKER.lower() not in description.lower():
            continue

        items_info = playlist.get("items") or {}

        sources.append({
            "playlist_id": playlist_id,
            "playlist_name": playlist.get("name") or playlist_id,
            "snapshot_id": playlist.get("snapshot_id"),
            "spotify_track_total": items_info.get("total"),
        })

    return sources


def normalize_playlist_items(items):
    rows = []
    seen = set()

    for playlist_item in items:
        track = playlist_item.get("item")

        if not track:
            continue

        track_uri = track.get("uri")

        if not track_uri or not track_uri.startswith("spotify:track:"):
            continue

        if track_uri in seen:
            continue

        seen.add(track_uri)

        track_name = track.get("name") or ""
        artist_name = ", ".join(
            artist.get("name", "")
            for artist in track.get("artists", [])
        )
        added_at = playlist_item.get("added_at")

        rows.append((
            track_uri,
            track_name,
            artist_name,
            added_at,
        ))

    return rows


def get_sync_state(conn, key):
    row = conn.execute(
        "SELECT value FROM sync_state WHERE key = ?",
        (key,),
    ).fetchone()

    return row[0] if row else None


def set_sync_state(conn, key, value):
    conn.execute("""
        INSERT INTO sync_state (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, value))


def get_existing_source_ids(conn):
    return {
        row[0]
        for row in conn.execute(
            "SELECT playlist_id FROM source"
        ).fetchall()
    }


def get_existing_playlist_count(conn, playlist_id):
    row = conn.execute(
        "SELECT COUNT(*) FROM playlist WHERE playlist_id = ?",
        (playlist_id,),
    ).fetchone()

    return row[0] if row else 0


def build_sync_plan(conn, sources, force_full=False):
    existing_source_ids = get_existing_source_ids(conn)
    plan = []

    for source in sources:
        playlist_id = source["playlist_id"]
        snapshot_id = source["snapshot_id"]
        snapshot_key = SNAPSHOT_PREFIX + playlist_id

        stored_snapshot = get_sync_state(conn, snapshot_key)
        db_count = get_existing_playlist_count(conn, playlist_id)
        spotify_total = source["spotify_track_total"]

        if force_full:
            action = "download"
            reason = "--full"

        elif stored_snapshot and snapshot_id and stored_snapshot == snapshot_id:
            action = "skip"
            reason = "unveraendert"

        elif (
            stored_snapshot is None
            and playlist_id in existing_source_ids
            and db_count > 0
            and spotify_total is not None
            and db_count == spotify_total
        ):
            action = "bootstrap"
            reason = "bestehende DB passt zur Spotify-Trackzahl"

        else:
            action = "download"

            if playlist_id not in existing_source_ids:
                reason = "neue Source"
            elif stored_snapshot and snapshot_id:
                reason = "Playlist geaendert"
            elif db_count != spotify_total:
                reason = (
                    f"Trackzahl geaendert "
                    f"(DB {db_count} / Spotify {spotify_total})"
                )
            else:
                reason = "Snapshot noch unbekannt"

        plan.append({
            **source,
            "action": action,
            "reason": reason,
            "snapshot_key": snapshot_key,
            "db_count": db_count,
        })

    return plan


def download_required_playlists(client, plan):
    """
    Fetch every required source completely before touching SQLite.
    """
    downloaded = {}

    for entry in plan:
        if entry["action"] != "download":
            continue

        name = entry["playlist_name"]
        print(f"Lade: {name} ({entry['reason']}) ...")

        items = client.get_playlist_items(entry["playlist_id"])
        rows = normalize_playlist_items(items)
        downloaded[entry["playlist_id"]] = rows

        print(f"  -> {len(rows)} Tracks")

    return downloaded


def apply_sync(conn, sources, plan, downloaded):
    current_ids = {
        source["playlist_id"]
        for source in sources
    }

    existing_ids = get_existing_source_ids(conn)
    removed_ids = existing_ids - current_ids

    try:
        for playlist_id in removed_ids:
            conn.execute(
                "DELETE FROM playlist WHERE playlist_id = ?",
                (playlist_id,),
            )
            conn.execute(
                "DELETE FROM source WHERE playlist_id = ?",
                (playlist_id,),
            )
            conn.execute(
                "DELETE FROM sync_state WHERE key = ?",
                (SNAPSHOT_PREFIX + playlist_id,),
            )

        for source in sources:
            conn.execute("""
                INSERT INTO source (playlist_id, playlist_name)
                VALUES (?, ?)
                ON CONFLICT(playlist_id) DO UPDATE SET
                    playlist_name = excluded.playlist_name
            """, (
                source["playlist_id"],
                source["playlist_name"],
            ))

        for entry in plan:
            playlist_id = entry["playlist_id"]

            if entry["action"] == "download":
                rows = downloaded[playlist_id]

                conn.execute(
                    "DELETE FROM playlist WHERE playlist_id = ?",
                    (playlist_id,),
                )

                conn.executemany("""
                    INSERT INTO playlist (
                        playlist_id,
                        track_uri,
                        track_name,
                        artist_name,
                        added_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, [
                    (
                        playlist_id,
                        track_uri,
                        track_name,
                        artist_name,
                        added_at,
                    )
                    for (
                        track_uri,
                        track_name,
                        artist_name,
                        added_at,
                    ) in rows
                ])

            snapshot_id = entry["snapshot_id"]

            if snapshot_id:
                set_sync_state(
                    conn,
                    entry["snapshot_key"],
                    snapshot_id,
                )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    return removed_ids


def print_final_stats(conn):
    source_count = conn.execute(
        "SELECT COUNT(*) FROM source"
    ).fetchone()[0]

    playlist_rows = conn.execute(
        "SELECT COUNT(*) FROM playlist"
    ).fetchone()[0]

    unique_uris = conn.execute(
        "SELECT COUNT(DISTINCT track_uri) FROM playlist"
    ).fetchone()[0]

    print()
    print("=" * 55)
    print(f"Quellplaylists:           {source_count}")
    print(f"Playlist-Zeilen gesamt:   {playlist_rows}")
    print(f"Eindeutige Track-URIs:    {unique_uris}")


def main():
    parser = argparse.ArgumentParser(
        description="Synchronisiert Spotify-Playlists mit #today-source."
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help=(
            "Alle markierten Source-Playlists komplett neu laden. "
            "Normalerweise nicht noetig."
        ),
    )
    add_data_dir_argument(parser)
    args = parser.parse_args()
    paths = application_paths_from_args(args)
    paths.ensure_runtime_directories()

    client = SpotifyClient()

    logger.info("source_sync started")

    print()
    print(f'Suche Playlists mit "{SOURCE_MARKER}" in der Beschreibung...')
    print()

    # Remote discovery happens before SQLite is modified.
    sources = find_today_sources(client)

    print(f"Today Sources gefunden: {len(sources)}")
    print()

    for source in sources:
        print(f"  {source['playlist_name']}")

    if not sources:
        # A successful sync with no matching playlists still initializes the
        # source schema.  Scoring can then produce an empty, valid preview
        # instead of treating the database as never synchronized.
        conn = sqlite3.connect(paths.database_path)
        try:
            create_tables(conn)
            conn.commit()
        finally:
            conn.close()
        print()
        print("Keine Today Sources gefunden.")
        print("Die bestehende DB wurde nicht veraendert.")
        logger.info(
            "source_sync finished sources=0 spotify_requests=%d db_changed=false",
            client.request_count,
        )
        return

    with sqlite3.connect(paths.database_path) as conn:
        create_tables(conn)

        plan = build_sync_plan(
            conn,
            sources,
            force_full=args.full,
        )

        print()
        print("Synchronisationsplan:")
        print()

        for entry in plan:
            action_text = {
                "skip": "SKIP",
                "bootstrap": "CACHE",
                "download": "LOAD",
            }[entry["action"]]

            print(
                f"  [{action_text:5}] "
                f"{entry['playlist_name']} - {entry['reason']}"
            )

        print()

        # If this raises, apply_sync is never reached and DB remains unchanged.
        downloaded = download_required_playlists(client, plan)

        removed_ids = apply_sync(
            conn,
            sources,
            plan,
            downloaded,
        )

        if removed_ids:
            print()
            print(
                f"Nicht mehr markierte Sources entfernt: "
                f"{len(removed_ids)}"
            )

        print_final_stats(conn)

        skipped = sum(
            1 for entry in plan
            if entry["action"] == "skip"
        )
        bootstrapped = sum(
            1 for entry in plan
            if entry["action"] == "bootstrap"
        )
        loaded = sum(
            1 for entry in plan
            if entry["action"] == "download"
        )

        print()
        print(
            f"API-sparend: {skipped} unveraendert, "
            f"{bootstrapped} Cache uebernommen, "
            f"{loaded} neu geladen."
        )
        print(f"Spotify-Requests: {client.request_count}")

        logger.info(
            "source_sync finished sources=%d skipped=%d bootstrapped=%d "
            "loaded=%d removed=%d spotify_requests=%d",
            len(sources),
            skipped,
            bootstrapped,
            loaded,
            len(removed_ids),
            client.request_count,
        )


if __name__ == "__main__":
    try:
        main()
    except SpotifyClientError as exc:
        logger.error("source_sync failed error=%s", exc)
        raise SystemExit(1)
