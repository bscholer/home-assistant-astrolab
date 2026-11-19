"""One coordinator for everything Astrolab tells us."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AstrolabClient, AstrolabError
from .const import DOMAIN, MORNING_TTL_S, SCAN_INTERVAL_S, SYSTEM_TTL_S, TONIGHT_TTL_S, WEATHER_TTL_S

_LOGGER = logging.getLogger(__name__)

type AstrolabConfigEntry = ConfigEntry[AstrolabCoordinator]


def summarize_tonight(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep only what the sensors need. The full list holds hundreds of objects with sky curves."""
    entries = payload.get("entries") or []
    best = max(entries, key=lambda e: e.get("score") or 0, default=None)
    return {
        "dusk": payload.get("dusk_utc"),
        "dawn": payload.get("dawn_utc"),
        "min_alt_deg": payload.get("min_alt_deg"),
        "visible": sum(1 for e in entries if (e.get("hours_above_min_alt") or 0) > 0),
        "best": best
        and {
            k: best.get(k)
            for k in (
                "name",
                "common_name",
                "constellation",
                "object_type",
                "score",
                "hours_above_min_alt",
                "alt_now_deg",
                "az_now_deg",
                "transit_utc",
                "session_count",
            )
        },
    }


class AstrolabCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    config_entry: AstrolabConfigEntry

    def __init__(self, hass: HomeAssistant, entry: AstrolabConfigEntry, client: AstrolabClient) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN, config_entry=entry, update_interval=timedelta(seconds=SCAN_INTERVAL_S)
        )
        self.client = client
        # name -> (fetched at, value). A slow source that fails keeps its last value.
        self._slow: dict[str, tuple[float, Any]] = {}

    async def _slow_source(
        self, name: str, ttl: float, fetch: Callable[[], Awaitable[Any]], shape: Callable[[Any], Any] = lambda x: x
    ) -> Any:
        fetched_at, value = self._slow.get(name, (0.0, None))
        if fetched_at and time.monotonic() - fetched_at < ttl:
            return value
        try:
            value = shape(await fetch())
        except AstrolabError as err:
            # The forecast needs a site and an outside service; any of the slow ones can be missing.
            _LOGGER.debug("Astrolab %s unavailable: %s", name, err)
        self._slow[name] = (time.monotonic(), value)
        return value

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            scope = await self.client.scope()
        except AstrolabError as err:
            raise UpdateFailed(f"Astrolab did not answer: {err}") from err
        return {
            "scope": scope,
            "weather": await self._slow_source("weather", WEATHER_TTL_S, self.client.weather),
            "morning": await self._slow_source("morning", MORNING_TTL_S, self.client.morning),
            "tonight": await self._slow_source("tonight", TONIGHT_TTL_S, self.client.tonight, summarize_tonight),
            "system": await self._slow_source("system", SYSTEM_TTL_S, self.client.system),
        }
