"""Datetime platform for the Sourdough Monitor integration.

Provides a date/time picker for logging a peak at a specific moment, for when
you notice the starter has peaked but didn't catch it exactly — pick the time
it actually peaked rather than only being able to log "now" via the button.
"""

from __future__ import annotations

import logging
from datetime import datetime

import homeassistant.util.dt as dt_util
from homeassistant.components.datetime import DateTimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SourdoughCoordinator
from .sensor import _device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sourdough Monitor datetime entities."""
    coordinator: SourdoughCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        SourdoughLogPeakAtDateTime(coordinator, entry),
        SourdoughRecordFeedingAtDateTime(coordinator, entry),
    ])


class SourdoughLogPeakAtDateTime(
    CoordinatorEntity[SourdoughCoordinator], DateTimeEntity
):
    """Log a peak at a chosen time.

    Reads back the most recent logged peak, and setting a new value records a
    peak at that timestamp (the rise time since the last feeding is calculated
    automatically). Use this when you didn't catch the peak exactly — for the
    "it just peaked now" case, the **Log Peak** button is quicker.
    """

    _attr_has_entity_name = True
    _attr_name = "Log Peak At"
    _attr_icon = "mdi:clock-edit-outline"

    def __init__(self, coordinator: SourdoughCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_log_peak_at"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> datetime | None:
        raw = (self.coordinator.data or {}).get("last_peak_dt")
        if raw:
            return dt_util.parse_datetime(raw)
        return None

    async def async_set_value(self, value: datetime) -> None:
        await self.coordinator.async_log_peak(timestamp=value)


class SourdoughRecordFeedingAtDateTime(
    CoordinatorEntity[SourdoughCoordinator], DateTimeEntity
):
    """Record a feeding at a chosen time.

    Like the **Record Feeding** button (configured amounts, with discard applied
    when the current phase calls for it), but lets you set the time the feeding
    actually happened — useful for catching up after forgetting to log one.
    """

    _attr_has_entity_name = True
    _attr_name = "Record Feeding At"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: SourdoughCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_record_feeding_at"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> datetime | None:
        raw = (self.coordinator.data or {}).get("last_feeding_dt")
        if raw:
            return dt_util.parse_datetime(raw)
        return None

    async def async_set_value(self, value: datetime) -> None:
        data = self.coordinator.data or {}
        discarded_g = data.get("discard_amount_g", 0.0) if data.get("should_discard") else 0.0
        await self.coordinator.async_record_feeding(
            discarded_g=discarded_g, timestamp=value
        )
