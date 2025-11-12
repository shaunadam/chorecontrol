"""The ChoreControl integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .api_client import ChoreControlApiClient
from .const import (
    ATTR_APPROVER_USER_ID,
    ATTR_CHORE_INSTANCE_ID,
    ATTR_POINTS_DELTA,
    ATTR_REASON,
    ATTR_REWARD_ID,
    ATTR_USER_ID,
    CONF_ADDON_URL,
    CONF_SCAN_INTERVAL,
    COORDINATOR,
    DOMAIN,
    PLATFORMS,
    SERVICE_ADJUST_POINTS,
    SERVICE_APPROVE_CHORE,
    SERVICE_CLAIM_CHORE,
    SERVICE_CLAIM_REWARD,
    SERVICE_REFRESH_DATA,
    SERVICE_REJECT_CHORE,
)
from .coordinator import ChoreControlDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Service schemas
SERVICE_CLAIM_CHORE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CHORE_INSTANCE_ID): cv.positive_int,
        vol.Required(ATTR_USER_ID): cv.positive_int,
    }
)

SERVICE_APPROVE_CHORE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CHORE_INSTANCE_ID): cv.positive_int,
        vol.Required(ATTR_APPROVER_USER_ID): cv.positive_int,
    }
)

SERVICE_REJECT_CHORE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CHORE_INSTANCE_ID): cv.positive_int,
        vol.Required(ATTR_APPROVER_USER_ID): cv.positive_int,
        vol.Required(ATTR_REASON): cv.string,
    }
)

SERVICE_ADJUST_POINTS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_USER_ID): cv.positive_int,
        vol.Required(ATTR_POINTS_DELTA): int,
        vol.Required(ATTR_REASON): cv.string,
    }
)

SERVICE_CLAIM_REWARD_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_REWARD_ID): cv.positive_int,
        vol.Required(ATTR_USER_ID): cv.positive_int,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ChoreControl from a config entry."""
    _LOGGER.debug("Setting up ChoreControl integration")

    # Store integration data
    hass.data.setdefault(DOMAIN, {})

    # Create API client
    addon_url = entry.data[CONF_ADDON_URL]
    scan_interval = entry.data.get(CONF_SCAN_INTERVAL)

    api_client = ChoreControlApiClient(hass, addon_url)

    # Create data update coordinator
    coordinator = ChoreControlDataUpdateCoordinator(
        hass,
        api_client,
        scan_interval=scan_interval,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator
    hass.data[DOMAIN][entry.entry_id] = {
        COORDINATOR: coordinator,
    }

    # Forward entry setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await async_setup_services(hass, coordinator)

    _LOGGER.info("ChoreControl integration setup complete")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading ChoreControl integration")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Remove entry data
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_setup_services(
    hass: HomeAssistant,
    coordinator: ChoreControlDataUpdateCoordinator,
) -> None:
    """Set up services for ChoreControl."""

    async def handle_claim_chore(call: ServiceCall) -> None:
        """Handle claim_chore service call."""
        chore_instance_id = call.data[ATTR_CHORE_INSTANCE_ID]
        user_id = call.data[ATTR_USER_ID]

        _LOGGER.debug(
            "Claiming chore instance %s for user %s",
            chore_instance_id,
            user_id,
        )

        await coordinator.api_client.claim_chore(chore_instance_id, user_id)
        await coordinator.async_request_refresh()

    async def handle_approve_chore(call: ServiceCall) -> None:
        """Handle approve_chore service call."""
        chore_instance_id = call.data[ATTR_CHORE_INSTANCE_ID]
        approver_user_id = call.data[ATTR_APPROVER_USER_ID]

        _LOGGER.debug(
            "Approving chore instance %s by user %s",
            chore_instance_id,
            approver_user_id,
        )

        await coordinator.api_client.approve_chore(chore_instance_id, approver_user_id)
        await coordinator.async_request_refresh()

    async def handle_reject_chore(call: ServiceCall) -> None:
        """Handle reject_chore service call."""
        chore_instance_id = call.data[ATTR_CHORE_INSTANCE_ID]
        approver_user_id = call.data[ATTR_APPROVER_USER_ID]
        reason = call.data[ATTR_REASON]

        _LOGGER.debug(
            "Rejecting chore instance %s by user %s: %s",
            chore_instance_id,
            approver_user_id,
            reason,
        )

        await coordinator.api_client.reject_chore(
            chore_instance_id,
            approver_user_id,
            reason,
        )
        await coordinator.async_request_refresh()

    async def handle_adjust_points(call: ServiceCall) -> None:
        """Handle adjust_points service call."""
        user_id = call.data[ATTR_USER_ID]
        points_delta = call.data[ATTR_POINTS_DELTA]
        reason = call.data[ATTR_REASON]

        _LOGGER.debug(
            "Adjusting points for user %s by %s: %s",
            user_id,
            points_delta,
            reason,
        )

        await coordinator.api_client.adjust_points(user_id, points_delta, reason)
        await coordinator.async_request_refresh()

    async def handle_claim_reward(call: ServiceCall) -> None:
        """Handle claim_reward service call."""
        reward_id = call.data[ATTR_REWARD_ID]
        user_id = call.data[ATTR_USER_ID]

        _LOGGER.debug(
            "Claiming reward %s for user %s",
            reward_id,
            user_id,
        )

        await coordinator.api_client.claim_reward(reward_id, user_id)
        await coordinator.async_request_refresh()

    async def handle_refresh_data(call: ServiceCall) -> None:
        """Handle refresh_data service call."""
        _LOGGER.debug("Refreshing ChoreControl data")
        await coordinator.async_request_refresh()

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLAIM_CHORE,
        handle_claim_chore,
        schema=SERVICE_CLAIM_CHORE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_APPROVE_CHORE,
        handle_approve_chore,
        schema=SERVICE_APPROVE_CHORE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REJECT_CHORE,
        handle_reject_chore,
        schema=SERVICE_REJECT_CHORE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_ADJUST_POINTS,
        handle_adjust_points,
        schema=SERVICE_ADJUST_POINTS_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CLAIM_REWARD,
        handle_claim_reward,
        schema=SERVICE_CLAIM_REWARD_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_DATA,
        handle_refresh_data,
    )

    _LOGGER.debug("ChoreControl services registered")
