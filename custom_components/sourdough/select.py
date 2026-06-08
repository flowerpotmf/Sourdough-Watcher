"""Select platform for the Sourdough Monitor integration.

Provides a quick "Maintenance cadence" preset selector so the feeding interval
can be switched between room-temperature and fridge/weekly routines straight
from a dashboard, without opening the integration's options dialog.
"""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_MAINTENANCE_INTERVAL_HOURS,
    DEFAULT_MAINTENANCE_INTERVAL_HOURS,
    DOMAIN,
    MAINTENANCE_PRESETS,
)
from .coordinator import SourdoughCoordinator
from .sensor import _device_info

_LOGGER = logging.getLogger(__name__)


def _custom_label(hours: float) -> str:
    """Label shown when the configured interval is not one of the presets."""
    return f"Custom ({hours:g}h)"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Sourdough Monitor select entities."""
    coordinator: SourdoughCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SourdoughMaintenanceCadenceSelect(coordinator, entry)])


class SourdoughMaintenanceCadenceSelect(
    CoordinatorEntity[SourdoughCoordinator], SelectEntity
):
    """Pick the Day 8+ maintenance feeding interval from a set of presets.

    Selecting a preset writes the matching interval to the config entry options,
    which the coordinator picks up on the next refresh. If the configured
    interval does not match a preset (e.g. it was set to an arbitrary value in
    the options dialog) a read-only "Custom (Xh)" entry reflects it.
    """

    _attr_has_entity_name = True
    _attr_name = "Maintenance Cadence"
    _attr_icon = "mdi:fridge-outline"

    def __init__(self, coordinator: SourdoughCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_maintenance_cadence"
        self._attr_device_info = _device_info(entry)

    def _current_hours(self) -> float:
        data = self.coordinator.data or {}
        return float(
            data.get(
                "maintenance_interval_hours", DEFAULT_MAINTENANCE_INTERVAL_HOURS
            )
        )

    @property
    def options(self) -> list[str]:
        opts = list(MAINTENANCE_PRESETS)
        hours = self._current_hours()
        if hours not in MAINTENANCE_PRESETS.values():
            opts.append(_custom_label(hours))
        return opts

    @property
    def current_option(self) -> str | None:
        hours = self._current_hours()
        for label, preset_hours in MAINTENANCE_PRESETS.items():
            if preset_hours == hours:
                return label
        return _custom_label(hours)

    async def async_select_option(self, option: str) -> None:
        hours = MAINTENANCE_PRESETS.get(option)
        if hours is None:
            # The "Custom (Xh)" entry carries no preset value; ignore it.
            return
        new_options = {
            **(self._entry.options or {}),
            CONF_MAINTENANCE_INTERVAL_HOURS: hours,
        }
        self.hass.config_entries.async_update_entry(
            self._entry, options=new_options
        )
