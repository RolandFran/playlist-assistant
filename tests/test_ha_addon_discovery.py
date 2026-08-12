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


def _supervisor_response(addons):
    return {"result": "ok", "data": {"addons": addons}}


class AddonDiscoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_uses_exact_name_and_dns_safe_supervisor_slug(self):
        session = _Session(_supervisor_response([{
            "name": "Playlist Assistant",
            "slug": "59a782bb_any_supervisor_slug",
            "repository": "https://example.invalid/apps",
            "installed": "0.1.11",
        }]))
        with patch.dict(os.environ, {"SUPERVISOR_TOKEN": "supervisor-token"}, clear=False):
            url = await async_discover_addon_base_url(session)

        self.assertEqual(url, "http://59a782bb-any-supervisor-slug:8098")
        self.assertEqual(
            session.calls,
            [(SUPERVISOR_ADDONS_URL, {"Authorization": "Bearer supervisor-token"})],
        )

    async def test_ignores_installed_field_shape(self):
        for installed in (False, None, "0.1.12"):
            with self.subTest(installed=installed):
                session = _Session(_supervisor_response([{
                    "name": "Playlist Assistant", "slug": "arbitrary_slug", "installed": installed,
                }]))
                with patch.dict(os.environ, {"SUPERVISOR_TOKEN": "supervisor-token"}, clear=False):
                    url = await async_discover_addon_base_url(session)
                self.assertEqual(url, "http://arbitrary-slug:8098")

    async def test_reports_every_supervisor_candidate_when_no_name_matches(self):
        session = _Session(_supervisor_response([{
            "name": "Other app", "slug": "other", "repository": "https://example.invalid/apps", "installed": False,
        }]))
        with patch.dict(os.environ, {"SUPERVISOR_TOKEN": "supervisor-token"}, clear=False):
            with self.assertRaisesRegex(AddonDiscoveryError, "Other app.*other.*example.invalid.*False"):
                await async_discover_addon_base_url(session)

    async def test_reports_multiple_exact_name_matches(self):
        session = _Session(_supervisor_response([
            {"name": "Playlist Assistant", "slug": "first", "repository": "one", "installed": None},
            {"name": "Playlist Assistant", "slug": "second", "repository": "two", "installed": "0.1"},
        ]))
        with patch.dict(os.environ, {"SUPERVISOR_TOKEN": "supervisor-token"}, clear=False):
            with self.assertRaisesRegex(AddonDiscoveryError, "found 2.*first.*second"):
                await async_discover_addon_base_url(session)

    async def test_requires_supervisor_token(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(AddonDiscoveryError):
                await async_discover_addon_base_url(_Session(_supervisor_response([])))

    async def test_rejects_unsuccessful_supervisor_result(self):
        with patch.dict(os.environ, {"SUPERVISOR_TOKEN": "supervisor-token"}, clear=False):
            with self.assertRaisesRegex(AddonDiscoveryError, "unsuccessful"):
                await async_discover_addon_base_url(_Session({"result": "error", "data": {"addons": []}}))

    async def test_rejects_missing_data_object(self):
        with patch.dict(os.environ, {"SUPERVISOR_TOKEN": "supervisor-token"}, clear=False):
            with self.assertRaisesRegex(AddonDiscoveryError, "no data object"):
                await async_discover_addon_base_url(_Session({"result": "ok"}))

    async def test_rejects_missing_addons_list(self):
        with patch.dict(os.environ, {"SUPERVISOR_TOKEN": "supervisor-token"}, clear=False):
            with self.assertRaisesRegex(AddonDiscoveryError, "no add-ons list"):
                await async_discover_addon_base_url(_Session({"result": "ok", "data": {}}))
