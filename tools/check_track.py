import argparse
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


PROJECT_DIR = Path(__file__).resolve().parents[1] if Path(__file__).resolve().parent.name == "tools" else Path(__file__).resolve().parent
DB_PATH = PROJECT_DIR / "playlist_assistant.db"
TODAY_JSON = PROJECT_DIR / "reports" / "today_tracks.json"


def normalize(value):
    return (value or "").strip().casefold()


def parse_track_id(value):
    value = value.strip()

    if value.startswith("spotify:track:"):
        return value.split(":")[-1]

    if "open.spotify.com" in value:
        match = re.search(r"/track/([A-Za-z0-9]+)", value)
        if match:
            return match.group(1)

    if re.fullmatch(r"[A-Za-z0-9]{15,30}", value):
        return value

    return None


def parse_time(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def days_since(value):
    dt = parse_time(value)
    if not dt:
        return None
    return (datetime.now(timezone.utc) - dt).total_seconds() / 86400


def table_columns(conn, table):
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


def find_playlist_track(conn, track_id=None, search_text=None):
    cols = table_columns(conn, "playlist")
    if not cols:
        return []

    select_cols = [c for c in [
        "track_uri", "track_id", "track_name", "artist_name",
        "playlist_id", "playlist_name", "added_at"
    ] if c in cols]

    if track_id:
        clauses = []
        params = []
        if "track_id" in cols:
            clauses.append("track_id = ?")
            params.append(track_id)
        if "track_uri" in cols:
            clauses.append("track_uri = ?")
            params.append(f"spotify:track:{track_id}")

        if clauses:
            sql = f"SELECT {', '.join(select_cols)} FROM playlist WHERE " + " OR ".join(clauses)
            rows = conn.execute(sql, params).fetchall()
            return [dict(zip(select_cols, row)) for row in rows]

    if search_text and "track_name" in cols:
        like = f"%{search_text}%"
        sql = f"""
            SELECT {', '.join(select_cols)}
            FROM playlist
            WHERE track_name LIKE ?
               OR artist_name LIKE ?
            ORDER BY artist_name, track_name
            LIMIT 30
        """
        rows = conn.execute(sql, (like, like)).fetchall()
        return [dict(zip(select_cols, row)) for row in rows]

    return []


def find_history_by_uri(conn, track_id):
    cols = table_columns(conn, "history")
    if not cols:
        return []

    select_cols = [c for c in [
        "played_at", "track_uri", "track_id", "track_name",
        "artist_name", "ms_played", "skipped", "data_source"
    ] if c in cols]

    clauses = []
    params = []
    if "track_id" in cols:
        clauses.append("track_id = ?")
        params.append(track_id)
    if "track_uri" in cols:
        clauses.append("track_uri = ?")
        params.append(f"spotify:track:{track_id}")

    if not clauses:
        return []

    sql = f"""
        SELECT {', '.join(select_cols)}
        FROM history
        WHERE {" OR ".join(clauses)}
        ORDER BY played_at DESC
    """
    rows = conn.execute(sql, params).fetchall()
    return [dict(zip(select_cols, row)) for row in rows]


def find_history_by_title_artist(conn, title, artist):
    cols = table_columns(conn, "history")
    if "track_name" not in cols or "artist_name" not in cols:
        return []

    select_cols = [c for c in [
        "played_at", "track_uri", "track_id", "track_name",
        "artist_name", "ms_played", "skipped", "data_source"
    ] if c in cols]

    rows = conn.execute(
        f"""
        SELECT {', '.join(select_cols)}
        FROM history
        WHERE LOWER(TRIM(track_name)) = ?
          AND LOWER(TRIM(artist_name)) = ?
        ORDER BY played_at DESC
        """,
        (normalize(title), normalize(artist)),
    ).fetchall()

    return [dict(zip(select_cols, row)) for row in rows]


def load_today_entry(track_id):
    if not TODAY_JSON.exists():
        return None

    try:
        payload = json.loads(TODAY_JSON.read_text(encoding="utf-8"))
    except Exception:
        return None

    tracks = payload.get("tracks", payload if isinstance(payload, list) else [])
    uri = f"spotify:track:{track_id}"

    for row in tracks:
        if row.get("track_uri") == uri:
            return row

    return None


def print_history(label, rows):
    print()
    print(label)
    print("=" * 72)

    if not rows:
        print("Keine Treffer.")
        return

    newest = rows[0].get("played_at")
    oldest = rows[-1].get("played_at")

    print(f"Plays:              {len(rows)}")
    print(f"Zuletzt gehoert:    {newest}")
    if newest:
        print(f"Tage seitdem:       {days_since(newest):.2f}")
    print(f"Erster DB-Treffer:  {oldest}")

    print()
    print("Letzte Wiedergaben:")
    for row in rows[:10]:
        played_at = row.get("played_at", "-")
        source = row.get("data_source")
        extra = f"  [{source}]" if source else ""
        print(f"  {played_at}{extra}")


def main():
    parser = argparse.ArgumentParser(
        description="Prueft einen Spotify-Track gegen Playlist-Quellen, History und aktuelle Today-Auswahl."
    )
    parser.add_argument(
        "track",
        help="Spotify Track-URL, spotify:track:URI, Track-ID oder Suchtext."
    )
    parser.add_argument(
        "--artist",
        help="Optionaler Interpret bei Textsuche."
    )
    args = parser.parse_args()

    if not DB_PATH.exists():
        raise SystemExit(f"Datenbank nicht gefunden: {DB_PATH}")

    track_id = parse_track_id(args.track)

    with sqlite3.connect(DB_PATH) as conn:
        playlist_rows = find_playlist_track(
            conn,
            track_id=track_id,
            search_text=None if track_id else args.track,
        )

        if not track_id:
            if not playlist_rows:
                print("Kein passender Track in den aktiven Source-Daten gefunden.")
                raise SystemExit(1)

            if args.artist:
                filtered = [
                    row for row in playlist_rows
                    if normalize(args.artist) in normalize(row.get("artist_name"))
                ]
                if filtered:
                    playlist_rows = filtered

            unique = {}
            for row in playlist_rows:
                uri = row.get("track_uri")
                if uri:
                    unique[uri] = row

            if len(unique) != 1:
                print("Mehrere Treffer gefunden. Bitte Spotify-URL/URI verwenden:")
                for row in list(unique.values())[:20]:
                    print(
                        f"  {row.get('artist_name', '-')} - "
                        f"{row.get('track_name', '-')}  "
                        f"{row.get('track_uri', '-')}"
                    )
                raise SystemExit(2)

            uri = next(iter(unique))
            track_id = uri.split(":")[-1]

        history_uri = find_history_by_uri(conn, track_id)

        # Resolve canonical title/artist from playlist first, otherwise history.
        canonical = None
        for row in playlist_rows:
            if row.get("track_uri") == f"spotify:track:{track_id}":
                canonical = row
                break

        if canonical is None and history_uri:
            canonical = history_uri[0]

        title = canonical.get("track_name") if canonical else None
        artist = canonical.get("artist_name") if canonical else None

        history_fallback = []
        if title and artist:
            history_fallback = find_history_by_title_artist(conn, title, artist)

    print()
    print("# Track-Prüfung")
    print()
    print(f"Track-ID:           {track_id}")
    print(f"Spotify-URI:        spotify:track:{track_id}")
    if title:
        print(f"Titel:              {title}")
    if artist:
        print(f"Interpret:          {artist}")

    print()
    print("AKTIVE SOURCES")
    print("=" * 72)
    matching_playlist_rows = [
        row for row in playlist_rows
        if row.get("track_uri") == f"spotify:track:{track_id}"
    ]

    if matching_playlist_rows:
        print(f"Source-Einträge:      {len(matching_playlist_rows)}")
        for row in matching_playlist_rows:
            playlist_name = row.get("playlist_name")
            playlist_id = row.get("playlist_id")
            added_at = row.get("added_at")

            parts = []
            if playlist_name:
                parts.append(playlist_name)
            elif playlist_id:
                parts.append(playlist_id)
            else:
                parts.append("(Source unbekannt)")

            if added_at:
                parts.append(f"seit {added_at}")

            print("  " + " | ".join(parts))
    else:
        print("Nicht in den aktuell synchronisierten Sources gefunden.")

    print_history("HISTORY - EXAKTE URI", history_uri)

    if history_uri:
        print()
        print("METADATENVERGLEICH - PLAYLIST / HISTORY")
        print("=" * 72)

        playlist_title = title or "-"
        playlist_artist = artist or "-"

        history_titles = sorted({
            row.get("track_name") or "-"
            for row in history_uri
        })
        history_artists = sorted({
            row.get("artist_name") or "-"
            for row in history_uri
        })

        print(f"Playlist-Titel:      {playlist_title}")
        print("History-Titel:")
        for value in history_titles:
            print(f"  {value}")

        print()
        print(f"Playlist-Interpret:  {playlist_artist}")
        print("History-Interpret:")
        for value in history_artists:
            print(f"  {value}")

        title_match = any(
            normalize(value) == normalize(playlist_title)
            for value in history_titles
        )
        artist_match = any(
            normalize(value) == normalize(playlist_artist)
            for value in history_artists
        )

        print()
        print(f"Titel identisch:     {'JA' if title_match else 'NEIN'}")
        print(f"Interpret identisch: {'JA' if artist_match else 'NEIN'}")

    # This is the matching logic most relevant for the current scoring implementation.
    if title and artist:
        same_as_uri = {
            row.get("played_at") for row in history_uri
        } == {
            row.get("played_at") for row in history_fallback
        }

        label = "HISTORY - TITEL + INTERPRET"
        if same_as_uri:
            label += " (identisch mit URI-Treffern)"
        print_history(label, history_fallback)

        if len(history_fallback) != len(history_uri):
            print()
            print("HINWEIS")
            print("=" * 72)
            print(
                "Titel+Interpret findet eine andere Anzahl als die exakte Spotify-URI. "
                "Das kann z. B. bei Remaster-, Album- oder Re-Release-Varianten auftreten."
            )

    today = load_today_entry(track_id)
    print()
    print("AKTUELLE TODAY-AUSWAHL")
    print("=" * 72)
    if today:
        print(f"Position:           {today.get('position', '-')}")
        print(f"Score:              {today.get('combined_score', '-')}")
        print(f"Rare Score:         {today.get('rare_score', '-')}")
        print(f"Long Score:         {today.get('long_score', '-')}")
        print(f"Play Count:         {today.get('play_count', '-')}")
        print(f"Tage seit Play:     {today.get('days_since', '-')}")
    else:
        print("Track ist nicht in der aktuellen Today-Auswahl.")

    print()
    print("Prüfung abgeschlossen.")


if __name__ == "__main__":
    main()
