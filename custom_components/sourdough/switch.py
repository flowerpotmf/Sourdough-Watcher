"""Switch platform for the Sourdough Monitor integration.

Exposes a toggle for whether the starter is discarded before each maintenance
(Day 8+) feeding. Fridge-stored, weekly routines that keep a small amount of
starter rather than discarding can turn this off straight from a dashboard.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_MAINTENANCE_DISCARD,
    DEFAULT_MAINTENANCE_DISCARD,
    DOMAIN,
)
from .coordinator import SourdoughCoordinator
from .sensor import _device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sourdough Monitor switch entities."""
    coordinator: SourdoughCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SourdoughMaintenanceDiscardSwitch(coordinator, entry)])


class SourdoughMaintenanceDiscardSwitch(
    CoordinatorEntity[SourdoughCoordinator], SwitchEntity
):
    """Toggle discarding during the maintenance phase.

    Writes the choice to the config entry options so it persists and is picked
    up by the coordinator on the next refresh.
    """

    _attr_has_entity_name = True
    _attr_name = "Discard During Maintenance"
    _attr_icon = "mdi:delete-sweep-outline"

    def __init__(self, coordinator: SourdoughCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_maintenance_discard"
        self._attr_device_info = _device_info(entry)

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if not data:
            return None
        return bool(data.get("maintenance_discard", DEFAULT_MAINTENANCE_DISCARD))

    async def _async_set(self, value: bool) -> None:
        new_options = {
            **(self._entry.options or {}),
            CONF_MAINTENANCE_DISCARD: value,
        }
        self.hass.config_entries.async_update_entry(
            self._entry, options=new_options
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set(False)
