"""Astrolab: scheduler, nightly results, forecast and processing health in Home Assistant."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AstrolabClient, AstrolabError
from .const import CONF_URL
from .coordinator import AstrolabConfigEntry, AstrolabCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: AstrolabConfigEntry) -> bool:
    client = AstrolabClient(async_get_clientsession(hass), entry.data[CONF_URL])
    try:
        await client.health()
    except AstrolabError as err:
        raise ConfigEntryNotReady(f"Astrolab at {client.url} did not answer: {err}") from err
    coordinator = AstrolabCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AstrolabConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
