import json
import math
import os
import sqlite3
import argparse
from datetime import datetime, timezone

from db_state import build_input_state, fingerprint_state
from runtime_config import (
    RuntimeConfig,
    add_runtime_config_arguments,
    get_runtime_config,
    runtime_config_from_args,
)


DB_PATH = "playlist_assistant.db"
OUTPUT_PATH = os.path.join("reports", "scoring_output.txt")
TODAY_OUTPUT_PATH = os.path.join("reports", "today_output.txt")
TODAY_JSON_PATH = os.path.join("reports", "today_tracks.json")

def parse_spotify_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def normalize(value: str | None) -> str:
    return (value or "").strip().casefold()


def select_today(candidates, size: int, artist_min_gap: int):
    remaining = list(candidates)
    selected = []
    relaxed_count = 0

    target_size = min(size, len(remaining))

    while remaining and len(selected) < target_size:
        recent_artists = {
            normalize(row["artist_name"])
            for row in selected[-artist_min_gap:]
        } if artist_min_gap > 0 else set()

        chosen_index = None

        for index, row in enumerate(remaining):
            artist_key = normalize(row["artist_name"])

            if not artist_key or artist_key not in recent_artists:
                chosen_index = index
                break

        if chosen_index is None:
            chosen_index = 0
            relaxed_count += 1

        selected.append(remaining.pop(chosen_index))

    return selected, relaxed_count


def calculate_combined_score(
    rare_score: float,
    long_score: float,
    config: RuntimeConfig,
) -> float:
    """Kombiniert die Scores mit den intern normalisierten Gewichten."""
    return (
        config.rare_weight_factor * rare_score
        + config.long_weight_factor * long_score
    )


