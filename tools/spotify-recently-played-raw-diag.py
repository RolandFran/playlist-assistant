import os
import json

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth


CHECKPOINT = "2026-08-07T18:43:15.162Z"
LIMIT = 50


def iso_to_unix_ms(value):
    from datetime import datetime

    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return int(dt.timestamp() * 1000)


def main():
    load_dotenv()

    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.getenv(
        "SPOTIFY_REDIRECT_URI",
        "http://127.0.0.1:8888/callback",
    )

    if not client_id or not client_secret:
        raise RuntimeError(
            "Spotify-Zugangsdaten fehlen. "
            "Pruefe SPOTIFY_CLIENT_ID und SPOTIFY_CLIENT_SECRET in .env."
        )

    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope="user-read-recently-played",
        cache_path=".cache-playlist-assistant",
        open_browser=True,
    )

    sp = spotipy.Spotify(
        auth_manager=auth_manager,
        retries=0,
        status_retries=0,
    )

    after_ms = iso_to_unix_ms(CHECKPOINT)

    print("=== REQUEST 1: after=<checkpoint> ===")
    result = sp.current_user_recently_played(
        limit=LIMIT,
        after=after_ms,
    )

    print("items:", len(result.get("items", [])))
    print("total:", result.get("total"))
    print("href:", result.get("href"))
    print("next:", result.get("next"))
    print("cursors:", json.dumps(result.get("cursors"), indent=2))

    items = result.get("items", [])

    if items:
        times = [item["played_at"] for item in items]
        print("oldest:", min(times))
        print("newest:", max(times))

    print()
    print("=== REQUEST 2: Spotipy sp.next(result) ===")

    if result.get("next"):
        result2 = sp.next(result)

        print("items:", len(result2.get("items", [])))
        print("total:", result2.get("total"))
        print("href:", result2.get("href"))
        print("next:", result2.get("next"))
        print("cursors:", json.dumps(result2.get("cursors"), indent=2))

        items2 = result2.get("items", [])

        if items2:
            times2 = [item["played_at"] for item in items2]
            print("oldest:", min(times2))
            print("newest:", max(times2))
    else:
        print("Kein next-Link vorhanden.")

    print()
    print("=== REQUEST 3: before=<oldest first page> ===")

    if items:
        oldest_ms = min(
            iso_to_unix_ms(item["played_at"])
            for item in items
        )

        result3 = sp.current_user_recently_played(
            limit=LIMIT,
            before=oldest_ms,
        )

        print("items:", len(result3.get("items", [])))
        print("total:", result3.get("total"))
        print("href:", result3.get("href"))
        print("next:", result3.get("next"))
        print("cursors:", json.dumps(result3.get("cursors"), indent=2))

        items3 = result3.get("items", [])

        if items3:
            times3 = [item["played_at"] for item in items3]
            print("oldest:", min(times3))
            print("newest:", max(times3))
    else:
        print("Keine Items in Request 1.")


if __name__ == "__main__":
    main()
