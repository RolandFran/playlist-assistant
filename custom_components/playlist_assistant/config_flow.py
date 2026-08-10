from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from .const import DOMAIN

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    async def async_step_user(self, user_input=None) -> FlowResult:
        if user_input is not None:
            await self.async_set_unique_id(user_input["url"])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="Playlist Assistant", data=user_input)
        return self.async_show_form(step_id="user", data_schema={"url": str, "bridge_token": str})
