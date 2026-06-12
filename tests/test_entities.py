"""Tests for the binary_sensor, select, switch and calendar entities.

These construct the entities against a real coordinator (with its data set
directly) and exercise their read-side properties. Option-writing paths that
need the entity platform/hass wiring are covered indirectly by the config and
options flow tests.
"""

from datetime import datetime, timedelta, timezone

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sourdough.binary_sensor import (
    SourdoughFeedingDueBinarySensor,
)
from custom_components.sourdough.calendar import SourdoughCalendar
from custom_components.sourdough.const import CONF_NAME, DOMAIN, SENSOR_RISE_TIME
from custom_components.sourdough.coordinator import SourdoughCoordinator
from custom_components.sourdough.select import SourdoughMaintenanceCadenceSelect
from custom_components.sourdough.sensor import (
    SourdoughRiseTimeSensor,
    _device_info,
)
from custom_components.sourdough.switch import SourdoughMaintenanceDiscardSwitch

from .conftest import DEFAULT_CONFIG

_NOW = datetime(2026, 3, 8, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    return


def _coord(hass, *, data=None, stored=None, config=None):
    entry = MockConfigEntry(domain=DOMAIN, data=config or DEFAULT_CONFIG)
    entry.add_to_hass(hass)
    coord = SourdoughCoordinator(hass, entry)
    coord._stored = stored or {"feedings": []}
    coord.data = data or {}
    return coord, entry


async def test_binary_sensor_on_when_due(hass):
    coord, entry = _coord(hass, data={"is_due": True, "is_overdue": False})
    ent = SourdoughFeedingDueBinarySensor(coord, entry)
    assert ent.is_on is True


async def test_binary_sensor_off_when_not_due(hass):
    coord, entry = _coord(hass, data={"is_due": False})
    ent = SourdoughFeedingDueBinarySensor(coord, entry)
    assert ent.is_on is False


async def test_select_reflects_matching_preset(hass):
    coord, entry = _coord(hass, data={"maintenance_interval_hours": 168.0})
    ent = SourdoughMaintenanceCadenceSelect(coord, entry)
    assert ent.current_option == "Weekly — fridge (168h)"
    assert "Weekly — fridge (168h)" in ent.options


async def test_select_shows_custom_when_no_preset_matches(hass):
    coord, entry = _coord(hass, data={"maintenance_interval_hours": 100.0})
    ent = SourdoughMaintenanceCadenceSelect(coord, entry)
    assert ent.current_option == "Custom (100h)"
    assert "Custom (100h)" in ent.options


async def test_switch_reflects_discard_flag(hass):
    coord, entry = _coord(hass, data={"maintenance_discard": False})
    ent = SourdoughMaintenanceDiscardSwitch(coord, entry)
    assert ent.is_on is False


async def test_device_name_uses_configured_name(hass):
    """A configured starter name becomes the device name (for multiple starters)."""
    entry = MockConfigEntry(domain=DOMAIN, data={**DEFAULT_CONFIG, CONF_NAME: "Rye Starter"})
    entry.add_to_hass(hass)
    assert _device_info(entry)["name"] == "Rye Starter"


async def test_device_name_falls_back_when_unnamed(hass):
    """Entries created before naming existed keep the original device name."""
    entry = MockConfigEntry(domain=DOMAIN, data=DEFAULT_CONFIG)
    entry.add_to_hass(hass)
    assert _device_info(entry)["name"] == "Sourdough Monitor"


async def test_log_peak_at_datetime_reads_last_peak(hass):
    """The Log Peak At picker reflects the most recent logged peak."""
    from custom_components.sourdough.datetime import SourdoughLogPeakAtDateTime

    peak_ts = (_NOW - timedelta(hours=2)).isoformat()
    coord, entry = _coord(hass, data={"last_peak_dt": peak_ts})
    ent = SourdoughLogPeakAtDateTime(coord, entry)
    assert ent.native_value == _NOW - timedelta(hours=2)


async def test_log_peak_at_datetime_none_when_no_peak(hass):
    from custom_components.sourdough.datetime import SourdoughLogPeakAtDateTime

    coord, entry = _coord(hass, data={})
    ent = SourdoughLogPeakAtDateTime(coord, entry)
    assert ent.native_value is None


async def test_log_peak_at_datetime_logs_chosen_time(hass):
    """Setting the picker logs a peak at the chosen timestamp."""
    from unittest.mock import AsyncMock

    from custom_components.sourdough.datetime import SourdoughLogPeakAtDateTime

    coord, entry = _coord(hass, data={})
    coord.async_log_peak = AsyncMock()
    ent = SourdoughLogPeakAtDateTime(coord, entry)
    chosen = _NOW - timedelta(hours=3)
    await ent.async_set_value(chosen)
    coord.async_log_peak.assert_awaited_once_with(timestamp=chosen)


async def test_rise_time_sensor_reads_value(hass):
    coord, entry = _coord(hass, data={"last_rise_hours": 5.5, "peak_count": 2})
    ent = SourdoughRiseTimeSensor(
        coord, entry, "metric",
        key=SENSOR_RISE_TIME,
        name="Last Rise Time",
        data_key="last_rise_hours",
        icon="mdi:trending-up",
    )
    assert ent.native_value == 5.5
    assert ent.extra_state_attributes["peak_count"] == 2


async def test_calendar_includes_peak_events(hass):
    peak_ts = (_NOW - timedelta(hours=3)).isoformat()
    stored = {
        "feedings": [],
        "peaks": [{"timestamp": peak_ts, "rise_hours": 6.0}],
    }
    coord, entry = _coord(
        hass,
        data={"next_feeding_dt": (_NOW + timedelta(hours=12)).isoformat(), "is_overdue": False},
        stored=stored,
    )
    cal = SourdoughCalendar(coord, entry)
    events = await cal.async_get_events(
        hass, _NOW - timedelta(days=1), _NOW + timedelta(days=1)
    )
    assert any("peaked" in e.summary.lower() for e in events)


async def test_calendar_event_is_next_feeding(hass):
    next_ts = (_NOW + timedelta(hours=12)).isoformat()
    coord, entry = _coord(hass, data={"next_feeding_dt": next_ts, "is_overdue": False})
    cal = SourdoughCalendar(coord, entry)
    event = cal.event
    assert event is not None
    assert "Feed sourdough starter" in event.summary


async def test_calendar_get_events_includes_past_and_next(hass):
    feeding_ts = (_NOW - timedelta(days=1)).isoformat()
    next_ts = (_NOW + timedelta(hours=12)).isoformat()
    stored = {
        "feedings": [
            {"timestamp": feeding_ts, "flour_g": 60, "water_g": 60, "discarded_g": 0}
        ]
    }
    coord, entry = _coord(
        hass,
        data={"next_feeding_dt": next_ts, "is_overdue": False},
        stored=stored,
    )
    cal = SourdoughCalendar(coord, entry)
    events = await cal.async_get_events(
        hass, _NOW - timedelta(days=2), _NOW + timedelta(days=2)
    )
    summaries = [e.summary for e in events]
    assert "Starter fed" in summaries
    assert any("Feed sourdough starter" in s for s in summaries)
    # Sorted oldest first: the past feeding precedes the upcoming one.
    assert events[0].start < events[-1].start
