"""Tests for coordinator logic: phase detection, weight estimation, day calculation.

Weight estimation tests call the module-level pure function directly — no HA
infrastructure needed. _compute_state tests use the hass fixture (which sets
up the Frame helper) with dt_util.now patched to a fixed datetime.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import homeassistant.util.dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sourdough.const import (
    CONF_MAINTENANCE_DISCARD,
    CONF_MAINTENANCE_INTERVAL_HOURS,
    CONF_VESSEL_TARE,
    DOMAIN,
)
from custom_components.sourdough.coordinator import (
    SourdoughCoordinator,
    _build_instructions,
    _get_phase_for_day,
    _humanize_interval,
    _phase_label,
    estimate_starter_weight,
    rise_hours_for_peak,
)

from .conftest import DEFAULT_CONFIG

# Fixed "now" used across all tests that need a stable clock
_NOW = datetime(2026, 3, 8, 12, 0, 0, tzinfo=timezone.utc)
_DT_NOW = "custom_components.sourdough.coordinator.dt_util.now"


def _ts(dt: datetime) -> str:
    return dt.isoformat()


# ---------------------------------------------------------------------------
# Pure function tests — no HA required
# ---------------------------------------------------------------------------

class TestPhaseForDay:
    @pytest.mark.parametrize("day,expected_hours,expected_discard", [
        (1, 24, False),
        (2, 24, False),
        (3, 24, True),
        (4, 24, True),
        (5, 24, True),
        (6, 12, True),
        (7, 12, True),
        (8, 12, True),
        (20, 12, True),
    ])
    def test_phase_schedule(self, day, expected_hours, expected_discard):
        hours, discard = _get_phase_for_day(day)
        assert hours == expected_hours
        assert discard == expected_discard

    @pytest.mark.parametrize("day", [8, 12, 30])
    def test_maintenance_interval_is_configurable(self, day):
        """Day 8+ uses the supplied maintenance interval, not a fixed 12h."""
        hours, discard = _get_phase_for_day(day, maintenance_interval_hours=168)
        assert hours == 168
        assert discard is True

    @pytest.mark.parametrize("day", [1, 5, 7])
    def test_establishment_days_ignore_maintenance_interval(self, day):
        """Days 1-7 keep their fixed recipe interval regardless of the override."""
        hours, _ = _get_phase_for_day(day, maintenance_interval_hours=168)
        assert hours != 168

    def test_maintenance_discard_toggle(self):
        """Maintenance discard follows the maintenance_discard argument."""
        _, discard_off = _get_phase_for_day(10, 168, maintenance_discard=False)
        _, discard_on = _get_phase_for_day(10, 168, maintenance_discard=True)
        assert discard_off is False
        assert discard_on is True


class TestHumanizeInterval:
    @pytest.mark.parametrize("hours,expected", [
        (12, "every 12 hours"),
        (1, "every hour"),
        (24, "every day"),
        (48, "every 2 days"),
        (168, "every week"),
        (336, "every 2 weeks"),
    ])
    def test_phrasing(self, hours, expected):
        assert _humanize_interval(hours) == expected


class TestPhaseLabel:
    @pytest.mark.parametrize("day,expected", [
        (1, "Initialization"),
        (2, "Initialization"),
        (3, "Establishment"),
        (5, "Establishment"),
        (6, "Activation"),
        (7, "Activation"),
        (8, "Maintenance"),
        (30, "Maintenance"),
    ])
    def test_labels(self, day, expected):
        assert _phase_label(day) == expected


class TestBuildInstructions:
    def test_day1_no_urgency(self):
        result = _build_instructions(1, False, 24, False, 0)
        assert "flour" in result.lower()
        assert "overdue" not in result.lower()

    def test_overdue_message_included(self):
        result = _build_instructions(3, True, 24, True, 90)
        assert "overdue" in result.lower()
        assert "1h 30m" in result

    def test_day3_mentions_discard(self):
        result = _build_instructions(3, True, 24, False, 0)
        assert "discard" in result.lower()

    def test_maintenance_mentions_active(self):
        result = _build_instructions(10, True, 12, False, 0)
        assert "active" in result.lower()

    def test_maintenance_reflects_custom_interval(self):
        """A weekly maintenance interval should read as 'every week'."""
        result = _build_instructions(10, True, 168, False, 0)
        assert "every week" in result.lower()
        assert "12 hours" not in result

    def test_maintenance_without_discard_does_not_say_discard_half(self):
        """With maintenance discard off, instructions must not tell you to discard half."""
        result = _build_instructions(10, False, 168, False, 0)
        assert "discarding half" not in result.lower()
        assert "no discard" in result.lower()
        assert "active" in result.lower()


class TestRiseHoursForPeak:
    def test_none_when_no_prior_feeding(self):
        assert rise_hours_for_peak([], _NOW) is None

    def test_hours_since_last_feeding(self):
        feedings = [{"timestamp": _ts(_NOW - timedelta(hours=5))}]
        assert rise_hours_for_peak(feedings, _NOW) == pytest.approx(5.0)

    def test_uses_most_recent_feeding_before_peak(self):
        feedings = [
            {"timestamp": _ts(_NOW - timedelta(hours=30))},
            {"timestamp": _ts(_NOW - timedelta(hours=6))},
        ]
        assert rise_hours_for_peak(feedings, _NOW) == pytest.approx(6.0)

    def test_ignores_feedings_after_the_peak(self):
        peak = _NOW - timedelta(hours=2)
        feedings = [
            {"timestamp": _ts(_NOW - timedelta(hours=8))},  # 6h before the peak
            {"timestamp": _ts(_NOW)},  # after the peak — must be ignored
        ]
        assert rise_hours_for_peak(feedings, peak) == pytest.approx(6.0)


class TestEstimateStarterWeight:
    """Tests for the module-level estimate_starter_weight pure function."""

    def test_no_feedings_no_baseline_returns_zero(self):
        assert estimate_starter_weight([], 60, 60) == 0.0

    def test_single_feeding_accumulates(self):
        feedings = [{"timestamp": _ts(_NOW), "flour_g": 60, "water_g": 60, "discarded_g": 0}]
        assert estimate_starter_weight(feedings, 60, 60) == pytest.approx(120.0)

    def test_discard_reduces_weight(self):
        feedings = [
            {"timestamp": _ts(_NOW), "flour_g": 60, "water_g": 60, "discarded_g": 0},
            {"timestamp": _ts(_NOW + timedelta(hours=24)), "flour_g": 60, "water_g": 60, "discarded_g": 60},
        ]
        # After feeding 1: 120g. Feeding 2: discard 60 → 60g, add 120 → 180g
        assert estimate_starter_weight(feedings, 60, 60) == pytest.approx(180.0)

    def test_weight_cannot_go_negative(self):
        feedings = [{"timestamp": _ts(_NOW), "flour_g": 10, "water_g": 10, "discarded_g": 9999}]
        assert estimate_starter_weight(feedings, 60, 60) >= 0.0

    def test_baseline_used_as_starting_weight(self):
        baseline = {"timestamp": _ts(_NOW - timedelta(hours=1)), "weight_g": 200.0}
        feedings = [{"timestamp": _ts(_NOW), "flour_g": 60, "water_g": 60, "discarded_g": 0}]
        # baseline 200 + 60 flour + 60 water = 320
        assert estimate_starter_weight(feedings, 60, 60, baseline) == pytest.approx(320.0)

    def test_feedings_before_baseline_are_ignored(self):
        baseline = {"timestamp": _ts(_NOW), "weight_g": 200.0}
        old_feeding = {"timestamp": _ts(_NOW - timedelta(hours=2)), "flour_g": 60, "water_g": 60, "discarded_g": 0}
        assert estimate_starter_weight([old_feeding], 60, 60, baseline) == pytest.approx(200.0)


# ---------------------------------------------------------------------------
# _compute_state tests — require hass fixture for the Frame helper
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    return


def _make_coord(hass, config=None, stored=None):
    """Create a coordinator with real hass but mocked Store."""
    entry = MockConfigEntry(domain=DOMAIN, data=config or DEFAULT_CONFIG)
    entry.add_to_hass(hass)
    coord = SourdoughCoordinator(hass, entry)
    coord._stored = stored or {"start_datetime": _ts(_NOW), "feedings": []}
    return coord


class TestComputeState:
    async def test_day1_on_fresh_start(self, hass):
        coord = _make_coord(hass)
        with patch(_DT_NOW, return_value=_NOW):
            state = coord._compute_state()
        assert state["current_day"] == 1
        assert state["phase"] == "Initialization"
        assert state["should_discard"] is False
        assert state["starter_weight_g"] == 0.0

    async def test_day3_requires_discard(self, hass):
        stored = {"start_datetime": _ts(_NOW - timedelta(days=2, hours=1)), "feedings": []}
        coord = _make_coord(hass, stored=stored)
        with patch(_DT_NOW, return_value=_NOW):
            state = coord._compute_state()
        assert state["current_day"] == 3
        assert state["should_discard"] is True
        assert state["phase"] == "Establishment"

    async def test_total_weight_includes_vessel_tare(self, hass):
        stored = {
            "start_datetime": _ts(_NOW),
            "feedings": [
                {"timestamp": _ts(_NOW), "flour_g": 60, "water_g": 60, "discarded_g": 0}
            ],
        }
        config = {**DEFAULT_CONFIG, CONF_VESSEL_TARE: 200.0}
        coord = _make_coord(hass, config=config, stored=stored)
        with patch(_DT_NOW, return_value=_NOW):
            state = coord._compute_state()
        assert state["total_weight_g"] == pytest.approx(320.0)
        assert state["starter_weight_g"] == pytest.approx(120.0)

    async def test_no_discard_on_days_1_and_2(self, hass):
        for days_ago in [0, 1]:
            stored = {"start_datetime": _ts(_NOW - timedelta(days=days_ago)), "feedings": []}
            coord = _make_coord(hass, stored=stored)
            with patch(_DT_NOW, return_value=_NOW):
                state = coord._compute_state()
            assert state["discard_amount_g"] == 0.0

    async def test_is_overdue_when_past_next_feeding(self, hass):
        # Started 25h ago (day 1, 24h interval), no feedings → overdue
        stored = {"start_datetime": _ts(_NOW - timedelta(hours=25)), "feedings": []}
        coord = _make_coord(hass, stored=stored)
        with patch(_DT_NOW, return_value=_NOW):
            state = coord._compute_state()
        assert state["is_overdue"] is True
        assert state["overdue_minutes"] > 0

    async def test_hydration_calculation(self, hass):
        coord = _make_coord(hass)
        with patch(_DT_NOW, return_value=_NOW):
            state = coord._compute_state()
        # Default config: 60g flour, 60g water → 100%
        assert state["hydration_pct"] == pytest.approx(100.0)

    async def test_maintenance_uses_configured_interval(self, hass):
        """On Day 8+, next feeding honours the configured maintenance interval."""
        last_fed = _NOW - timedelta(hours=24)
        stored = {
            "start_datetime": _ts(_NOW - timedelta(days=9)),
            "feedings": [
                {"timestamp": _ts(last_fed), "flour_g": 60, "water_g": 60, "discarded_g": 0}
            ],
        }
        config = {**DEFAULT_CONFIG, CONF_MAINTENANCE_INTERVAL_HOURS: 168.0}
        coord = _make_coord(hass, config=config, stored=stored)
        with patch(_DT_NOW, return_value=_NOW):
            state = coord._compute_state()
        assert state["current_day"] == 10
        assert state["interval_hours"] == 168.0
        # Last fed 24h ago + 168h interval → not yet due
        expected_next = last_fed + timedelta(hours=168)
        assert state["next_feeding_dt"] == expected_next.isoformat()
        assert state["is_overdue"] is False

    async def test_maintenance_discard_can_be_disabled(self, hass):
        """With maintenance discard off, no discard is required on Day 8+."""
        stored = {
            "start_datetime": _ts(_NOW - timedelta(days=9)),
            "feedings": [
                {"timestamp": _ts(_NOW), "flour_g": 60, "water_g": 60, "discarded_g": 0}
            ],
        }
        config = {**DEFAULT_CONFIG, CONF_MAINTENANCE_DISCARD: False}
        coord = _make_coord(hass, config=config, stored=stored)
        with patch(_DT_NOW, return_value=_NOW):
            state = coord._compute_state()
        assert state["current_day"] == 10
        assert state["phase"] == "Maintenance"
        assert state["should_discard"] is False
        assert state["discard_amount_g"] == 0.0

    async def test_starter_metadata_defaults_in_state(self, hass):
        """Starter type and flour type fall back to sensible defaults."""
        coord = _make_coord(hass)
        with patch(_DT_NOW, return_value=_NOW):
            state = coord._compute_state()
        assert state["starter_type"] == "liquid"
        assert state["flour_type"] == "wheat"

    async def test_log_peak_records_rise_time(self, hass):
        """Logging a peak stores its rise time (hours since the last feeding)."""
        last_fed = _NOW - timedelta(hours=6)
        stored = {
            "start_datetime": _ts(_NOW - timedelta(days=9)),
            "feedings": [
                {"timestamp": _ts(last_fed), "flour_g": 60, "water_g": 60, "discarded_g": 0}
            ],
        }
        coord = _make_coord(hass, stored=stored)
        coord._store.async_save = AsyncMock()
        with patch(_DT_NOW, return_value=_NOW):
            await coord.async_log_peak()
            state = coord._compute_state()
        assert state["peak_count"] == 1
        assert state["last_rise_hours"] == pytest.approx(6.0)
        assert state["average_rise_hours"] == pytest.approx(6.0)
        assert state["last_peak_dt"] == _NOW.isoformat()
        assert coord._store.async_save.await_count == 1

    async def test_log_peak_backdated_timestamp(self, hass):
        """A peak can be logged with a past timestamp (logged after the fact)."""
        last_fed = _NOW - timedelta(hours=10)
        peak_time = _NOW - timedelta(hours=2)
        stored = {
            "start_datetime": _ts(_NOW - timedelta(days=9)),
            "feedings": [
                {"timestamp": _ts(last_fed), "flour_g": 60, "water_g": 60, "discarded_g": 0}
            ],
        }
        coord = _make_coord(hass, stored=stored)
        coord._store.async_save = AsyncMock()
        with patch(_DT_NOW, return_value=_NOW):
            await coord.async_log_peak(timestamp=peak_time)
            state = coord._compute_state()
        # Peak 2h ago, fed 10h ago → 8h rise time.
        assert state["last_rise_hours"] == pytest.approx(8.0)
        assert state["last_peak_dt"] == peak_time.isoformat()

    async def test_estimated_peak_from_average_rise(self, hass):
        """Estimated peak = last feeding + average rise time."""
        last_fed = _NOW - timedelta(hours=3)
        stored = {
            "start_datetime": _ts(_NOW - timedelta(days=9)),
            "feedings": [
                {"timestamp": _ts(last_fed), "flour_g": 60, "water_g": 60, "discarded_g": 0}
            ],
            "peaks": [
                {"timestamp": _ts(_NOW - timedelta(days=1)), "rise_hours": 6.0}
            ],
        }
        coord = _make_coord(hass, stored=stored)
        with patch(_DT_NOW, return_value=_NOW):
            state = coord._compute_state()
        assert state["average_rise_hours"] == pytest.approx(6.0)
        assert state["estimated_peak_dt"] == (last_fed + timedelta(hours=6)).isoformat()
        # Fed 3h ago + 6h rise → 3h in the future, so not due and not yet peaked.
        assert state["peak_due"] is False
        assert state["has_peaked_this_cycle"] is False

    async def test_peak_due_when_estimate_passed(self, hass):
        """Peak Due turns on once the estimated peak time is reached."""
        last_fed = _NOW - timedelta(hours=8)
        stored = {
            "start_datetime": _ts(_NOW - timedelta(days=9)),
            "feedings": [
                {"timestamp": _ts(last_fed), "flour_g": 60, "water_g": 60, "discarded_g": 0}
            ],
            "peaks": [
                {"timestamp": _ts(_NOW - timedelta(days=2)), "rise_hours": 6.0}
            ],
        }
        coord = _make_coord(hass, stored=stored)
        with patch(_DT_NOW, return_value=_NOW):
            state = coord._compute_state()
        # Fed 8h ago + 6h rise = 2h ago → due, and no peak logged this cycle.
        assert state["peak_due"] is True

    async def test_rolling_average_uses_recent_peaks(self, hass):
        """Average rise time uses the last ROLLING_PEAKS_WINDOW (5) peaks only."""
        rises = [10.0, 10.0, 10.0, 2.0, 2.0, 2.0]  # 6 peaks; last 5 = 10,10,2,2,2
        peaks = [
            {"timestamp": _ts(_NOW - timedelta(days=6 - i)), "rise_hours": r}
            for i, r in enumerate(rises)
        ]
        stored = {"start_datetime": _ts(_NOW - timedelta(days=9)), "feedings": [], "peaks": peaks}
        coord = _make_coord(hass, stored=stored)
        with patch(_DT_NOW, return_value=_NOW):
            state = coord._compute_state()
        assert state["average_rise_hours"] == pytest.approx(5.2)   # (10+10+2+2+2)/5
        assert state["all_time_average_rise_hours"] == pytest.approx(6.0)  # 36/6

    async def test_history_export_summary(self, hass):
        stored = {
            "start_datetime": _ts(_NOW),
            "feedings": [
                {"timestamp": _ts(_NOW), "flour_g": 60, "water_g": 60, "discarded_g": 0},
                {"timestamp": _ts(_NOW + timedelta(hours=24)), "flour_g": 60, "water_g": 60, "discarded_g": 50},
            ],
            "peaks": [{"timestamp": _ts(_NOW), "rise_hours": 6.0}],
        }
        coord = _make_coord(hass, stored=stored)
        exp = coord.history_export()
        assert exp["summary"]["total_feedings"] == 2
        assert exp["summary"]["total_flour_g"] == pytest.approx(120.0)
        assert exp["summary"]["total_discarded_g"] == pytest.approx(50.0)
        assert exp["summary"]["peak_count"] == 1
        assert exp["summary"]["average_rise_hours"] == pytest.approx(6.0)
        assert len(exp["feedings"]) == 2

    async def test_skip_feeding_pushes_next_due_by_one_interval(self, hass):
        """Skipping advances the next-feeding time by one interval, no feeding logged."""
        last_fed = _NOW - timedelta(hours=1)
        stored = {
            "start_datetime": _ts(_NOW - timedelta(days=9)),
            "feedings": [
                {"timestamp": _ts(last_fed), "flour_g": 60, "water_g": 60, "discarded_g": 0}
            ],
        }
        config = {**DEFAULT_CONFIG, CONF_MAINTENANCE_INTERVAL_HOURS: 12.0}
        coord = _make_coord(hass, config=config, stored=stored)
        coord._store.async_save = AsyncMock()
        with patch(_DT_NOW, return_value=_NOW):
            before = coord._compute_state()
            await coord.async_skip_feeding()
            after = coord._compute_state()

        before_due = dt_util.parse_datetime(before["next_feeding_dt"])
        after_due = dt_util.parse_datetime(after["next_feeding_dt"])
        assert after_due - before_due == timedelta(hours=12)
        # No feeding was logged by skipping.
        assert after["feeding_count"] == before["feeding_count"]
        assert coord._store.async_save.await_count == 1
