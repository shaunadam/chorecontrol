"""Sensor platform for ChoreControl."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    COORDINATOR,
    DOMAIN,
)

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
    """Set up ChoreControl sensor platform."""
    coordinator: ChoreControlDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        COORDINATOR
    ]

    entities: list[SensorEntity] = []

    # Global sensors
    entities.append(ChoreControlPendingApprovalsSensor(coordinator))
    entities.append(ChoreControlTotalKidsSensor(coordinator))
    entities.append(ChoreControlActiveChoresSensor(coordinator))

    # Track which kids we've created sensors for
    known_kid_ids: set[int] = set()

    # Per-kid sensors
    if coordinator.data and "kids" in coordinator.data:
        for user in coordinator.data["kids"]:
            user_id = user["id"]
            known_kid_ids.add(user_id)
            entities.extend(
                [
                    ChoreControlPointsSensor(coordinator, user),
                    ChoreControlPendingChoresSensor(coordinator, user),
                    ChoreControlClaimedChoresSensor(coordinator, user),
                    ChoreControlCompletedTodaySensor(coordinator, user),
                    ChoreControlCompletedThisWeekSensor(coordinator, user),
                ]
            )

    async_add_entities(entities)

    @callback
    def async_add_new_kid_sensors() -> None:
        """Add sensors for newly discovered kids."""
        if not coordinator.data or "kids" not in coordinator.data:
            return

        new_entities: list[SensorEntity] = []

        for user in coordinator.data["kids"]:
            user_id = user["id"]
            if user_id not in known_kid_ids:
                _LOGGER.debug("Adding sensors for new kid: %s", user["username"])
                known_kid_ids.add(user_id)
                new_entities.extend(
                    [
                        ChoreControlPointsSensor(coordinator, user),
                        ChoreControlPendingChoresSensor(coordinator, user),
                        ChoreControlClaimedChoresSensor(coordinator, user),
                        ChoreControlCompletedTodaySensor(coordinator, user),
                        ChoreControlCompletedThisWeekSensor(coordinator, user),
                    ]
                )

        if new_entities:
            async_add_entities(new_entities)

    # Listen for coordinator updates to add sensors for new kids
    entry.async_on_unload(
        coordinator.async_add_listener(async_add_new_kid_sensors)
    )


class ChoreControlSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for ChoreControl sensors."""

    def __init__(
        self,
        coordinator: ChoreControlDataUpdateCoordinator,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_has_entity_name = True


# Global sensors


class ChoreControlPendingApprovalsSensor(ChoreControlSensorBase):
    """Sensor for pending approvals count."""

    def __init__(self, coordinator: ChoreControlDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_pending_approvals"
        self._attr_name = "Pending approvals"
        self._attr_icon = "mdi:clipboard-check-outline"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the number of pending approvals."""
        if not self.coordinator.data:
            return 0
        return self.coordinator.data.get("pending_approvals_count", 0)

    @property
    def device_info(self) -> dict:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, "chorecontrol")},
            "name": "ChoreControl",
            "manufacturer": "ChoreControl",
            "model": "Chore Management System",
        }


class ChoreControlTotalKidsSensor(ChoreControlSensorBase):
    """Sensor for total kids count."""

    def __init__(self, coordinator: ChoreControlDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_total_kids"
        self._attr_name = "Total kids"
        self._attr_icon = "mdi:account-group"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the number of kids."""
        if not self.coordinator.data:
            return 0
        return len(self.coordinator.data.get("kids", []))

    @property
    def device_info(self) -> dict:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, "chorecontrol")},
            "name": "ChoreControl",
            "manufacturer": "ChoreControl",
            "model": "Chore Management System",
        }


