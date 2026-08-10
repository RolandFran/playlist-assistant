"""Configuration of the authenticated, internal add-on bridge."""
from __future__ import annotations
import voluptuous as vol
from aiohttp import ClientError
from homeassistant import config_entries
from homeassistant.const import CONF_URL
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .bridge import AddonBridge
from .const import DOMAIN

CONF_BRIDGE_TOKEN = "bridge_token"
STEP_USER_SCHEMA = vol.Schema({
    vol.Required(CONF_URL, default="http://playlist_assistant:8098"): vol.All(str, vol.Url()),
    vol.Required(CONF_BRIDGE_TOKEN): vol.All(str, vol.Length(min=16)),
})

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            try:
                bridge = AddonBridge(async_get_clientsession(self.hass), user_input[CONF_URL], user_input[CONF_BRIDGE_TOKEN])
                await bridge.state()
            except (ClientError, TimeoutError, ValueError):
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(user_input[CONF_URL])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Playlist Assistant", data=user_input)
        return self.async_show_form(step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors)
