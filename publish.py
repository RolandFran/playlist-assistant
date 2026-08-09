import argparse
import json
import logging
import math
import os
import sys
from pathlib import Path

from db_state import get_current_input_fingerprint

from client import (
    PLAYLIST_WRITE_BATCH_SIZE,
    SpotifyClient,
    SpotifyClientError,
)


TODAY_JSON_PATH = Path("reports") / "today_tracks.json"

TARGET_PLAYLIST_NAME = os.getenv("SPOTIFY_TARGET_PLAYLIST", "Today")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("playlist_assistant.publish")


def load_today_tracks(path: Path):
    if not path.exists():
        raise RuntimeError(
            f"{path} fehlt. Fuehre zuerst 'python scoring.py' aus."
        )

    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    tracks = payload.get("tracks")

    if not isinstance(tracks, list):
        raise RuntimeError(f"{path} enthaelt keine gueltige Trackliste.")

    uris = []

    for index, track in enumerate(tracks, start=1):
        uri = (track.get("track_uri") or "").strip()

        if not uri.startswith("spotify:track:"):
            raise RuntimeError(
                f"Ungueltige Spotify-Track-URI an Position {index}: {uri!r}"
            )

        uris.append(uri)

    if len(uris) != len(set(uris)):
        raise RuntimeError(
            "Die Today-Auswahl enthaelt doppelte Spotify-URIs. "
            "Abbruch, damit die Zielplaylist keine unbemerkten Dubletten bekommt."
        )

    return payload, uris


def validate_scoring_freshness(payload):
    expected = payload.get("input_fingerprint")

    if not expected:
        raise RuntimeError(
            "Today-Auswahl enthaelt noch keinen Input-Fingerprint. "
            "Fuehre einmal 'python scoring.py' aus."
        )

    current, _state = get_current_input_fingerprint()

    if current != expected:
        generated_at = payload.get("generated_at", "unbekannt")
        raise RuntimeError(
            "Today-Auswahl ist veraltet: Sources oder History haben sich "
            "seit dem letzten Scoring geaendert. "
            f"Scoring-Zeitpunkt: {generated_at}. "
            "Fuehre zuerst 'python scoring.py' aus."
        )

    return current

def print_plan(payload, uris, target_playlist):
    total = len(uris)
    batches = max(1, math.ceil(total / PLAYLIST_WRITE_BATCH_SIZE))

    print()
    print("Spotify Publish - Dry-Run")
    print("=" * 60)
    print(f"Zielplaylist:       {TARGET_PLAYLIST_NAME}")
    print(f"Tracks:             {total}")
    print(
        f"API-Bloecke:        {batches} x max. "
        f"{PLAYLIST_WRITE_BATCH_SIZE}"
    )
    print(f"Scoring-Groesse:    {payload.get('configured_size', '-')}")
    print(f"Artist-Gap:         {payload.get('artist_gap', '-')}")
    print("Sichtbarkeit:       privat")
    print()

    if target_playlist:
        print("Spotify-Ziel:       vorhandene eigene Playlist")
        print(f"Playlist-ID:        {target_playlist.get('id')}")
        print(
            "Aktion bei --write: Playlist auf privat setzen, "
            "Inhalt vollstaendig ersetzen, Reihenfolge beibehalten."
        )
    else:
        print("Spotify-Ziel:       noch nicht vorhanden")
        print(
            "Aktion bei --write: private Playlist anlegen und "
            "anschliessend befuellen."
        )

    if uris:
        print()
        print("Erste Tracks:")
        for track in payload["tracks"][:5]:
            print(
                f"  {track['position']:>3}. "
                f"{track.get('artist_name') or '-'} - "
                f"{track.get('track_name') or track['track_uri']}"
            )

    print()


def main():
    parser = argparse.ArgumentParser(
        description="Schreibt die von scoring.py erzeugte Today-Auswahl nach Spotify."
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Tatsaechlich nach Spotify schreiben. Ohne --write nur Dry-Run.",
    )
    args = parser.parse_args()

    payload, uris = load_today_tracks(TODAY_JSON_PATH)
    input_fingerprint = validate_scoring_freshness(payload)

    print(f"Scoring-Stand:       aktuell ({input_fingerprint[:12]}...)")

    client = SpotifyClient()
    target_playlist = client.find_owned_playlist_by_name(
        TARGET_PLAYLIST_NAME
    )

    print_plan(payload, uris, target_playlist)

    if not args.write:
        print("Nichts veraendert. Zum Schreiben die Option --write verwenden.")
        print(f"Spotify-Requests: {client.request_count}")
        return

    logger.info(
        "publish started playlist=%s tracks=%d",
        TARGET_PLAYLIST_NAME,
        len(uris),
    )

    if target_playlist is None:
        target_playlist = client.create_private_playlist(
            TARGET_PLAYLIST_NAME,
        )
        print(
            f"Playlist '{TARGET_PLAYLIST_NAME}' angelegt: "
            f"{target_playlist['id']}"
        )

    playlist_id = target_playlist["id"]

    client.set_playlist_private(playlist_id)
    print("Playlist-Sichtbarkeit auf privat gesetzt.")

    client.replace_playlist_items(
        playlist_id,
        uris,
    )

    print(
        f"Fertig: {len(uris)} Tracks nach "
        f"'{TARGET_PLAYLIST_NAME}' geschrieben."
    )
    print(f"Spotify-Requests: {client.request_count}")

    logger.info(
        "publish finished playlist=%s tracks=%d spotify_requests=%d",
        TARGET_PLAYLIST_NAME,
        len(uris),
        client.request_count,
    )


if __name__ == "__main__":
    try:
        main()
    except (SpotifyClientError, RuntimeError) as exc:
        logger.error("publish failed error=%s", exc)
        print(f"FEHLER: {exc}", file=sys.stderr)
        sys.exit(1)
