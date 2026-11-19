"""The all-night scheduler switch."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import AstrolabError
from .coordinator import AstrolabConfigEntry
from .entity import AstrolabEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant, entry: AstrolabConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([AutoScheduler(entry.runtime_data)])


class AutoScheduler(AstrolabEntity, SwitchEntity):
    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "auto_scheduler")

    @property
    def is_on(self) -> bool | None:
        scheduler = (self.section("scope") or {}).get("scheduler")
        return None if scheduler is None else bool(scheduler.get("enabled"))

    async def _set(self, enabled: bool) -> None:
        try:
            await self.coordinator.client.set_auto(enabled)
        except AstrolabError as err:
            raise HomeAssistantError(f"Astrolab did not accept that: {err}") from err
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)
