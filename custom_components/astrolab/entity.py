"""Base entity."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AstrolabCoordinator


class AstrolabEntity(CoordinatorEntity[AstrolabCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: AstrolabCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Astrolab",
            manufacturer="Astrolab",
            configuration_url=coordinator.client.url,
        )

    def section(self, name: str) -> dict | None:
        return (self.coordinator.data or {}).get(name)
