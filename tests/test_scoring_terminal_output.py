import tempfile
import unittest

from application_paths import ApplicationPaths
from runtime_config import RuntimeConfig
from scoring import terminal_summary_lines


class ScoringTerminalOutputTests(unittest.TestCase):
    def test_short_summary_uses_requested_labels_without_diagnostic_details(self):
        with tempfile.TemporaryDirectory() as directory:
            lines = terminal_summary_lines(
                paths=ApplicationPaths.from_data_dir(directory),
                config=RuntimeConfig(artist_gap=7, rare_weight=60),
                candidate_count=42,
                max_play_count=13,
                max_days_since=12.5,
                today_count=20,
            )

        output = "\n".join(lines)
        self.assertIn("Bewertete Titel:      42", output)
        self.assertIn("Meiste Wiedergaben:   13×", output)
        self.assertIn("Ausgewählte Titel für Today: 20", output)
        self.assertIn("Künstlerabstand:      7 Titel", output)
        self.assertIn("Scoring-Report:", output)
        self.assertIn("Today-Liste:", output)
        self.assertIn("Spotify-Importdaten:", output)
        self.assertNotIn("Input-Fingerprint", output)
        self.assertNotIn("Gap-Ausnahmen", output)
