"""Calendar platform for the Sourdough Monitor integration.

Surfaces the feeding history and the next upcoming feeding as a Home Assistant
calendar, so they show up on calendar dashboards and can drive calendar-based
automations.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import homeassistant.util.dt as dt_util
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SourdoughCoordinator
from .sensor import _device_info

_LOGGER = logging.getLogger(__name__)

# Calendar entries are point-in-time events; give them a short visible duration.
EVENT_DURATION = timedelta(minutes=15)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sourdough Monitor calendar."""
    coordinator: SourdoughCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SourdoughCalendar(coordinator, entry)])


class SourdoughCalendar(CoordinatorEntity[SourdoughCoordinator], CalendarEntity):
    """A calendar of past feedings and the next upcoming feeding."""

    _attr_has_entity_name = True
    _attr_name = "Feeding Schedule"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: SourdoughCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_calendar"
        self._attr_device_info = _device_info(entry)

    def _next_feeding_event(self) -> CalendarEvent | None:
        data = self.coordinator.data or {}
        raw = data.get("next_feeding_dt")
        if not raw:
            return None
        start = dt_util.parse_datetime(raw)
        if start is None:
            return None
        overdue = data.get("is_overdue")
        summary = "Feed sourdough starter"
        if overdue:
            summary += " (overdue)"
        return CalendarEvent(
            start=start,
            end=start + EVENT_DURATION,
            summary=summary,
            description="Next scheduled sourdough feeding.",
        )

    @staticmethod
    def _feeding_event(feeding: dict) -> CalendarEvent | None:
        start = dt_util.parse_datetime(feeding.get("timestamp", ""))
        if start is None:
            return None
        flour = feeding.get("flour_g")
        water = feeding.get("water_g")
        discarded = feeding.get("discarded_g", 0.0)
        parts = []
        if flour is not None:
            parts.append(f"{flour:g} g flour")
        if water is not None:
            parts.append(f"{water:g} g water")
        if discarded:
            parts.append(f"{discarded:g} g discarded")
        description = ", ".join(parts) if parts else "Starter fed."
        return CalendarEvent(
            start=start,
            end=start + EVENT_DURATION,
            summary="Starter fed",
            description=description,
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming feeding event."""
        return self._next_feeding_event()

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return past feedings and the next feeding within the given range."""
        events: list[CalendarEvent] = []

        for feeding in self.coordinator.feedings:
            event = self._feeding_event(feeding)
            if event and start_date <= event.start <= end_date:
                events.append(event)

        next_event = self._next_feeding_event()
        if next_event and start_date <= next_event.start <= end_date:
            events.append(next_event)

        events.sort(key=lambda e: e.start)
        return events
