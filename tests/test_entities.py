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
from custom_components.sourdough.const import DOMAIN
from custom_components.sourdough.coordinator import SourdoughCoordinator
from custom_components.sourdough.select import SourdoughMaintenanceCadenceSelect
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
