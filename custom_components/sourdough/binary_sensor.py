"""Binary sensor platform for the Sourdough Monitor integration.

Exposes a single "Feeding Due" binary sensor so automations and dashboards can
react to a feeding being due without templating the coordinator attributes.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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
    """Set up the Sourdough Monitor binary sensors."""
    coordinator: SourdoughCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SourdoughFeedingDueBinarySensor(coordinator, entry)])


class SourdoughFeedingDueBinarySensor(
    CoordinatorEntity[SourdoughCoordinator], BinarySensorEntity
):
    """On when the starter is due (or overdue) for a feeding."""

    _attr_has_entity_name = True
    _attr_name = "Feeding Due"
    _attr_icon = "mdi:bell-ring-outline"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: SourdoughCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_feeding_due"
        self._attr_device_info = _device_info(entry)

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if not data:
            return None
        return bool(data.get("is_due"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return {
            "is_overdue": data.get("is_overdue"),
            "overdue_minutes": data.get("overdue_minutes"),
            "next_feeding_dt": data.get("next_feeding_dt"),
            "interval_hours": data.get("interval_hours"),
        }
