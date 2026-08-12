"""Authenticated client for the add-on's private Docker-network endpoint."""
from __future__ import annotations
import os

from aiohttp import ClientResponseError

SUPERVISOR_ADDONS_URL = "http://supervisor/addons"
ADDON_INGRESS_PORT = 8098
ADDON_NAME = "Playlist Assistant"


class AddonDiscoveryError(RuntimeError):
    """The Supervisor could not identify the installed Playlist Assistant app."""


async def async_discover_addon_base_url(session):
    """Resolve the app's Supervisor-assigned DNS name without hard-coding a repo prefix."""
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        raise AddonDiscoveryError("Supervisor token is unavailable; cannot discover the Playlist Assistant add-on.")

    headers = {"Authorization": f"Bearer {token}"}
    async with session.get(SUPERVISOR_ADDONS_URL, headers=headers) as response:
        response.raise_for_status()
        payload = await response.json()

    if not isinstance(payload, dict) or payload.get("result") != "ok":
        raise AddonDiscoveryError("Supervisor add-on discovery returned an unsuccessful response.")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise AddonDiscoveryError("Supervisor add-on discovery response has no data object.")
    addons = data.get("addons")
    if not isinstance(addons, list):
        raise AddonDiscoveryError("Supervisor add-on discovery response has no add-ons list.")

    # The Supervisor has already supplied the app list. Its ``installed`` field
    # is not stable across API versions, so identification uses the exact app
    # name and the Supervisor-provided slug without inferring either prefix or
    # suffix.
    matches = [addon for addon in addons if addon.get("name") == ADDON_NAME]
    if len(matches) != 1:
        candidates = [
            {
                "name": addon.get("name"),
                "slug": addon.get("slug"),
                "repository": addon.get("repository"),
                "installed": addon.get("installed"),
            }
            for addon in addons
        ]
        raise AddonDiscoveryError(
            "Expected exactly one Playlist Assistant add-on; "
            f"found {len(matches)}. "
            f"Supervisor add-ons: {candidates!r}"
        )

    # Supervisor documents this as {REPO}_{SLUG}; DNS hostnames use hyphens.
    return f"http://{matches[0]['slug'].replace('_', '-')}:{ADDON_INGRESS_PORT}"

class AddonBridge:
    def __init__(self, session, base_url, token):
        self._session, self._base_url = session, base_url.rstrip("/")
        self._headers = {"X-Playlist-Assistant-Bridge": token}
        self.data = {}

    async def state(self):
        async with self._session.get(self._base_url + "/bridge/state", headers=self._headers) as response:
            response.raise_for_status(); self.data = await response.json(); return self.data

    async def execute(self, action):
        async with self._session.post(self._base_url + "/bridge/actions/" + action, headers=self._headers) as response:
            response.raise_for_status(); self.data = await response.json(); return self.data

    async def schedule(self):
        return (await self.state())["schedule"]
