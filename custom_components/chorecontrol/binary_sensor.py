"""Binary sensor platform for ChoreControl."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COORDINATOR, DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import ChoreControlDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ChoreControl binary sensor platform."""
    coordinator: ChoreControlDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        COORDINATOR
    ]

    _LOGGER.debug("Setting up ChoreControl binary sensor platform")
    async_add_entities([ChoreControlApiConnectedSensor(coordinator)])


class ChoreControlApiConnectedSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for API connection status."""

    def __init__(self, coordinator: ChoreControlDataUpdateCoordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_api_connected"
        self._attr_name = "API connected"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_has_entity_name = True

    @property
    def is_on(self) -> bool:
        """Return True if API is connected."""
        if not self.coordinator.data:
            return False
        return self.coordinator.data.get("api_connected", False)

    @property
    def device_info(self) -> dict:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, "chorecontrol")},
            "name": "ChoreControl",
            "manufacturer": "ChoreControl",
            "model": "Chore Management System",
        }
