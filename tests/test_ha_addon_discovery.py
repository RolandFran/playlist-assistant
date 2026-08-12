"""Tests for Supervisor-based Playlist Assistant app discovery."""
import os
import unittest
from unittest.mock import patch

from custom_components.playlist_assistant.bridge import (
    AddonDiscoveryError,
    SUPERVISOR_ADDONS_URL,
    async_discover_addon_base_url,
)


class _Response:
    def __init__(self, payload):
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    def raise_for_status(self):
        return None

    async def json(self):
        return self.payload


class _Session:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, *, headers):
        self.calls.append((url, headers))
        return _Response(self.payload)


class AddonDiscoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_uses_supervisor_slug_and_dns_safe_hostname(self):
        session = _Session({"addons": [{"slug": "59a782bb_playlist_assistant"}]})
        with patch.dict(os.environ, {"SUPERVISOR_TOKEN": "supervisor-token"}, clear=False):
            url = await async_discover_addon_base_url(session)

        self.assertEqual(url, "http://59a782bb-playlist-assistant:8098")
        self.assertEqual(
            session.calls,
            [(SUPERVISOR_ADDONS_URL, {"Authorization": "Bearer supervisor-token"})],
        )

    async def test_does_not_assume_a_repository_prefix(self):
        session = _Session({"addons": [{"slug": "different_prefix_playlist_assistant"}]})
        with patch.dict(os.environ, {"SUPERVISOR_TOKEN": "supervisor-token"}, clear=False):
            url = await async_discover_addon_base_url(session)

        self.assertEqual(url, "http://different-prefix-playlist-assistant:8098")

    async def test_reports_missing_or_ambiguous_addon(self):
        with patch.dict(os.environ, {"SUPERVISOR_TOKEN": "supervisor-token"}, clear=False):
            with self.assertRaises(AddonDiscoveryError):
                await async_discover_addon_base_url(_Session({"addons": []}))
            with self.assertRaises(AddonDiscoveryError):
                await async_discover_addon_base_url(
                    _Session({"addons": [{"slug": "a_playlist_assistant"}, {"slug": "b_playlist_assistant"}]})
                )

    async def test_requires_supervisor_token(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(AddonDiscoveryError):
                await async_discover_addon_base_url(_Session({"addons": []}))
