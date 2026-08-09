import sqlite3
from datetime import datetime, timezone

DB_PATH = "playlist_assistant.db"


def parse_spotify_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main():
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

        #
        # 1. Unique candidates from all Today sources
        #
        conn.execute("""
            DROP TABLE IF EXISTS temp_candidates
        """)

        conn.execute("""
            CREATE TEMP TABLE temp_candidates AS
            SELECT
                track_uri,
                MAX(track_name) AS track_name,
                MAX(artist_name) AS artist_name,
                MIN(added_at) AS added_at
            FROM playlist
            GROUP BY track_uri
        """)

        conn.execute("""
            CREATE INDEX idx_temp_candidates_uri
            ON temp_candidates(track_uri)
        """)

        #
        # 2. Primary URI matches
        #
        uri_rows = conn.execute("""
            SELECT
                c.track_uri,
                c.track_name,
                c.artist_name,
                c.added_at,
                COUNT(p.played_at) AS play_count,
                MAX(p.played_at) AS last_played
            FROM temp_candidates c
            LEFT JOIN history p
                ON p.track_uri = c.track_uri
                AND (
                    c.added_at IS NULL
                    OR p.played_at >= c.added_at
                )
            GROUP BY
                c.track_uri,
                c.track_name,
                c.artist_name,
                c.added_at
        """).fetchall()

        #
        # Collect candidates without a URI match
        #
        no_uri_match = [
            row for row in uri_rows
            if row[4] == 0
        ]

        #
        # 3. Aggregate fallback data ONCE
        #
        fallback_rows = conn.execute("""
            SELECT
                LOWER(track_name) AS track_name_key,
                LOWER(artist_name) AS artist_name_key,
                played_at
            FROM history
            WHERE track_name IS NOT NULL
              AND artist_name IS NOT NULL
        """).fetchall()

        fallback_index = {}

        for track_name_key, artist_name_key, played_at in fallback_rows:
            key = (
                track_name_key,
                artist_name_key,
            )

            fallback_index.setdefault(key, []).append(
                played_at
            )

        now = datetime.now(timezone.utc)

        play_buckets = {
            "0": 0,
            "1": 0,
            "2": 0,
            "3-5": 0,
            "6-10": 0,
            "11-20": 0,
            "21-50": 0,
            ">50": 0,
        }

        age_buckets = {
            "<7 Tage": 0,
            "7-30 Tage": 0,
            "31-90 Tage": 0,
            "91-180 Tage": 0,
            "181-365 Tage": 0,
            ">365 Tage": 0,
        }

        uri_matches = 0
        fallback_matches = 0
        no_matches = 0

        play_counts = []
        days_values = []

        #
        # 4. Process URI results
        #
        final_rows = []

        for (
            track_uri,
            track_name,
            artist_name,
            added_at,
            play_count,
            last_played,
        ) in uri_rows:

            if play_count > 0:
                uri_matches += 1

                final_rows.append(
                    (
                        track_uri,
                        track_name,
                        artist_name,
                        play_count,
                        last_played,
                    )
                )

                continue

            #
            # 5. Fall back to title + artist only for unmatched candidates
            #
            key = (
                (track_name or "").lower(),
                (artist_name or "").lower(),
            )

            matching_times = fallback_index.get(
                key,
                [],
            )

            if added_at:
                matching_times = [
                    value
                    for value in matching_times
                    if value >= added_at
                ]

            if matching_times:
                fallback_matches += 1

                play_count = len(matching_times)
                last_played = max(matching_times)

            else:
                no_matches += 1

                play_count = 0
                last_played = None

            final_rows.append(
                (
                    track_uri,
                    track_name,
                    artist_name,
                    play_count,
                    last_played,
                )
            )

        #
        # 6. Statistics
        #
        for (
            track_uri,
            track_name,
            artist_name,
            play_count,
            last_played,
        ) in final_rows:

            play_counts.append(play_count)

            if play_count == 0:
                play_buckets["0"] += 1
            elif play_count == 1:
                play_buckets["1"] += 1
            elif play_count == 2:
                play_buckets["2"] += 1
            elif play_count <= 5:
                play_buckets["3-5"] += 1
            elif play_count <= 10:
                play_buckets["6-10"] += 1
            elif play_count <= 20:
                play_buckets["11-20"] += 1
            elif play_count <= 50:
                play_buckets["21-50"] += 1
            else:
                play_buckets[">50"] += 1

            if last_played:
                last_dt = parse_spotify_time(
                    last_played
                )

                days_since = (
                    now - last_dt
                ).total_seconds() / 86400

                days_values.append(days_since)

                if days_since < 7:
                    age_buckets["<7 Tage"] += 1
                elif days_since <= 30:
                    age_buckets["7-30 Tage"] += 1
                elif days_since <= 90:
                    age_buckets["31-90 Tage"] += 1
                elif days_since <= 180:
                    age_buckets["91-180 Tage"] += 1
                elif days_since <= 365:
                    age_buckets["181-365 Tage"] += 1
                else:
                    age_buckets[">365 Tage"] += 1

        print()
        print("MATCHING")
        print("=" * 40)
        print(f"URI-Match:          {uri_matches:>5}")
        print(f"Fallback-Match:     {fallback_matches:>5}")
        print(f"Kein Match:         {no_matches:>5}")

        print()
        print("PLAY-COUNT-VERTEILUNG")
        print("=" * 40)

        for bucket, count in play_buckets.items():
            print(f"{bucket:>6} Plays: {count:>5}")

        print()
        print("LETZTES HÖREN")
        print("=" * 40)

        for bucket, count in age_buckets.items():
            print(f"{bucket:<15}: {count:>5}")

        print()
        print("GESAMT")
        print("=" * 40)
        print(f"Today-Kandidaten:    {len(final_rows)}")
        print(f"0 Plays:             {play_buckets['0']}")
        print(
            f"mind. 1 Play:        "
            f"{len(final_rows) - play_buckets['0']}"
        )

        if play_counts:
            print(f"Max. Play-Count:     {max(play_counts)}")

        if days_values:
            print(f"Max. Tage seit Play: {max(days_values):.1f}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
