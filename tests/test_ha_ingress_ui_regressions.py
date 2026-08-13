"""Regression coverage for the Home Assistant ingress settings UI."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "ha_app" / "ui"


class IngressUiRegressionTests(unittest.TestCase):
    def setUp(self):
        self.app = (UI / "app.js").read_text(encoding="utf-8")
        self.html = (UI / "index.html").read_text(encoding="utf-8")

    def test_playlist_settings_keep_today_size_and_use_one_weight_control(self):
        self.assertIn(
            "playlist.append(field('today_size',settings.today_size,limits.today_size),"
            "weight(settings.rare_weight)",
            self.app,
        )
        self.assertNotIn("playlist.children[", self.app)
        self.assertNotIn("replaceWith(weight", self.app)
        self.assertIn("range.name='rare_weight'", self.app)
        self.assertIn("error.dataset.errorFor='rare_weight'", self.app)
        self.assertIn("caption.append(rare,long)", self.app)
        self.assertIn("long.textContent=`${100-Number(range.value)} ${t.long_label}`", self.app)

    def test_spotify_visibility_targets_only_authorization_section(self):
        self.assertIn('id="settings-section"', self.html)
        self.assertIn('id="spotify-authorization-section"', self.html)
        self.assertIn(
            "q('#spotify-authorization-section').hidden=state.spotify.available",
            self.app,
        )
        self.assertNotIn("q('#settings-section').hidden", self.app)
