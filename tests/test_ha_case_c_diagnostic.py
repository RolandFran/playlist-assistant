import io
import json
import os
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

from ha_app.client import _ProxySpotify
from ha_app.service import CASE_C_TIMEOUT_SECONDS, CASE_C_URL, run_case_c_diagnostic


class _Response:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class CaseCDiagnosticTests(unittest.TestCase):
    def test_posts_fixed_metadata_request_without_proxy_or_playlist_content_changes(self):
        captured = []

        def urlopen(request, timeout):
            captured.append((request, timeout))
            return _Response()

        with patch.dict(os.environ, {"SUPERVISOR_TOKEN": "supervisor-token"}, clear=True), \
                patch.object(_ProxySpotify, "_call", side_effect=AssertionError("proxy must be bypassed")), \
                patch("ha_app.service.urllib.request.urlopen", urlopen):
            result = run_case_c_diagnostic("playlist-id", "Case C temporary name")

        request, timeout = captured[0]
        self.assertEqual(result, "Case C: HTTP 200 — request completed.")
        self.assertEqual(request.full_url, CASE_C_URL)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.headers["Content-type"], "application/json")
        self.assertEqual(request.headers["Authorization"], "Bearer supervisor-token")
        self.assertEqual(timeout, CASE_C_TIMEOUT_SECONDS)
        self.assertEqual(json.loads(request.data), {
            "operation": "playlist_details",
            "path": {"playlist_id": "playlist-id"},
            "params": None,
            "json": {"name": "Case C temporary name", "public": False},
        })
        self.assertNotIn("uris", request.data.decode("utf-8"))
        self.assertNotIn("supervisor-token", result)

    def test_surfaces_http_502_without_exposing_response_details_or_authorization(self):
        error = HTTPError(CASE_C_URL, 502, "Bad Gateway", {}, io.BytesIO(b'{"error":"secret"}'))
        with patch.dict(os.environ, {"SUPERVISOR_TOKEN": "supervisor-token"}, clear=True), \
                patch("ha_app.service.urllib.request.urlopen", side_effect=error):
            result = run_case_c_diagnostic("playlist-id", "Case C temporary name")

        self.assertEqual(result, "Case C: HTTP 502 — Home Assistant returned an error response.")
        self.assertNotIn("secret", result)
        self.assertNotIn("supervisor-token", result)

    def test_missing_supervisor_token_is_safe(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "Supervisor authorization is unavailable") as caught:
                run_case_c_diagnostic("playlist-id", "Case C temporary name")

        self.assertNotIn("SUPERVISOR_TOKEN", str(caught.exception))
