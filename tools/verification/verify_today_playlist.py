import json
from pathlib import Path
import sys

PROJECT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_DIR))

from client import SpotifyClient

TODAY_JSON_PATH = Path("reports") / "today_tracks.json"
TARGET_PLAYLIST_NAME = "Today"


def load_expected():
    with TODAY_JSON_PATH.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    tracks = payload.get("tracks", [])
    expected = []

    for track in tracks:
        expected.append({
            "uri": track.get("track_uri"),
            "name": track.get("track_name"),
            "artist": track.get("artist_name"),
        })

    return expected


def normalize_playlist_item(item):
    track = item.get("item") or item.get("track") or {}

    return {
        "uri": track.get("uri"),
        "name": track.get("name"),
        "artist": ", ".join(
            artist.get("name", "")
            for artist in track.get("artists", [])
        ),
    }


def main():
    expected = load_expected()

    client = SpotifyClient()

    playlist = client.find_owned_playlist_by_name(TARGET_PLAYLIST_NAME)

    if playlist is None:
        raise RuntimeError(
            f"Playlist {TARGET_PLAYLIST_NAME!r} wurde nicht gefunden."
        )

    actual_items = client.get_playlist_items(playlist["id"])
    actual = [
        normalize_playlist_item(item)
        for item in actual_items
    ]

    print(f"Playlist-ID:        {playlist['id']}")
    print(f"Expected Tracks:    {len(expected)}")
    print(f"Spotify Tracks:     {len(actual)}")
    print(f"Spotify-Requests:   {client.request_count}")
    print()

    compare_count = min(len(expected), len(actual))

    mismatches = []

    for index in range(compare_count):
        if expected[index]["uri"] != actual[index]["uri"]:
            mismatches.append(index)

    count_ok = len(expected) == len(actual)
    order_ok = count_ok and not mismatches

    print(f"Track-Anzahl korrekt: {'JA' if count_ok else 'NEIN'}")
    print(f"Reihenfolge korrekt:  {'JA' if order_ok else 'NEIN'}")
    print()

    print("Erste 20 Positionen:")
    print("-" * 100)

    rows = min(20, compare_count)

    for index in range(rows):
        exp = expected[index]
        act = actual[index]
        match = exp["uri"] == act["uri"]

        print(
            f"{index + 1:>3}. "
            f"{'OK ' if match else 'ERR'} | "
            f"SOLL: {exp['artist']} - {exp['name']}"
        )

        if not match:
            print(
                f"     IST : {act['artist']} - {act['name']}"
            )

    if mismatches:
        first = mismatches[0]

        print()
        print(f"Erste Abweichung an Position {first + 1}:")
        print(
            f"  SOLL: {expected[first]['artist']} - "
            f"{expected[first]['name']}"
        )
        print(
            f"  IST : {actual[first]['artist']} - "
            f"{actual[first]['name']}"
        )

        print()
        print(f"Abweichende Positionen gesamt: {len(mismatches)}")
    elif count_ok:
        print()
        print("Alle Positionen stimmen mit today_tracks.json ueberein.")

    if len(expected) != len(actual):
        print()
        print(
            "Hinweis: Die Anzahl unterscheidet sich. "
            "Reihenfolgenvergleich ist deshalb nicht vollstaendig."
        )


if __name__ == "__main__":
    main()
