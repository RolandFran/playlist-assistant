import unittest

from runtime_config import RuntimeConfig
from scoring import calculate_combined_score


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
                RuntimeConfig(rare_weight=100, long_weight=0),
            ),
            80.0,
        )
