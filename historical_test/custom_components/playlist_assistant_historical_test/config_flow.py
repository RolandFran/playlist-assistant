"""Home Assistant owned Spotify OAuth2 configuration flow."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import SOURCE_REAUTH
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_entry_oauth2_flow

from .const import DOMAIN, SPOTIFY_SCOPE


class ConfigFlow(config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN):
    """Link one Spotify account directly to this integration."""

    VERSION = 3
    DOMAIN = DOMAIN

    @property
    def logger(self):
        """Return the OAuth helper logger."""
        return logging.getLogger(__name__)

    @property
    def extra_authorize_data(self) -> dict[str, str]:
        """Request only the scope needed for the connection proof."""
        return {"scope": SPOTIFY_SCOPE, "show_dialog": "true"}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Choose credentials managed by Home Assistant."""
        return await self.async_step_pick_implementation(user_input)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Ask for confirmation before linking the existing entry again."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Restart OAuth without exposing or requesting a token."""
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm", data_schema=vol.Schema({}))

        return await self.async_step_pick_implementation(
            user_input={"implementation": self._get_reauth_entry().data["auth_implementation"]}
        )

    async def async_oauth_create_entry(self, data: dict[str, Any]) -> FlowResult:
        """Store HA's OAuth metadata and token reference in the config entry."""
        if self.source == SOURCE_REAUTH:
            entry = self._get_reauth_entry()
            return self.async_update_reload_and_abort(
                entry,
                data_updates={"token": data["token"]},
            )

        await self.async_set_unique_id("spotify")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title="Playlist Assistant Historical Test Spotify",
            data=data,
        )
