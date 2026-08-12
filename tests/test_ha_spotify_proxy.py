import json
import os
import unittest
from io import BytesIO
from urllib.error import HTTPError
from unittest.mock import patch

from ha_app.client import SpotifyApiError, SpotifyClient


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
        self.assertEqual(requests[2], {
            "operation": "playlist_items",
            "path": {"playlist_id": "playlist"},
            "params": {"limit": 50, "offset": 0},
            "json": None,
        })
        self.assertNotIn("access_token", json.dumps(requests))

    def test_playlist_items_follow_spotify_pagination_parameters(self):
        requests = []
        responses = iter((
            _Response({"items": [{"item": {"uri": "spotify:track:1"}}], "next": "https://api.spotify.com/v1/playlists/playlist/tracks?limit=50&offset=50"}),
            _Response({"items": [{"item": {"uri": "spotify:track:2"}}], "next": None}),
        ))
        def open_request(request, timeout):
            requests.append(json.loads(request.data))
            return next(responses)

        with patch.dict(os.environ, self.env, clear=True), patch("ha_app.client.urllib.request.urlopen", open_request):
            items = SpotifyClient().get_playlist_items("playlist")

        self.assertEqual(len(items), 2)
        self.assertEqual(requests[1]["operation"], "playlist_items")
        self.assertEqual(requests[1]["path"], {"playlist_id": "playlist"})
        self.assertEqual(requests[1]["params"], {"limit": "50", "offset": "50"})

    def test_playlist_item_proxy_failure_logs_safe_status_and_spotify_detail(self):
        error = HTTPError(
            self.env["PLAYLIST_ASSISTANT_SPOTIFY_PROXY"],
            403,
            "Forbidden",
            None,
            BytesIO(b'{"error":"Insufficient client scope"}'),
        )
        with patch.dict(os.environ, self.env, clear=True), \
                patch("ha_app.client.urllib.request.urlopen", side_effect=error), \
                self.assertLogs("playlist_assistant.spotify", "ERROR") as logs:
            client = SpotifyClient()
            with self.assertRaisesRegex(SpotifyApiError, "HTTP 403.*Insufficient client scope") as caught:
                client.get_playlist_items("playlist")

        self.assertEqual(caught.exception.operation, "playlist_items")
        self.assertEqual(caught.exception.http_status, 403)
        self.assertIn("operation=playlist_items status=403 detail=Insufficient client scope", logs.output[0])
        self.assertNotIn(self.env["SUPERVISOR_TOKEN"], "\n".join(logs.output))