def main(config: RuntimeConfig | None = None):
    """Führt das Scoring mit einer bereits validierten Konfiguration aus."""
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    config = config or get_runtime_config()

    conn = sqlite3.connect(DB_PATH)

    try:
        playlist_rows = conn.execute("""
            SELECT
                track_uri,
                track_name,
                artist_name,
                added_at
            FROM playlist
        """).fetchall()

        history_rows = conn.execute("""
            SELECT
                played_at,
                track_name,
                artist_name
            FROM history
        """).fetchall()

        # History einmal in zwei Indizes aufbauen:
        # 1. exakte Spotify-URI als primaerer Match
        # 2. Titel + Interpret nur als Fallback
        history_by_uri = {}
        history_by_song = {}

        history_rows_with_uri = conn.execute("""
            SELECT
                played_at,
                track_uri,
                track_name,
                artist_name
            FROM history
        """).fetchall()

        for played_at, track_uri, track_name, artist_name in history_rows_with_uri:
            if track_uri:
                history_by_uri.setdefault(track_uri, []).append(played_at)

            key = (
                normalize(track_name),
                normalize(artist_name),
            )
            history_by_song.setdefault(key, []).append(played_at)

        playlist_by_song = {}

        for track_uri, track_name, artist_name, added_at in playlist_rows:
            key = (
                normalize(track_name),
                normalize(artist_name),
            )

            current = playlist_by_song.get(key)

            if current is None:
                playlist_by_song[key] = {
                    "track_uri": track_uri,
                    "track_name": track_name,
                    "artist_name": artist_name,
                    "added_at": added_at,
                }
            else:
                if added_at and (
                    current["added_at"] is None
                    or added_at < current["added_at"]
                ):
                    current["added_at"] = added_at

        candidates = []

        for key, playlist_track in playlist_by_song.items():
            track_uri = playlist_track["track_uri"]
            track_name = playlist_track["track_name"]
            artist_name = playlist_track["artist_name"]
            added_at = playlist_track["added_at"]

            # Primaer: exakte Spotify-URI.
            # Nur wenn die URI keinen Treffer liefert, auf Titel + Interpret
            # zurueckfallen. So werden unterschiedliche Artist-Metadaten bei
            # identischer Spotify-Track-ID korrekt behandelt.
            uri_plays = list(history_by_uri.get(track_uri, []))

            if added_at:
                uri_plays = [
                    played_at
                    for played_at in uri_plays
                    if played_at >= added_at
                ]

            if uri_plays:
                plays = uri_plays
                match_type = "uri"
            else:
                plays = list(history_by_song.get(key, []))

                if added_at:
                    plays = [
                        played_at
                        for played_at in plays
                        if played_at >= added_at
                    ]

                match_type = "title_artist" if plays else "none"

            play_count = len(plays)
            last_played = max(plays) if plays else None

            candidates.append({
                "track_uri": track_uri,
                "track_name": track_name,
                "artist_name": artist_name,
                "added_at": added_at,
                "play_count": play_count,
                "last_played": last_played,
                "match_type": match_type,
            })

        now = datetime.now(timezone.utc)

        max_play_count = max(
            (row["play_count"] for row in candidates),
            default=0,
        )

        heard_days = []

        for row in candidates:
            if row["last_played"]:
                last_dt = parse_spotify_time(row["last_played"])
                days_since = max(
                    0.0,
                    (now - last_dt).total_seconds() / 86400,
                )
                row["days_since"] = days_since
                row["days_since_added"] = None
                heard_days.append(days_since)
            elif row["added_at"]:
                added_dt = parse_spotify_time(row["added_at"])
                row["days_since"] = None
                row["days_since_added"] = max(
                    0.0,
                    (now - added_dt).total_seconds() / 86400,
                )
            else:
                row["days_since"] = None
                row["days_since_added"] = None

        max_days_since = max(heard_days, default=0.0)

        for row in candidates:
            play_count = row["play_count"]
            days_since = row["days_since"]

            if play_count <= 0 or max_play_count <= 0:
                rare_score = 100.0
            else:
                rare_score = 100.0 * (
                    1.0
                    - math.log1p(play_count)
                    / math.log1p(max_play_count)
                )

            if days_since is None:
                long_score = 50.0
            elif max_days_since <= 0:
                long_score = 0.0
            else:
                long_score = 100.0 * (
                    math.log1p(days_since)
                    / math.log1p(max_days_since)
                )

            long_score = max(0.0, min(100.0, long_score))

            combined_score = calculate_combined_score(
                rare_score,
                long_score,
                config,
            )

            row["rare_score"] = rare_score
            row["long_score"] = long_score
            row["combined_score"] = combined_score

        candidates.sort(
            key=lambda row: (
                -row["combined_score"],
                -(row["days_since_added"] or 0.0)
                if row["play_count"] == 0 else 0.0,
                row["artist_name"] or "",
                row["track_name"] or "",
            )
        )

        today_rows, relaxed_count = select_today(
            candidates,
            config.today_size,
            config.artist_min_gap,
        )

        output_lines = []
        output_lines.append(
            f"{'Score':>7}  "
            f"{'Rare':>7}  "
            f"{'Long':>7}  "
            f"{'Plays':>5}  "
            f"{'Tage':>8}  "
            f"{'Match':<15}  "
            f"{'Künstler':<30}  "
            f"Titel"
        )
        output_lines.append("-" * 132)

        for row in candidates:
            days_text = (
                "-"
                if row["days_since"] is None
                else f"{row['days_since']:.1f}"
            )

            output_lines.append(
                f"{row['combined_score']:>7.1f}  "
                f"{row['rare_score']:>7.1f}  "
                f"{row['long_score']:>7.1f}  "
                f"{row['play_count']:>5}  "
                f"{days_text:>8}  "
                f"{({'uri': 'URI', 'title_artist': 'Titel+Interpret', 'none': 'kein Match'}.get(row['match_type'], row['match_type'])):<15}  "
                f"{(row['artist_name'] or '-')[:30]:30}  "
                f"{row['track_name'] or row['track_uri']}"
            )

        output_lines.append("")
        output_lines.append("=" * 132)
        output_lines.append(f"Kandidaten:          {len(candidates)}")
        output_lines.append(f"Höchste Wiedergabezahl: {max_play_count}")
        output_lines.append(f"Längste Hörpause:    {max_days_since:.1f} Tage")
        output_lines.append(
            f"Gewichtung:          Rare {config.rare_weight} / Long {config.long_weight}"
        )
        output_lines.append(f"Konfiguriert:         {config.today_size} Titel")
        output_lines.append(f"Artist-Min-Gap:       {config.artist_min_gap}")

        today_lines = []
        today_lines.append(
            f"{'Nr.':>4}  "
            f"{'Score':>7}  "
            f"{'Rare':>7}  "
            f"{'Long':>7}  "
            f"{'Plays':>5}  "
            f"{'Tage':>8}  "
            f"{'Künstler':<30}  "
            f"Titel"
        )
        today_lines.append("-" * 120)

        for rank, row in enumerate(today_rows, start=1):
            days_text = (
                "-"
                if row["days_since"] is None
                else f"{row['days_since']:.1f}"
            )

            today_lines.append(
                f"{rank:>4}  "
                f"{row['combined_score']:>7.1f}  "
                f"{row['rare_score']:>7.1f}  "
                f"{row['long_score']:>7.1f}  "
                f"{row['play_count']:>5}  "
                f"{days_text:>8}  "
                f"{(row['artist_name'] or '-')[:30]:30}  "
                f"{row['track_name'] or row['track_uri']}"
            )

        today_lines.append("")
        today_lines.append("=" * 120)
        today_lines.append(f"Auswahlgroesse:       {len(today_rows)}")
        today_lines.append(f"Konfiguriert:         {config.today_size}")
        today_lines.append(f"Artist-Min-Gap:       {config.artist_min_gap}")
        today_lines.append(f"Gap-Ausnahmen:        {relaxed_count}")
        today_lines.append(
            f"Gewichtung:           Rare {config.rare_weight} / Long {config.long_weight}"
        )

        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(output_lines))

        with open(TODAY_OUTPUT_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(today_lines))

        # Capture the exact DB input state used for this scoring run.
        input_state = build_input_state(conn)
        input_fingerprint = fingerprint_state(input_state)

        today_payload = {
            "generated_at": now.isoformat(),
            "input_fingerprint": input_fingerprint,
            "input_state": input_state,
            "playlist_size": len(today_rows),
            "configured_size": config.today_size,
            "artist_min_gap": config.artist_min_gap,
            "rare_weight": config.rare_weight,
            "long_weight": config.long_weight,
            "runtime_config": {
                "today_size": config.today_size,
                "rare_weight": config.rare_weight,
                "long_weight": config.long_weight,
                "artist_min_gap": config.artist_min_gap,
            },
            "tracks": [
                {
                    "position": rank,
                    "track_uri": row["track_uri"],
                    "track_name": row["track_name"],
                    "artist_name": row["artist_name"],
                    "combined_score": round(row["combined_score"], 3),
                    "rare_score": round(row["rare_score"], 3),
                    "long_score": round(row["long_score"], 3),
                    "play_count": row["play_count"],
                    "days_since": (
                        None
                        if row["days_since"] is None
                        else round(row["days_since"], 3)
                    ),
                }
                for rank, row in enumerate(today_rows, start=1)
            ],
        }

        with open(TODAY_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(today_payload, f, ensure_ascii=False, indent=2)

        print()
        print("Scoring abgeschlossen.")
        print()
        print(f"Kandidaten:          {len(candidates)}")
        print(f"Höchste Wiedergabezahl: {max_play_count}")
        print(f"Längste Hörpause:    {max_days_since:.1f} Tage")
        print(
            f"Gewichtung:          Rare {config.rare_weight} / "
            f"Long {config.long_weight}"
        )
        print(f"Today-Auswahl:        {len(today_rows)}")
        print(f"Artist-Min-Gap:       {config.artist_min_gap}")
        print(f"Gap-Ausnahmen:        {relaxed_count}")
        print(f"Input-Fingerprint:    {input_fingerprint[:12]}...")
        print()
        print("Vollständiger Scoring-Report:")
        print(os.path.abspath(OUTPUT_PATH))
        print()
        print("Today-Auswahl:")
        print(os.path.abspath(TODAY_OUTPUT_PATH))
        print()
        print("Today-Daten für Spotify:")
        print(os.path.abspath(TODAY_JSON_PATH))

    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Today-Auswahl mit optionaler Laufzeitkonfiguration berechnen."
    )
    add_runtime_config_arguments(parser)
    main(runtime_config_from_args(parser.parse_args()))
