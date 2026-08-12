import unittest

from sync import find_today_sources, normalize_playlist_items


class _SpotifyClient:
    def get_all_user_playlists(self):
        return [
            {
                "id": "source-id",
                "name": "Source",
                "description": "#today-source",
                "snapshot_id": "snapshot",
                "items": {"total": 2},
            }
        ]


class SourceSyncApiShapeTests(unittest.TestCase):
    def test_source_discovery_uses_current_playlist_items_total(self):
        sources = find_today_sources(_SpotifyClient())

        self.assertEqual(sources[0]["spotify_track_total"], 2)

    def test_source_items_use_current_item_field_without_legacy_track_fallback(self):
        rows = normalize_playlist_items([
            {
                "item": {
                    "uri": "spotify:track:one",
                    "name": "One",
                    "artists": [{"name": "Artist"}],
                },
                "added_at": "2026-01-01T00:00:00Z",
            },
            {
                "track": {
                    "uri": "spotify:track:legacy",
                    "name": "Legacy",
                    "artists": [{"name": "Artist"}],
                },
            },
        ])

        self.assertEqual(rows, [
            ("spotify:track:one", "One", "Artist", "2026-01-01T00:00:00Z"),
        ])
