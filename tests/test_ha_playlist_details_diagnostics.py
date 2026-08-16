"""Focused tests for the temporary playlist-details diagnostic service path."""
import importlib
import sys
import types
import unittest


class _Response:
    def __init__(self, status, payload, *, headers=None, history=()):
        self.status = status
        self.payload = payload
        self.request_info = types.SimpleNamespace(headers=headers or {})
        self.history = history

    async def __aenter__(self): return self
    async def __aexit__(self, *_): return None
    def raise_for_status(self):
        if self.status >= 400: raise ValueError("http error")
    async def json(self): return self.payload


class _OAuthSession:
    def __init__(self, response): self.response = response; self.requests = []
    async def async_request(self, method, url, **kwargs):
        self.requests.append((method, url, kwargs))
        return self.response


def _install_stubs():
    aiohttp = types.ModuleType("aiohttp"); aiohttp.ClientError = type("ClientError", (Exception,), {})
    homeassistant = types.ModuleType("homeassistant"); exceptions = types.ModuleType("homeassistant.exceptions")
    exceptions.OAuth2TokenRequestReauthError = type("OAuth2TokenRequestReauthError", (Exception,), {})
    helpers = types.ModuleType("homeassistant.helpers"); oauth = types.ModuleType("homeassistant.helpers.config_entry_oauth2_flow")
    oauth.OAuth2Session = _OAuthSession
    sys.modules.update({"aiohttp": aiohttp, "homeassistant": homeassistant, "homeassistant.exceptions": exceptions,
                        "homeassistant.helpers": helpers, "homeassistant.helpers.config_entry_oauth2_flow": oauth})


class PlaylistDetailsDiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        _install_stubs()
        cls.diagnostics = importlib.import_module("custom_components.playlist_assistant.diagnostics")
        cls.spotify = importlib.import_module("custom_components.playlist_assistant.spotify")

    async def _run(self, variant, response):
        session = _OAuthSession(response)
        with self.assertLogs("custom_components.playlist_assistant.diagnostics", "INFO") as logs:
            result = await self.diagnostics.async_diagnose_playlist_details(
                session, playlist_id="target-123", name="Diagnostic rename", public=False, variant=variant
            )
        return session, result, " ".join(logs.output)

    async def test_direct_oauth_bypasses_spotify_api_and_sends_expected_request(self):
        original = self.diagnostics.SpotifyApi
        self.diagnostics.SpotifyApi = lambda _: self.fail("direct_oauth must bypass SpotifyApi")
        try:
            session, result, log = await self._run("direct_oauth", _Response(200, {}))
        finally:
            self.diagnostics.SpotifyApi = original
        self.assertEqual(result, {})
        self.assertEqual(session.requests, [("PUT", "https://api.spotify.com/v1/playlists/target-123", {"json": {"name": "Diagnostic rename", "public": False}})])
        self.assertIn("variant=direct_oauth method=PUT path=/playlists/target-123 status=200", log)

    async def test_spotify_api_uses_spotify_api_and_sends_same_logical_payload(self):
        calls = []
        original = self.diagnostics.SpotifyApi
        class SpySpotifyApi:
            def __init__(self, session): calls.append(session)
            async def async_request(self, method, path, **kwargs):
                calls.append((method, path, kwargs))
                kwargs["response_observer"](_Response(200, {}))
                return {}
        self.diagnostics.SpotifyApi = SpySpotifyApi
        try:
            session, result, log = await self._run("spotify_api", _Response(500, {}))
        finally:
            self.diagnostics.SpotifyApi = original
        self.assertEqual(result, {})
        self.assertEqual(calls[0], session)
        self.assertEqual(calls[1][:2], ("PUT", "/playlists/target-123"))
        self.assertEqual(calls[1][2]["json"], {"name": "Diagnostic rename", "public": False})
        self.assertIn("variant=spotify_api method=PUT path=/playlists/target-123 status=200", log)

    async def test_error_status_is_safe_and_credential_values_are_not_logged(self):
        response = _Response(502, {"error": {"message": "access_token=very-secret upstream failed"}}, headers={
            "Authorization": "Bearer very-secret", "Accept": "application/json", "User-Agent": "HA-test"
        })
        session = _OAuthSession(response)
        with self.assertLogs("custom_components.playlist_assistant.diagnostics", "INFO") as logs:
            with self.assertRaises(self.spotify.SpotifyRequestError) as caught:
                await self.diagnostics.async_diagnose_playlist_details(session, playlist_id="target-123", name="Rename", public=False, variant="direct_oauth")
        output = " ".join(logs.output)
        self.assertEqual(caught.exception.detail, "access_token=very-secret upstream failed")
        self.assertIn("status=502", output)
        self.assertIn("access_token=[REDACTED]", output)
        self.assertNotIn("very-secret", output)
        self.assertNotIn("Authorization", output)
