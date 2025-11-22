"""Button platform for ChoreControl."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.button import ButtonEntity
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
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
    """Set up ChoreControl button platform."""
    coordinator: ChoreControlDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        COORDINATOR
    ]

    # Track current buttons by unique_id
    current_buttons: dict[str, ChoreControlClaimButton] = {}

    def _create_button_for_user(
        instance: dict[str, Any],
        user_id: int,
        username: str,
        needed_ids: set[str],
        new_buttons: list[ChoreControlClaimButton],
    ) -> None:
        """Create a button for a specific user and instance."""
        unique_id = f"{DOMAIN}_claim_{instance['instance_id']}_{user_id}"
        needed_ids.add(unique_id)

        if unique_id not in current_buttons:
            button = ChoreControlClaimButton(
                coordinator, instance, user_id, username
            )
            current_buttons[unique_id] = button
            new_buttons.append(button)
            _LOGGER.debug(
                "Creating button: %s for %s",
                instance["chore_name"],
                username,
            )

    def _process_instance(
        instance: dict[str, Any],
        kids: list[dict[str, Any]],
        needed_ids: set[str],
        new_buttons: list[ChoreControlClaimButton],
    ) -> None:
        """Process a single claimable instance to create buttons."""
        if instance["assignment_type"] == "shared":
            # Shared chore: one button per kid who can claim
            for kid in kids:
                _create_button_for_user(
                    instance, kid["id"], kid["username"], needed_ids, new_buttons
                )
        else:
            # Individual chore: one button for assigned user
            user_id = instance.get("assigned_to")
            if not user_id:
                return
            user = coordinator.get_user_by_id(user_id)
            if user:
                _create_button_for_user(
                    instance, user_id, user["username"], needed_ids, new_buttons
                )

    @callback
    def async_update_buttons() -> None:
        """Update button entities based on claimable instances."""
        if not coordinator.data:
            return

        claimable = coordinator.data.get("claimable_instances", [])
        kids = coordinator.data.get("kids", [])

        # Build set of needed button unique_ids
        needed_ids: set[str] = set()
        new_buttons: list[ChoreControlClaimButton] = []

        for instance in claimable:
            _process_instance(instance, kids, needed_ids, new_buttons)

        # Remove buttons no longer needed
        entity_registry = er.async_get(hass)
        for unique_id in list(current_buttons.keys()):
            if unique_id not in needed_ids:
                current_buttons.pop(unique_id)
                # Remove from entity registry
                entity_id = entity_registry.async_get_entity_id(
                    "button", DOMAIN, unique_id
                )
                if entity_id:
                    entity_registry.async_remove(entity_id)
                    _LOGGER.debug("Removed button %s", entity_id)

        # Add new buttons
        if new_buttons:
            async_add_entities(new_buttons)
            _LOGGER.debug("Added %d new claim buttons", len(new_buttons))

    # Initial button creation
    async_update_buttons()

    # Listen for coordinator updates to add/remove buttons
    entry.async_on_unload(coordinator.async_add_listener(async_update_buttons))


class ChoreControlClaimButton(CoordinatorEntity, ButtonEntity):
    """Button to claim a chore instance."""

    def __init__(
        self,
        coordinator: ChoreControlDataUpdateCoordinator,
        instance: dict[str, Any],
        user_id: int,
        username: str,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self.instance_id = instance["instance_id"]
        self.chore_name = instance["chore_name"]
        self.user_id = user_id
        self.username = username
        self.points = instance.get("points", 0)

        self._attr_unique_id = f"{DOMAIN}_claim_{self.instance_id}_{user_id}"
        self._attr_name = f"Claim {self.chore_name} ({username})"
        self._attr_icon = "mdi:checkbox-marked-circle-outline"
        self._attr_has_entity_name = True

    async def async_press(self) -> None:
        """Handle button press - claim the chore."""
        _LOGGER.debug(
            "Claiming chore instance %s for user %s (%s)",
            self.instance_id,
            self.user_id,
            self.username,
        )
        await self.coordinator.api_client.claim_chore(self.instance_id, self.user_id)
        await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {
            "instance_id": self.instance_id,
            "chore_name": self.chore_name,
            "user_id": self.user_id,
            "username": self.username,
            "points": self.points,
        }

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, f"kid_{self.user_id}")},
            "name": self.username,
            "manufacturer": "ChoreControl",
            "model": "Kid",
            "via_device": (DOMAIN, "chorecontrol"),
        }
