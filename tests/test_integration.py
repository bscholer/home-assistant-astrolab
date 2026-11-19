"""Everything here uses made-up data. No real site, coordinates or scope addresses."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.astrolab.const import CONF_URL, DOMAIN

BASE = "http://astrolab.test:8000"

SCOPE = {
    "configured": True,
    "reachable": True,
    "scheduler": {
        "state": "observing",
        "target": "M 31",
        "reason": "capturing",
        "enabled": True,
        "skipped": [],
        "integrated_s": {"M 31": 7200.0, "M 45": 3600.0},
    },
    "observe": {"state": "idle", "target": None},
}
WEATHER = {"max_cloud_pct": 80, "mean_cloud_pct": 55.5, "precip_mm": 0.2, "snow_cm": 0.0, "warn": False, "reason": None}
MORNING = {
    "night": "2026-01-02",
    "totals": {"shot_s": 7200.0, "kept_s": 5400.0, "scrap_s": 600.0},
    "targets": [
        {
            "name": "NGC 224",
            "common_name": "Andromeda Galaxy",
            "frames": 100,
            "shot_s": 3600.0,
            "kept_s": 3000.0,
            "state": "updated",
        },
        {"name": "NGC 7000", "common_name": None, "frames": 50, "shot_s": 3600.0, "kept_s": 2400.0, "state": "kept"},
    ],
}
TONIGHT = {
    "dusk_utc": "2026-01-02T01:00:00+00:00",
    "dawn_utc": "2026-01-02T13:00:00+00:00",
    "min_alt_deg": 20.0,
    "site_latitude": 1.0,
    "site_longitude": 2.0,
    "entries": [
        {
            "name": "NGC 1976",
            "common_name": "Orion Nebula",
            "score": 0.9,
            "hours_above_min_alt": 6.0,
            "alt_curve_deg": [1, 2],
        },
        {"name": "NGC 224", "common_name": "Andromeda Galaxy", "score": 0.4, "hours_above_min_alt": 0.0},
        {"name": "M 1", "common_name": "Crab", "score": 0.1, "hours_above_min_alt": 2.0},
    ],
}
SYSTEM = {
    "gpu": {"util": 12.0, "temp_c": 41.0},
    "disk": {"used": 500, "total": 1000},
    "jobs": {"queued": 1, "running": 0, "failed_24h": 2},
}


def mock_astrolab(mocker: AiohttpClientMocker, **overrides):
    routes = {
        "/api/health": {"status": "ok"},
        "/api/scope": SCOPE,
        "/api/scope/weather": WEATHER,
        "/api/morning": MORNING,
        "/api/tonight": TONIGHT,
        "/api/system": SYSTEM,
    }
    routes.update(overrides)
    for path, body in routes.items():
        if isinstance(body, int):
            mocker.get(f"{BASE}{path}", status=body, json={"detail": "no"})
        else:
            mocker.get(f"{BASE}{path}", json=body)


async def setup(hass: HomeAssistant, mocker: AiohttpClientMocker, **overrides) -> MockConfigEntry:
    mock_astrolab(mocker, **overrides)
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_URL: BASE}, unique_id=BASE)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def state(hass: HomeAssistant, entity_id: str):
    s = hass.states.get(entity_id)
    assert s is not None, entity_id
    return s


async def test_scheduler_and_night(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    await setup(hass, aioclient_mock)
    assert state(hass, "sensor.astrolab_scheduler").state == "observing"
    assert state(hass, "sensor.astrolab_current_target").state == "M 31"
    assert state(hass, "sensor.astrolab_scheduler_reason").state == "capturing"
    total = state(hass, "sensor.astrolab_total_integration")
    assert total.state == "3.0"
    assert total.attributes["targets"] == {"M 31": 2.0, "M 45": 1.0}
    assert state(hass, "sensor.astrolab_last_night").state == "2026-01-02"
    assert state(hass, "sensor.astrolab_last_night_shot").state == "2.0"
    assert state(hass, "sensor.astrolab_last_night_kept").state == "1.5"
    assert state(hass, "sensor.astrolab_last_night_frames").state == "150"
    names = [t["name"] for t in state(hass, "sensor.astrolab_last_night").attributes["targets"]]
    assert names == ["Andromeda Galaxy", "NGC 7000"]


async def test_tonight_and_forecast(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    await setup(hass, aioclient_mock)
    assert state(hass, "sensor.astrolab_best_target_tonight").state == "Orion Nebula"
    assert state(hass, "sensor.astrolab_targets_visible_tonight").state == "2"
    assert state(hass, "sensor.astrolab_dusk").state.startswith("2026-01-02T01:00")
    assert state(hass, "sensor.astrolab_cloud_cover_peak").state == "80"
    assert state(hass, "binary_sensor.astrolab_weather_warning").state == "off"


async def test_weather_warning_carries_reason(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    warn = {**WEATHER, "warn": True, "reason": "snow forecast (3.0 cm)"}
    await setup(hass, aioclient_mock, **{"/api/scope/weather": warn})
    s = state(hass, "binary_sensor.astrolab_weather_warning")
    assert s.state == "on"
    assert s.attributes["reason"] == "snow forecast (3.0 cm)"


async def test_system(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    await setup(hass, aioclient_mock)
    assert state(hass, "sensor.astrolab_gpu_load").state == "12.0"
    assert state(hass, "sensor.astrolab_cache_disk_used").state == "50.0"
    assert state(hass, "sensor.astrolab_jobs_failed_24_h").state == "2"
    assert state(hass, "binary_sensor.astrolab_processing").state == "on"
    assert state(hass, "binary_sensor.astrolab_telescope_link").state == "on"


async def test_missing_forecast_does_not_break_the_rest(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """No site set: the forecast answers 400. Everything else still works."""
    await setup(hass, aioclient_mock, **{"/api/scope/weather": 400})
    assert state(hass, "sensor.astrolab_scheduler").state == "observing"
    assert state(hass, "sensor.astrolab_cloud_cover_peak").state == "unknown"
    assert state(hass, "binary_sensor.astrolab_weather_warning").state == "unknown"


async def test_no_nights_yet(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    empty = {"night": None, "nights": [], "targets": []}
    await setup(hass, aioclient_mock, **{"/api/morning": empty})
    assert state(hass, "sensor.astrolab_last_night").state == "unknown"
    assert state(hass, "sensor.astrolab_last_night_kept").state == "unknown"


async def test_switch_turns_scheduler_off(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    await setup(hass, aioclient_mock)
    aioclient_mock.put(f"{BASE}/api/scope/auto", json={})
    assert state(hass, "switch.astrolab_auto_scheduler").state == "on"
    await hass.services.async_call("switch", "turn_off", {"entity_id": "switch.astrolab_auto_scheduler"}, blocking=True)
    call = next(c for c in aioclient_mock.mock_calls if c[0] == "PUT")
    assert call[2] == {"enabled": False}  # no `targets`, so the target list is left alone


async def test_unreachable_retries(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(f"{BASE}/api/health", exc=TimeoutError())
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_URL: BASE}, unique_id=BASE)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_config_flow(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(f"{BASE}/api/health", exc=TimeoutError())
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: "astrolab.test:8000/"})
    assert result["errors"] == {"base": "cannot_connect"}
    aioclient_mock.clear_requests()
    mock_astrolab(aioclient_mock)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: "astrolab.test:8000/"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_URL: BASE}


async def test_same_server_twice(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    await setup(hass, aioclient_mock)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: BASE})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
