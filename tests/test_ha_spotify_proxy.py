import json
import os
import unittest
from unittest.mock import patch

from ha_app.client import SpotifyClient


class _Response:
    def __init__(self, body): self.body = body
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self): return json.dumps(self.body).encode()


class ProxyClientTests(unittest.TestCase):
    def setUp(self):
        self.env = {"PLAYLIST_ASSISTANT_SPOTIFY_PROXY": "http://supervisor/core/api/playlist_assistant/spotify", "SUPERVISOR_TOKEN": "supervisor"}

    def test_operations_are_mapped_without_spotify_credentials(self):
        requests = []
        def open_request(request, timeout):
            requests.append(json.loads(request.data)); return _Response({"id": "user"})
        with patch.dict(os.environ, self.env, clear=True), patch("ha_app.client.urllib.request.urlopen", open_request):
            client = SpotifyClient()
            client.get_recently_played_since(None)
            client.get_all_user_playlists()
            client.get_playlist_items("playlist")
            client.create_private_playlist("Today")
            client.rename_playlist("playlist", "Today")
            client.set_playlist_private("playlist")
            client.replace_playlist_items("playlist", ["spotify:track:1"])
        self.assertEqual([item["operation"] for item in requests], ["recently_played", "user_playlists", "playlist_items", "current_user", "create_playlist", "playlist_details", "playlist_details", "replace_items"])
        self.assertNotIn("access_token", json.dumps(requests))
