"""Button platform for ChoreControl."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COORDINATOR, DOMAIN
from .coordinator import ChoreControlDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ChoreControl button platform."""
    coordinator: ChoreControlDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        COORDINATOR
    ]

    entities: list[ButtonEntity] = []

    # TODO: Create claim buttons for chore/kid combinations
    # This will be implemented when we have the actual chore instance data
    # For now, just set up the platform without entities

    async_add_entities(entities)


class ChoreControlButtonBase(CoordinatorEntity, ButtonEntity):
    """Base class for ChoreControl buttons."""

    def __init__(
        self,
        coordinator: ChoreControlDataUpdateCoordinator,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_has_entity_name = True


class ChoreControlClaimButton(ChoreControlButtonBase):
    """Button to claim a chore."""

    def __init__(
        self,
        coordinator: ChoreControlDataUpdateCoordinator,
        chore_instance: dict[str, Any],
        user: dict[str, Any],
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self.chore_instance_id = chore_instance["id"]
        self.user_id = user["id"]
        self.username = user["username"]
        chore_name = chore_instance.get("chore_name", "chore")

        self._attr_unique_id = (
            f"{DOMAIN}_claim_{self.chore_instance_id}_{self.user_id}"
        )
        self._attr_name = f"Claim {chore_name} - {self.username}"
        self._attr_icon = "mdi:hand-okay"

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.api_client.claim_chore(
            self.chore_instance_id,
            self.user_id,
        )
        await self.coordinator.async_request_refresh()
