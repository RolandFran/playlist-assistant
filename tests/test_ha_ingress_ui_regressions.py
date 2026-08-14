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

    def test_settings_autosave_only_on_commit_events(self):
        self.assertNotIn("button(t.save", self.app)
        self.assertNotIn("onsubmit=", self.app)
        self.assertIn("input.onblur=()=>saveField(form,key,input.value)", self.app)
        self.assertIn("if(event.key==='Enter'){event.preventDefault();input.blur()}", self.app)
        self.assertIn("input.oninput=()=>setFieldError", self.app)
        self.assertIn("if(error||normalized===baseline)return", self.app)

    def test_slider_updates_live_but_persists_on_change(self):
        self.assertIn("range.oninput=()=>", self.app)
        self.assertIn("range.onchange=()=>saveField(form,'rare_weight',range.value)", self.app)
        self.assertIn("values.className='slider-values'", self.app)
        self.assertIn("values.append(longValue,range,rareValue)", self.app)
        self.assertIn("100-Number(value)", self.app)

    def test_switch_persists_immediately_and_uses_confirmed_state(self):
        self.assertIn("input.onchange=()=>saveField(form,'today_schedule_enabled',input.checked)", self.app)
        self.assertIn("form.querySelectorAll('input').forEach(input=>input.disabled=true)", self.app)
        self.assertIn("state=result.state;status();renderSettings()", self.app)
        self.assertNotIn("schedule-status", self.app)
        self.assertNotIn('id="schedule-status"', self.html)

    def test_actions_keep_status_in_the_triggering_button(self):
        self.assertIn("activeAction=null", self.app)
        self.assertIn("if(activeAction||completedAction)return", self.app)
        self.assertIn("b.disabled=!state.spotify.available||Boolean(activeAction)||Boolean(completedAction)", self.app)
        self.assertIn("if(activeAction===action)return t[`${action}_active`]", self.app)
        self.assertIn("if(completedAction===action)return completionMessage(action)", self.app)
        self.assertIn("setTimeout(()=>{completedAction=null;actions()},1800)", self.app)
        self.assertNotIn("action-message", self.app)
        self.assertNotIn('id="action-message"', self.html)

    def test_preview_completion_uses_only_reliable_existing_count(self):
        self.assertIn("action==='preview'&&Number.isInteger(state.today.count)", self.app)
        self.assertNotIn("['preview','publish','run']", self.app)

    def test_track_columns_are_declarative_and_days_are_frontend_only(self):
        self.assertIn("const trackColumns=", self.app)
        self.assertIn("key:'days'", self.app)
        self.assertIn("function daysSinceLastPlayed(value)", self.app)
        self.assertIn("head.replaceChildren(...trackColumns.map", self.app)
        self.assertIn("trackColumns.forEach(column=>", self.app)
        self.assertIn('id="track-columns"', self.html)
        for language, expected in (("en", "Days"), ("de", "Tage")):
            translations = json.loads((UI / "i18n" / f"{language}.json").read_text(encoding="utf-8"))
            self.assertEqual(translations["days"], expected)
