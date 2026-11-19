"""Binary sensors."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AstrolabConfigEntry
from .entity import AstrolabEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: AstrolabConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    c = entry.runtime_data
    async_add_entities([WeatherWarning(c), PipelineBusy(c), ScopeLinked(c)])


class WeatherWarning(AstrolabEntity, BinarySensorEntity):
    """Snow or real rain is coming. This is the same check that tells you to bring the scope in."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "weather_warning")

    @property
    def is_on(self) -> bool | None:
        weather = self.section("weather")
        return None if weather is None else bool(weather.get("warn"))

    @property
    def extra_state_attributes(self) -> dict | None:
        weather = self.section("weather")
        return {"reason": weather.get("reason")} if weather else None


class PipelineBusy(AstrolabEntity, BinarySensorEntity):
    """Processing jobs are queued or running."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "pipeline_busy")

    @property
    def is_on(self) -> bool | None:
        jobs = (self.section("system") or {}).get("jobs")
        return None if jobs is None else bool(jobs.get("queued") or jobs.get("running"))


class ScopeLinked(AstrolabEntity, BinarySensorEntity):
    """Astrolab can reach the telescope (its relay)."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "scope_linked")

    @property
    def is_on(self) -> bool | None:
        scope = self.section("scope") or {}
        return bool(scope.get("reachable")) if scope.get("configured") else None
