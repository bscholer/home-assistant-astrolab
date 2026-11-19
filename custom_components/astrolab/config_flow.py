"""Setup: where is Astrolab?"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AstrolabClient, AstrolabError, normalize_url
from .const import CONF_URL, DOMAIN


class AstrolabConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _ask(self, step: str, user_input: dict[str, Any] | None, default: str = "") -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            url = normalize_url(user_input[CONF_URL])
            try:
                await AstrolabClient(async_get_clientsession(self.hass), url).health()
            except AstrolabError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(url)
                if step == "user":
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(title="Astrolab", data={CONF_URL: url})
                return self.async_update_reload_and_abort(
                    self._get_reconfigure_entry(), unique_id=url, data={CONF_URL: url}
                )
        return self.async_show_form(
            step_id=step,
            data_schema=vol.Schema({vol.Required(CONF_URL, default=default or "http://"): str}),
            errors=errors,
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._ask("user", user_input)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await self._ask("reconfigure", user_input, self._get_reconfigure_entry().data[CONF_URL])
