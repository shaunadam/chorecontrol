"""Sensor platform for ChoreControl."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    COORDINATOR,
    DOMAIN,
    ROLE_KID,
    ROLE_PARENT,
    SENSOR_ACTIVE_CHORES,
    SENSOR_CLAIMED_CHORES,
    SENSOR_COMPLETED_THIS_WEEK,
    SENSOR_COMPLETED_TODAY,
    SENSOR_PENDING_APPROVALS,
    SENSOR_PENDING_CHORES,
    SENSOR_POINTS,
    SENSOR_TOTAL_KIDS,
)
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

    # Per-kid sensors
    if coordinator.data and "users" in coordinator.data:
        for user in coordinator.data["users"]:
            if user.get("role") == ROLE_KID:
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
        if not self.coordinator.data or "parent_dashboard" not in self.coordinator.data:
            return 0
        return self.coordinator.data["parent_dashboard"].get("pending_approvals", 0)


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
        if not self.coordinator.data or "users" not in self.coordinator.data:
            return 0
        return sum(1 for u in self.coordinator.data["users"] if u.get("role") == ROLE_KID)


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
        if not self.coordinator.data or "chores" not in self.coordinator.data:
            return 0
        return sum(1 for c in self.coordinator.data["chores"] if c.get("is_active", False))


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
        if not self.coordinator.data or "users" not in self.coordinator.data:
            return 0
        for user in self.coordinator.data["users"]:
            if user["id"] == self.user_id:
                return user.get("points", 0)
        return 0


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
        # TODO: Implement based on actual data structure
        return 0


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
        # TODO: Implement based on actual data structure
        return 0


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
        # TODO: Implement based on actual data structure
        return 0


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
        # TODO: Implement based on actual data structure
        return 0
