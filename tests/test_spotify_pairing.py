import json
import unittest
from unittest.mock import patch

from ha_app.spotify_pairing import PairingSession, encrypt_import, validate_pairing_document
from tools.spotify_local_login import pkce_challenge, validate_callback


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
        imported["ciphertext"] = imported["ciphertext"][:-1] + "A"
        with self.assertRaises(ValueError): session.decrypt_import(imported)

    def test_pairing_validation_rejects_expiry_and_extra_fields(self):
        document = PairingSession("client", "scope").public_document()
        document["extra"] = True
        with self.assertRaises(ValueError): validate_pairing_document(document)
