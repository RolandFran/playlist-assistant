import unittest

from runtime_config import RuntimeConfig
from scoring import calculate_combined_score, select_today


class ScoringConfigTests(unittest.TestCase):
    def test_default_fifty_fifty_scoring_is_unchanged(self):
        config = RuntimeConfig()

        self.assertEqual(
            calculate_combined_score(80.0, 20.0, config),
            50.0,
        )

    def test_weighting_uses_normalized_user_values(self):
        self.assertEqual(
            calculate_combined_score(
                80.0,
                20.0,
                RuntimeConfig(rare_weight=100),
            ),
            80.0,
        )

    def test_external_config_controls_selection_size_and_artist_gap(self):
        candidates = [
            {"artist_name": "Artist A", "track_name": "One"},
            {"artist_name": "Artist A", "track_name": "Two"},
            {"artist_name": "Artist B", "track_name": "Three"},
        ]

        selected, relaxed_count = select_today(candidates, size=2, artist_gap=1)

        self.assertEqual([row["track_name"] for row in selected], ["One", "Three"])
        self.assertEqual(relaxed_count, 0)
