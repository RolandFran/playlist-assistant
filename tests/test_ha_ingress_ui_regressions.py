"""Regression coverage for the Home Assistant ingress settings UI."""
import json
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
        self.assertIn("left.append(long,longValue);right.append(rare,rareValue)", self.app)
        self.assertIn("caption.append(left,right)", self.app)

    def test_weight_slider_keeps_rare_weight_direction_and_displays_both_end_values(self):
        self.assertIn("range.name='rare_weight'", self.app)
        self.assertIn("longValue.textContent=100-Number(range.value)", self.app)
        self.assertIn("rareValue.textContent=range.value", self.app)
        self.assertIn("left.append(long,longValue);right.append(rare,rareValue)", self.app)
        for rare_weight, left, right in ((0, 100, 0), (50, 50, 50), (75, 25, 75), (100, 0, 100)):
            self.assertEqual(100 - rare_weight, left)
            self.assertEqual(rare_weight, right)

    def test_playlist_settings_use_clear_localized_wording(self):
        expected = {
            "de": {
                "playlist": "Neue Playlist", "today_size": "Länge", "target_playlist_name": "Name",
                "artist_gap": "Abstand zwischen Songs desselben Künstlers",
                "history_poll_minutes": "Hörverlauf aktualisieren alle", "minutes": "Minuten",
            },
            "en": {
                "playlist": "New playlist", "today_size": "Length", "target_playlist_name": "Name",
                "artist_gap": "Songs between tracks by the same artist",
                "history_poll_minutes": "Update listening history every", "minutes": "minutes",
            },
        }
        for language, values in expected.items():
            translations = json.loads((UI / "i18n" / f"{language}.json").read_text(encoding="utf-8"))
            for key, value in values.items():
                self.assertEqual(translations[key], value)

    def test_spotify_visibility_targets_only_authorization_section(self):
        self.assertIn('id="settings-section"', self.html)
        self.assertIn('id="spotify-authorization-section"', self.html)
        self.assertIn(
            "q('#spotify-authorization-section').hidden=state.spotify.available",
            self.app,
        )
        self.assertNotIn("q('#settings-section').hidden", self.app)

    def test_actions_show_progress_and_prevent_parallel_requests(self):
        self.assertIn("activeAction=null", self.app)
        self.assertIn("if(activeAction)return", self.app)
        self.assertIn("b.disabled=!state.spotify.available||Boolean(activeAction)", self.app)
        self.assertIn("activeAction=action;actionMessage(t[`${action}_running`],true);actions()", self.app)
        self.assertIn("button(activeAction===action?t[`${action}_active`]:t[action])", self.app)
        self.assertIn("finally{activeAction=null;actions()}", self.app)

    def test_actions_use_specific_completion_feedback_and_reliable_preview_count(self):
        self.assertIn("function completionMessage(action)", self.app)
        self.assertIn("t[`${action}_completed`]", self.app)
        self.assertIn("Number.isInteger(state.today.count)", self.app)
        self.assertNotIn("t.action_success", self.app)

    def test_action_feedback_translations_cover_every_action(self):
        for language in ("de", "en"):
            translations = json.loads((UI / "i18n" / f"{language}.json").read_text(encoding="utf-8"))
            for action in ("sync", "preview", "publish", "run"):
                self.assertTrue(translations[f"{action}_running"])
                self.assertTrue(translations[f"{action}_active"])
                self.assertTrue(translations[f"{action}_completed"])
