"""Focused tests for the HA-owned Spotify connection proof."""
import importlib
import sys
import types
import unittest
from urllib.parse import parse_qs, urlparse
from pathlib import Path


class _Response:
    def __init__(self, status, payload):
        self.status = status
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    def raise_for_status(self):
        if self.status >= 400:
            raise ValueError("http error")

    async def json(self):
        return self.payload


class _OAuthSession:
    def __init__(self, response):
        self.response = response
        self.requests = []

    async def async_request(self, method, url, **kwargs):
        self.requests.append((method, url, kwargs))
        return self.response


class _CoordinatorBase:
    def __init__(self, *_, **kwargs):
        self.update_method = kwargs["update_method"]


class _LocalOAuth2Implementation:
    def __init__(self, hass, domain, client_id, client_secret, authorize_url, token_url):
        self.hass = hass
        self._domain = domain
        self.client_id = client_id
        self.client_secret = client_secret
        self.authorize_url = authorize_url
        self.token_url = token_url

    @property
    def redirect_uri(self):
        return "http://wrong.example/auth/external/callback"

    async def async_generate_authorize_url(self, flow_id):
        return (
            f"{self.authorize_url}?response_type=code&client_id={self.client_id}"
            f"&redirect_uri={self.redirect_uri}&state={flow_id}"
        )


class _OAuthFlowHandler:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()

    async def async_step_auth(self, user_input=None):
        return user_input

    async def async_step_pick_implementation(self, user_input=None):
        self.picked_implementation = user_input
        return user_input

def _install_ha_stubs():
    voluptuous = types.ModuleType("voluptuous")
    voluptuous.Schema = lambda value: value
    voluptuous.Required = lambda value: value
    homeassistant = types.ModuleType("homeassistant")
    config_entries = types.ModuleType("homeassistant.config_entries")
    config_entries.ConfigFlow = type("ConfigFlow", (), {"__init_subclass__": classmethod(lambda cls, **kwargs: None)})
    config_entries.SOURCE_REAUTH = "reauth"
    const = types.ModuleType("homeassistant.const")
    const.CONF_CLIENT_ID = "client_id"
    const.CONF_CLIENT_SECRET = "client_secret"
    data_entry_flow = types.ModuleType("homeassistant.data_entry_flow")
    data_entry_flow.FlowResult = dict
    exceptions = types.ModuleType("homeassistant.exceptions")
    exceptions.OAuth2TokenRequestReauthError = type("OAuth2TokenRequestReauthError", (Exception,), {})
    helpers = types.ModuleType("homeassistant.helpers")
    components = types.ModuleType("homeassistant.components")
    http = types.ModuleType("homeassistant.components.http")
    class _HomeAssistantView:
        def json(self, payload, status_code=200, headers=None):
            return {"payload": payload, "status_code": status_code, "headers": headers}
    http.HomeAssistantView = _HomeAssistantView
    application_credentials = types.ModuleType("homeassistant.components.application_credentials")
    application_credentials.ClientCredential = type("ClientCredential", (), {})
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    oauth2 = types.ModuleType("homeassistant.helpers.config_entry_oauth2_flow")
    oauth2.OAuth2Session = _OAuthSession
    oauth2.LocalOAuth2Implementation = _LocalOAuth2Implementation
    oauth2.AbstractOAuth2FlowHandler = _OAuthFlowHandler
    coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")
    coordinator.DataUpdateCoordinator = _CoordinatorBase
    sys.modules.update({
        "voluptuous": voluptuous,
        "homeassistant": homeassistant,
        "homeassistant.config_entries": config_entries,
        "homeassistant.const": const,
        "homeassistant.data_entry_flow": data_entry_flow,
        "homeassistant.exceptions": exceptions,
        "homeassistant.components": components,
        "homeassistant.components.http": http,
        "homeassistant.components.application_credentials": application_credentials,
        "homeassistant.core": core,
        "homeassistant.helpers": helpers,
        "homeassistant.helpers.config_entry_oauth2_flow": oauth2,
        "homeassistant.helpers.update_coordinator": coordinator,
    })


class SpotifyConnectionTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        _install_ha_stubs()
        cls.spotify = importlib.import_module("custom_components.playlist_assistant.spotify")
        cls.coordinator_module = importlib.import_module("custom_components.playlist_assistant.coordinator")

    async def test_me_request_exposes_only_safe_profile_fields(self):
        session = _OAuthSession(_Response(200, {"id": "account-123", "display_name": "Ada"}))
        profile = await self.spotify.SpotifyApi(session).async_get_profile()
        self.assertEqual(session.requests, [("GET", "https://api.spotify.com/v1/me", {})])
        self.assertEqual(profile, {"account_id": "account-123", "display_name": "Ada"})

    async def test_unauthorized_me_marks_reauth_required_and_starts_ha_reauth(self):
        class Entry:
            def __init__(self): self.calls = 0
            def async_start_reauth(self, hass): self.calls += 1
        entry = Entry()
        api = self.spotify.SpotifyApi(_OAuthSession(_Response(401, {})))
        coordinator = self.coordinator_module.PlaylistAssistantCoordinator(object(), spotify=api, entry=entry)
        data = await coordinator._async_update_data()
        self.assertEqual(data["spotify"], {"state": "reauth_required"})
        self.assertEqual(entry.calls, 1)

    async def test_proxy_request_keeps_401_as_an_auth_error(self):
        api = self.spotify.SpotifyApi(_OAuthSession(_Response(401, {"error": {"message": "Unauthorized"}})))

        with self.assertRaises(self.spotify.SpotifyAuthError):
            await api.async_request("GET", "/playlists/source/tracks")

    async def test_proxy_request_keeps_403_spotify_detail(self):
        api = self.spotify.SpotifyApi(_OAuthSession(_Response(403, {"error": {"message": "Insufficient client scope"}})))

        with self.assertRaises(self.spotify.SpotifyRequestError) as caught:
            await api.async_request("GET", "/playlists/source/tracks")

        self.assertEqual(caught.exception.status, 403)
        self.assertEqual(caught.exception.detail, "Insufficient client scope")

    async def test_playlist_write_accepts_an_empty_success_response(self):
        class _EmptyResponse(_Response):
            async def json(self):
                raise ValueError("empty response body")

        api = self.spotify.SpotifyApi(_OAuthSession(_EmptyResponse(200, None)))

        result = await api.async_request(
            "PUT", "/playlists/playlist", json={"name": "Today", "public": False}
        )

        self.assertEqual(result, {})

    async def test_playlist_write_accepts_a_none_success_payload(self):
        api = self.spotify.SpotifyApi(_OAuthSession(_Response(200, None)))

        result = await api.async_request(
            "PUT", "/playlists/playlist", json={"name": "Today", "public": False}
        )

        self.assertEqual(result, {})

    async def test_successful_non_object_response_remains_a_connection_error(self):
        api = self.spotify.SpotifyApi(_OAuthSession(_Response(200, ["not", "an", "object"])))

        with self.assertRaises(self.spotify.SpotifyConnectionError):
            await api.async_request("PUT", "/playlists/playlist", json={"name": "Today"})

    async def test_proxy_request_keeps_400_spotify_detail(self):
        api = self.spotify.SpotifyApi(
            _OAuthSession(_Response(400, {"error": {"message": "Invalid playlist details"}}))
        )

        with self.assertRaises(self.spotify.SpotifyRequestError) as caught:
            await api.async_request("PUT", "/playlists/playlist", json={"public": False})

        self.assertEqual(caught.exception.status, 400)
        self.assertEqual(caught.exception.detail, "Invalid playlist details")

    async def test_playlist_proxy_reuses_the_connected_integration_session(self):
        api_module = importlib.import_module("custom_components.playlist_assistant.api")

        class ConnectedSpotify:
            def __init__(self):
                self.requests = []

            async def async_request(self, method, path, **kwargs):
                self.requests.append((method, path, kwargs))
                return {"id": "persisted-target", "name": "Today", "public": False}

        class Request:
            async def json(self):
                return {"operation": "playlist", "path": {"playlist_id": "persisted-target"}}

        spotify = ConnectedSpotify()
        hass = types.SimpleNamespace(data={"playlist_assistant": {"entry": {"spotify": spotify}}})

        response = await api_module.SpotifyProxyView(hass).post(Request())

        self.assertEqual(response["status_code"], 200)
        self.assertEqual(response["payload"]["id"], "persisted-target")
        self.assertEqual(
            spotify.requests,
            [("GET", "/playlists/persisted-target", {"params": None, "json": None})],
        )

    def test_config_flow_requests_only_profile_scope_and_exact_redirect(self):
        application_credentials = importlib.import_module("custom_components.playlist_assistant.application_credentials")
        credential = types.SimpleNamespace(client_id="client", client_secret="secret")
        implementation = self._asyncioRunner.run(
            application_credentials.async_get_auth_implementation(
                object(), "playlist_assistant", credential
            )
        )
        authorization_url = self._asyncioRunner.run(
            implementation.async_generate_authorize_url("flow-id")
        )
        query = parse_qs(urlparse(authorization_url).query)
        self.assertEqual(query["redirect_uri"], ["https://my.home-assistant.io/redirect/oauth"])
        config_flow = importlib.import_module("custom_components.playlist_assistant.config_flow")
        self.assertEqual(config_flow.ConfigFlow.extra_authorize_data.fget(object()), {"scope": "user-read-private user-read-recently-played playlist-read-private playlist-read-collaborative playlist-modify-private playlist-modify-public", "show_dialog": "true"})
        constants = Path("custom_components/playlist_assistant/const.py").read_text(encoding="utf-8")
        self.assertIn('"user-read-recently-played"', constants)
        self.assertIn('SPOTIFY_REDIRECT_URI = "https://my.home-assistant.io/redirect/oauth"', constants)

    def test_application_credentials_exposes_the_dashboard_as_a_placeholder(self):
        application_credentials = importlib.import_module("custom_components.playlist_assistant.application_credentials")

        placeholders = self._asyncioRunner.run(
            application_credentials.async_get_description_placeholders(object())
        )

        self.assertEqual(
            placeholders,
            {
                "spotify_developer_dashboard_url": "https://developer.spotify.com/dashboard",
                "redirect_uri": "https://my.home-assistant.io/redirect/oauth",
            },
        )

    def test_reauth_reuses_managed_credential_implementation(self):
        config_flow = importlib.import_module("custom_components.playlist_assistant.config_flow")
        flow = object.__new__(config_flow.ConfigFlow)
        entry = types.SimpleNamespace(data={"auth_implementation": "playlist_assistant"})
        flow._get_reauth_entry = lambda: entry

        result = self._asyncioRunner.run(flow.async_step_reauth_confirm({}))

        self.assertEqual(result, {"implementation": "playlist_assistant"})
        self.assertEqual(flow.picked_implementation, {"implementation": "playlist_assistant"})

    def test_user_flow_uses_home_assistant_application_credentials(self):
        config_flow = importlib.import_module("custom_components.playlist_assistant.config_flow")
        flow = object.__new__(config_flow.ConfigFlow)

        result = self._asyncioRunner.run(flow.async_step_user())

        self.assertIsNone(result)
        self.assertIsNone(flow.picked_implementation)

    def test_oauth_entry_never_stores_client_credentials(self):
        config_flow = importlib.import_module("custom_components.playlist_assistant.config_flow")
        flow = object.__new__(config_flow.ConfigFlow)
        flow.source = "user"

        async def set_unique_id(_value):
            return None

        flow.async_set_unique_id = set_unique_id
        flow._abort_if_unique_id_configured = lambda: None
        flow.async_create_entry = lambda **kwargs: kwargs
        data = {"auth_implementation": "playlist_assistant", "token": {"access_token": "token"}}

        result = self._asyncioRunner.run(flow.async_oauth_create_entry(data))

        self.assertEqual(result["data"], data)
        self.assertNotIn("client_id", result["data"])
        self.assertNotIn("client_secret", result["data"])