class ChoreControlActiveChoresSensor(ChoreControlSensorBase):
    """Sensor for active chores count."""

    def __init__(self, coordinator: ChoreControlDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_active_chores"
        self._attr_name = "Active chores"
        self._attr_icon = "mdi:format-list-checks"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the number of active chores."""
        if not self.coordinator.data:
            return 0
        return len(self.coordinator.data.get("chores", []))

    @property
    def device_info(self) -> dict:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, "chorecontrol")},
            "name": "ChoreControl",
            "manufacturer": "ChoreControl",
            "model": "Chore Management System",
        }


# Per-kid sensors


class ChoreControlKidSensorBase(ChoreControlSensorBase):
    """Base class for per-kid sensors."""

    def __init__(
        self,
        coordinator: ChoreControlDataUpdateCoordinator,
        user: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.user_id = user["id"]
        self.username = user["username"]


class ChoreControlPointsSensor(ChoreControlKidSensorBase):
    """Sensor for kid's points balance."""

    def __init__(
        self,
        coordinator: ChoreControlDataUpdateCoordinator,
        user: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, user)
        self._attr_unique_id = f"{DOMAIN}_{self.username}_points"
        self._attr_name = f"{self.username} points"
        self._attr_icon = "mdi:star"
        self._attr_state_class = SensorStateClass.TOTAL

    @property
    def native_value(self) -> int:
        """Return the kid's points balance."""
        stats = self.coordinator.get_kid_stats(self.user_id)
        return stats["points"]

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        return {
            "user_id": self.user_id,
            "username": self.username,
        }

    @property
    def device_info(self) -> dict:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, f"kid_{self.user_id}")},
            "name": self.username,
            "manufacturer": "ChoreControl",
            "model": "Kid",
            "via_device": (DOMAIN, "chorecontrol"),
        }


class ChoreControlPendingChoresSensor(ChoreControlKidSensorBase):
    """Sensor for kid's pending chores count."""

    def __init__(
        self,
        coordinator: ChoreControlDataUpdateCoordinator,
        user: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, user)
        self._attr_unique_id = f"{DOMAIN}_{self.username}_pending_chores"
        self._attr_name = f"{self.username} pending chores"
        self._attr_icon = "mdi:clipboard-list-outline"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the number of pending chores."""
        stats = self.coordinator.get_kid_stats(self.user_id)
        return stats["pending_count"]

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        return {
            "user_id": self.user_id,
            "username": self.username,
        }

    @property
    def device_info(self) -> dict:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, f"kid_{self.user_id}")},
            "name": self.username,
            "manufacturer": "ChoreControl",
            "model": "Kid",
            "via_device": (DOMAIN, "chorecontrol"),
        }


class ChoreControlClaimedChoresSensor(ChoreControlKidSensorBase):
    """Sensor for kid's claimed chores count."""

    def __init__(
        self,
        coordinator: ChoreControlDataUpdateCoordinator,
        user: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, user)
        self._attr_unique_id = f"{DOMAIN}_{self.username}_claimed_chores"
        self._attr_name = f"{self.username} claimed chores"
        self._attr_icon = "mdi:hand-okay"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the number of claimed chores."""
        stats = self.coordinator.get_kid_stats(self.user_id)
        return stats["claimed_count"]

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        return {
            "user_id": self.user_id,
            "username": self.username,
        }

    @property
    def device_info(self) -> dict:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, f"kid_{self.user_id}")},
            "name": self.username,
            "manufacturer": "ChoreControl",
            "model": "Kid",
            "via_device": (DOMAIN, "chorecontrol"),
        }


class ChoreControlCompletedTodaySensor(ChoreControlKidSensorBase):
    """Sensor for kid's completed chores today."""

    def __init__(
        self,
        coordinator: ChoreControlDataUpdateCoordinator,
        user: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, user)
        self._attr_unique_id = f"{DOMAIN}_{self.username}_completed_today"
        self._attr_name = f"{self.username} completed today"
        self._attr_icon = "mdi:check-circle"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the number of chores completed today."""
        stats = self.coordinator.get_kid_stats(self.user_id)
        return stats["completed_today"]

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        return {
            "user_id": self.user_id,
            "username": self.username,
        }

    @property
    def device_info(self) -> dict:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, f"kid_{self.user_id}")},
            "name": self.username,
            "manufacturer": "ChoreControl",
            "model": "Kid",
            "via_device": (DOMAIN, "chorecontrol"),
        }


class ChoreControlCompletedThisWeekSensor(ChoreControlKidSensorBase):
    """Sensor for kid's completed chores this week."""

    def __init__(
        self,
        coordinator: ChoreControlDataUpdateCoordinator,
        user: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, user)
        self._attr_unique_id = f"{DOMAIN}_{self.username}_completed_this_week"
        self._attr_name = f"{self.username} completed this week"
        self._attr_icon = "mdi:calendar-check"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int:
        """Return the number of chores completed this week."""
        stats = self.coordinator.get_kid_stats(self.user_id)
        return stats["completed_this_week"]

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        return {
            "user_id": self.user_id,
            "username": self.username,
        }

    @property
    def device_info(self) -> dict:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, f"kid_{self.user_id}")},
            "name": self.username,
            "manufacturer": "ChoreControl",
            "model": "Kid",
            "via_device": (DOMAIN, "chorecontrol"),
        }
