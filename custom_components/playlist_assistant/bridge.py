"""Authenticated client for the add-on's private Docker-network endpoint."""
from __future__ import annotations
from aiohttp import ClientResponseError

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
