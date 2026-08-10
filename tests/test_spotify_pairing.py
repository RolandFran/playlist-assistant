import json
import unittest
from unittest.mock import patch

from ha_app.spotify_pairing import LOOPBACK_REDIRECT, PairingSession, encrypt_import, validate_pairing_document
from tools.spotify_local_login import LOOPBACK_HOST, LOOPBACK_PORT, authorization_url, create_listener, exchange_code, pkce_challenge, validate_callback


class SpotifyPairingTests(unittest.TestCase):
    def test_pkce_and_callback_state(self):
        self.assertEqual(len(pkce_challenge("a" * 64)), 43)
        self.assertEqual(validate_callback("/callback?code=value&state=good", "good"), "value")
        with self.assertRaises(ValueError): validate_callback("/callback?code=value&state=bad", "good")

    def test_pairing_is_encrypted_one_time_and_tamper_safe(self):
        session = PairingSession("client", "scope")
        document = session.public_document()
        imported = encrypt_import(document, "refresh-token")
        self.assertNotIn("refresh-token", json.dumps(imported))
        self.assertEqual(session.decrypt_import(imported)["refresh_token"], "refresh-token")
        imported["ciphertext"] = ("A" if imported["ciphertext"][0] != "A" else "B") + imported["ciphertext"][1:]
        with self.assertRaises(ValueError): session.decrypt_import(imported)

    def test_pairing_validation_rejects_expiry_and_extra_fields(self):
        document = PairingSession("client", "scope").public_document()
        document["extra"] = True
        with self.assertRaises(ValueError): validate_pairing_document(document)

    def test_pairing_uses_the_registered_fixed_loopback_redirect(self):
        self.assertEqual(PairingSession("client", "scope").public_document()["loopback_redirect"], LOOPBACK_REDIRECT)
        self.assertEqual(LOOPBACK_REDIRECT, "http://127.0.0.1:8888/callback")

    @patch("tools.spotify_local_login.ThreadingHTTPServer")
    def test_listener_binds_only_the_fixed_loopback_address(self, server):
        create_listener(object)
        server.assert_called_once_with((LOOPBACK_HOST, LOOPBACK_PORT), object)

    @patch("tools.spotify_local_login.ThreadingHTTPServer", side_effect=OSError("occupied"))
    def test_busy_fixed_port_has_safe_actionable_error(self, _server):
        with self.assertRaisesRegex(RuntimeError, "Port 8888 on 127.0.0.1 is unavailable"):
            create_listener(object)

    @patch("tools.spotify_local_login.urllib.request.urlopen")
    def test_token_exchange_uses_exact_fixed_redirect(self, urlopen):
        response = urlopen.return_value.__enter__.return_value
        response.read.return_value = b'{"refresh_token":"token"}'
        exchange_code({"spotify_client_id": "client"}, "code", LOOPBACK_REDIRECT, "verifier")
        body = urlopen.call_args.args[0].data.decode()
        self.assertIn("redirect_uri=http%3A%2F%2F127.0.0.1%3A8888%2Fcallback", body)
        self.assertIn("redirect_uri=http%3A%2F%2F127.0.0.1%3A8888%2Fcallback", authorization_url({"spotify_client_id":"client","spotify_scopes":"scope"}, "state", "verifier"))
