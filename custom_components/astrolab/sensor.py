"""Sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import AstrolabConfigEntry, AstrolabCoordinator
from .entity import AstrolabEntity

PARALLEL_UPDATES = 0


def _hours(seconds: float | None) -> float | None:
    return None if seconds is None else round(seconds / 3600, 2)


def _scheduler(data: dict) -> dict:
    return (data.get("scope") or {}).get("scheduler") or {}


def _totals(data: dict) -> dict | None:
    return (data.get("morning") or {}).get("totals")


def _night_has_data(data: dict) -> bool:
    return bool((data.get("morning") or {}).get("night"))


def _morning_total(key: str) -> Callable[[dict], float | None]:
    def value(data: dict) -> float | None:
        totals = _totals(data)
        return _hours(totals.get(key)) if totals and _night_has_data(data) else None

    return value


def _night(data: dict) -> date | None:
    night = (data.get("morning") or {}).get("night")
    return date.fromisoformat(night) if night else None


def _morning_frames(data: dict) -> int | None:
    targets = (data.get("morning") or {}).get("targets")
    return sum(t.get("frames") or 0 for t in targets) if targets else None


def _timestamp(section: str, key: str) -> Callable[[dict], datetime | None]:
    def value(data: dict) -> datetime | None:
        raw = (data.get(section) or {}).get(key)
        return dt_util.parse_datetime(raw) if raw else None

    return value


def _best(data: dict) -> dict:
    return (data.get("tonight") or {}).get("best") or {}


def _section(section: str, *path: str) -> Callable[[dict], Any]:
    def value(data: dict) -> Any:
        node: Any = data.get(section)
        for key in path:
            if not isinstance(node, dict):
                return None
            node = node.get(key)
        return node

    return value


def _cache_disk_percent(data: dict) -> float | None:
    disk = (data.get("system") or {}).get("disk") or {}
    if not disk.get("total"):
        return None
    return round(100 * disk["used"] / disk["total"], 1)


def _night_attrs(data: dict) -> dict:
    targets = (data.get("morning") or {}).get("targets") or []
    return {
        "targets": [
            {
                "name": t.get("common_name") or t.get("name"),
                "catalog_name": t.get("name"),
                "frames": t.get("frames"),
                "shot_hours": _hours(t.get("shot_s")),
                "kept_hours": _hours(t.get("kept_s")),
                "state": t.get("state"),
            }
            for t in targets
        ]
    }


def _integration_attrs(data: dict) -> dict:
    integrated = _scheduler(data).get("integrated_s") or {}
    return {"targets": {name: _hours(s) for name, s in sorted(integrated.items())}}


@dataclass(frozen=True, kw_only=True)
class AstrolabSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict], Any]
    attrs_fn: Callable[[dict], dict] | None = None


SENSORS: tuple[AstrolabSensorDescription, ...] = (
    # The all-night scheduler.
    AstrolabSensorDescription(key="scheduler_state", value_fn=lambda d: _scheduler(d).get("state")),
    AstrolabSensorDescription(
        key="scheduler_target",
        value_fn=lambda d: _scheduler(d).get("target") or _section("scope", "observe", "target")(d),
    ),
    AstrolabSensorDescription(key="scheduler_reason", value_fn=lambda d: _scheduler(d).get("reason")),
    AstrolabSensorDescription(
        key="integration_total",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=lambda d: (
            _hours(sum((_scheduler(d).get("integrated_s") or {}).values()))
            if _scheduler(d).get("integrated_s") is not None
            else None
        ),
        attrs_fn=_integration_attrs,
    ),
    # What happened last night.
    AstrolabSensorDescription(
        key="last_night", device_class=SensorDeviceClass.DATE, value_fn=_night, attrs_fn=_night_attrs
    ),
    AstrolabSensorDescription(
        key="last_night_shot",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=1,
        value_fn=_morning_total("shot_s"),
    ),
    AstrolabSensorDescription(
        key="last_night_kept",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=1,
        value_fn=_morning_total("kept_s"),
    ),
    AstrolabSensorDescription(
        key="last_night_scrapped",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=1,
        value_fn=_morning_total("scrap_s"),
    ),
    AstrolabSensorDescription(key="last_night_frames", native_unit_of_measurement="frames", value_fn=_morning_frames),
    # Tonight.
    AstrolabSensorDescription(
        key="dusk", device_class=SensorDeviceClass.TIMESTAMP, value_fn=_timestamp("tonight", "dusk")
    ),
    AstrolabSensorDescription(
        key="dawn", device_class=SensorDeviceClass.TIMESTAMP, value_fn=_timestamp("tonight", "dawn")
    ),
    AstrolabSensorDescription(
        key="best_target",
        value_fn=lambda d: _best(d).get("common_name") or _best(d).get("name"),
        attrs_fn=_best,
    ),
    AstrolabSensorDescription(key="targets_visible", value_fn=_section("tonight", "visible")),
    # Forecast for the night.
    AstrolabSensorDescription(
        key="cloud_max",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_section("weather", "max_cloud_pct"),
    ),
    AstrolabSensorDescription(
        key="cloud_mean",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_section("weather", "mean_cloud_pct"),
    ),
    AstrolabSensorDescription(
        key="precipitation",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement="mm",
        value_fn=_section("weather", "precip_mm"),
    ),
    AstrolabSensorDescription(
        key="snowfall",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement="cm",
        value_fn=_section("weather", "snow_cm"),
    ),
    # The computer doing the processing.
    AstrolabSensorDescription(
        key="gpu_load",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_section("system", "gpu", "util"),
    ),
    AstrolabSensorDescription(
        key="gpu_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_section("system", "gpu", "temp_c"),
    ),
    AstrolabSensorDescription(
        key="cache_disk_used",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_cache_disk_percent,
    ),
    AstrolabSensorDescription(key="jobs_queued", value_fn=_section("system", "jobs", "queued")),
    AstrolabSensorDescription(key="jobs_running", value_fn=_section("system", "jobs", "running")),
    AstrolabSensorDescription(key="jobs_failed_24h", value_fn=_section("system", "jobs", "failed_24h")),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: AstrolabConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities(AstrolabSensor(entry.runtime_data, d) for d in SENSORS)


class AstrolabSensor(AstrolabEntity, SensorEntity):
    entity_description: AstrolabSensorDescription

    def __init__(self, coordinator: AstrolabCoordinator, description: AstrolabSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data or {})

    @property
    def extra_state_attributes(self) -> dict | None:
        fn = self.entity_description.attrs_fn
        return fn(self.coordinator.data or {}) if fn else None
