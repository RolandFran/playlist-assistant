from client import SpotifyClient
from collector import iso_to_unix_ms

CHECKPOINT = "2026-08-07T18:43:15.162Z"

client = SpotifyClient()
items = client.get_recently_played_since(iso_to_unix_ms(CHECKPOINT))

print(f"Checkpoint:       {CHECKPOINT}")
print(f"Empfangen:        {len(items)}")
print(f"Spotify-Requests: {client.request_count}")

if items:
    print(f"Aeltester Play:   {items[0]['played_at']}")
    print(f"Neuester Play:    {items[-1]['played_at']}")
