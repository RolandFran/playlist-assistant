"""Focused coverage for the historical proxy-observability checkpoint."""

from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from historical_test.playlist_assistant_historical_test.client import SpotifyClient


class _Response:
    status = 200

    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return json.dumps(self.body).encode()


class HistoricalProxyObservabilityCheckpointTests(unittest.TestCase):
    def test_metadata_put_keeps_the_historical_target_payload_and_safe_logs(self):
        requests = []

        def open_request(request, timeout):
            requests.append(json.loads(request.data))
            return _Response({"snapshot_id": "snapshot"})

        environment = {
            "PLAYLIST_ASSISTANT_SPOTIFY_PROXY": "http://supervisor/core/api/playlist_assistant_historical_test/spotify",
            "SUPERVISOR_TOKEN": "historical-supervisor-token",
        }
        with patch.dict(os.environ, environment, clear=True), \
                patch("historical_test.playlist_assistant_historical_test.client.urllib.request.urlopen", open_request), \
                self.assertLogs("playlist_assistant_historical_test.spotify", "DEBUG") as logs:
            SpotifyClient().prepare_private_playlist("persisted-target", "Renamed Historical Target")

        self.assertEqual(requests, [{
            "operation": "playlist_details",
            "path": {"playlist_id": "persisted-target"},
            "params": None,
            "json": {"name": "Renamed Historical Target", "public": False},
        }])
        output = "\n".join(logs.output)
        self.assertIn("spotify_proxy_request operation=playlist_details method=POST", output)
        self.assertIn("json_keys=['name', 'public']", output)
        self.assertIn("spotify_proxy_response operation=playlist_details", output)
        self.assertNotIn(environment["SUPERVISOR_TOKEN"], output)


if __name__ == "__main__":
    unittest.main()
