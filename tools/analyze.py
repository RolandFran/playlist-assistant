import os
import sqlite3
from datetime import datetime, timezone


DB_PATH = "playlist_assistant.db"
OUTPUT_PATH = os.path.join("reports", "analyze_output.txt")


def parse_spotify_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main():
    output_dir = os.path.dirname(OUTPUT_PATH)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)

    try:
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_history_track_uri
            ON history(track_uri)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_history_name_artist
            ON history(track_name, artist_name)
        """)
        conn.commit()

        # Eindeutige Kandidaten aus allen #today-source-Playlists.
        candidates = conn.execute("""
            SELECT
                track_uri,
                MAX(track_name) AS track_name,
                MAX(artist_name) AS artist_name,
                MIN(added_at) AS added_at
            FROM playlist
            GROUP BY track_uri
            ORDER BY artist_name, track_name
        """).fetchall()

        # History einmal für den Fallback über Titel + Künstler indexieren.
        fallback_index = {}
        for track_name, artist_name, played_at in conn.execute("""
            SELECT track_name, artist_name, played_at
            FROM history
            WHERE track_name IS NOT NULL
              AND artist_name IS NOT NULL
        """):
            key = (track_name.lower(), artist_name.lower())
            fallback_index.setdefault(key, []).append(played_at)

        now = datetime.now(timezone.utc)
        heard_count = 0
        never_count = 0
        uri_matches = 0
        fallback_matches = 0
        rows = []

        for track_uri, track_name, artist_name, added_at in candidates:
            uri_times = [
                row[0]
                for row in conn.execute("""
                    SELECT played_at
                    FROM history
                    WHERE track_uri = ?
                      AND (? IS NULL OR played_at >= ?)
                """, (track_uri, added_at, added_at)).fetchall()
            ]

            if uri_times:
                play_times = uri_times
                uri_matches += 1
                match_type = "URI"
            else:
                key = ((track_name or "").lower(), (artist_name or "").lower())
                play_times = fallback_index.get(key, [])
                if added_at:
                    play_times = [value for value in play_times if value >= added_at]

                if play_times:
                    fallback_matches += 1
                    match_type = "Fallback"
                else:
                    match_type = "-"

            play_count = len(play_times)
            last_played = max(play_times) if play_times else None

            if last_played is None:
                never_count += 1
                days_text = "-"
                last_played_text = "-"
            else:
                heard_count += 1
                days_since = (now - parse_spotify_time(last_played)).total_seconds() / 86400
                days_text = f"{days_since:.2f}"
                last_played_text = last_played

            rows.append((
                play_count,
                last_played or "",
                days_text,
                added_at or "-",
                last_played_text,
                match_type,
                artist_name or "-",
                track_name or track_uri,
            ))

        rows.sort(key=lambda row: (row[0], row[1]))

        output_lines = [
            f"{'Plays':>5}  {'Tage':>8}  {'Seit':<24}  {'Zuletzt gehört':<24}  {'Match':<8}  {'Künstler':<30}  Titel",
            "-" * 155,
        ]

        for play_count, _, days_text, added_at, last_played_text, match_type, artist_name, track_name in rows:
            output_lines.append(
                f"{play_count:>5}  "
                f"{days_text:>8}  "
                f"{added_at:24}  "
                f"{last_played_text:24}  "
                f"{match_type:<8}  "
                f"{artist_name[:30]:30}  "
                f"{track_name}"
            )

        output_lines.extend([
            "",
            "=" * 155,
            f"Eindeutige Kandidaten:             {len(candidates)}",
            f"Seit Aufnahme gehört:              {heard_count}",
            f"Seit Aufnahme nicht gehört:        {never_count}",
            f"URI-Matches:                        {uri_matches}",
            f"Fallback-Matches:                   {fallback_matches}",
        ])

        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(output_lines))

        print()
        print("Analyse abgeschlossen.")
        print()
        print(f"Eindeutige Kandidaten:      {len(candidates)}")
        print(f"Seit Aufnahme gehört:       {heard_count}")
        print(f"Noch nicht gehört:          {never_count}")
        print(f"URI-Matches:                {uri_matches}")
        print(f"Fallback-Matches:           {fallback_matches}")
        print()
        print("Vollständiger Report:")
        print(os.path.abspath(OUTPUT_PATH))

    finally:
        conn.close()


if __name__ == "__main__":
    main()
