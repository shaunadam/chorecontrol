"""The ChoreControl integration."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from aiohttp import web
from homeassistant.components.webhook import (
    async_generate_url,
    async_register,
    async_unregister,
)
from homeassistant.helpers import config_validation as cv

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
    EVENT_CHORE_INSTANCE_APPROVED,
    EVENT_CHORE_INSTANCE_CLAIMED,
    EVENT_CHORE_INSTANCE_REJECTED,
    EVENT_REWARD_CLAIM_APPROVED,
    EVENT_REWARD_CLAIM_CLAIMED,
    EVENT_REWARD_CLAIM_REJECTED,
    PLATFORMS,
    SERVICE_ADJUST_POINTS,
    SERVICE_APPROVE_CHORE,
    SERVICE_CLAIM_CHORE,
    SERVICE_CLAIM_REWARD,
    SERVICE_REFRESH_DATA,
    SERVICE_REJECT_CHORE,
    WEBHOOK_ID,
)
from .coordinator import ChoreControlDataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant, ServiceCall

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

    # Register webhook
    async_register(
        hass,
        DOMAIN,
        "ChoreControl Events",
        WEBHOOK_ID,
        handle_webhook,
    )

    # Generate webhook URL for add-on configuration
    webhook_url = async_generate_url(hass, WEBHOOK_ID)
    hass.data[DOMAIN][entry.entry_id]["webhook_url"] = webhook_url

    _LOGGER.info("ChoreControl webhook registered at %s", webhook_url)

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
        # Unregister webhook
        async_unregister(hass, WEBHOOK_ID)
        _LOGGER.debug("ChoreControl webhook unregistered")

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

    async def handle_refresh_data(_call: ServiceCall) -> None:
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


async def handle_webhook(
    hass: HomeAssistant,
    _webhook_id: str,
    request: web.Request,
) -> web.Response | None:
    """Handle incoming webhook from add-on."""
    try:
        data = await request.json()
    except ValueError:
        _LOGGER.error("Invalid JSON in webhook request")
        return web.Response(status=400, text="Invalid JSON")

    event_type = data.get("event")
    event_data = data.get("data", {})
    timestamp = data.get("timestamp")

    _LOGGER.debug(
        "Received webhook event: %s at %s",
        event_type,
        timestamp,
    )

    # Get coordinator (assumes single entry)
    coordinator = None
    for entry_data in hass.data.get(DOMAIN, {}).values():
        if isinstance(entry_data, dict) and COORDINATOR in entry_data:
            coordinator = entry_data[COORDINATOR]
            break

    if coordinator is None:
        _LOGGER.error("No coordinator found for webhook")
        return web.Response(status=500, text="No coordinator found")

    # Process event
    await process_webhook_event(hass, coordinator, event_type, event_data)

    # Trigger data refresh
    await coordinator.async_request_refresh()

    return web.Response(status=200, text="OK")


async def process_webhook_event(
    hass: HomeAssistant,
    coordinator: ChoreControlDataUpdateCoordinator,
    event_type: str,
    event_data: dict[str, Any],
) -> None:
    """Process webhook event and send notifications."""
    # Fire HA event for automations
    hass.bus.async_fire(
        f"{DOMAIN}_{event_type}",
        event_data,
    )

    _LOGGER.debug("Fired HA event: %s_%s", DOMAIN, event_type)

    # Send notifications based on event type
    if event_type == EVENT_CHORE_INSTANCE_CLAIMED:
        # Notify parents that kid claimed a chore
        await notify_parents(
            hass,
            coordinator,
            title="Chore Claimed",
            message=f"{event_data.get('username', 'Someone')} claimed '{event_data.get('chore_name', 'a chore')}'",
        )

    elif event_type == EVENT_CHORE_INSTANCE_APPROVED:
        # Notify kid their chore was approved
        user_id = event_data.get("user_id")
        points_awarded = event_data.get("points_awarded", 0)
        chore_name = event_data.get("chore_name", "a chore")
        if user_id:
            await notify_user(
                hass,
                user_id,
                title="Chore Approved!",
                message=f"'{chore_name}' was approved! +{points_awarded} points",
            )

    elif event_type == EVENT_CHORE_INSTANCE_REJECTED:
        # Notify kid their chore was rejected
        user_id = event_data.get("user_id")
        chore_name = event_data.get("chore_name", "a chore")
        reason = event_data.get("reason", "")
        if user_id:
            await notify_user(
                hass,
                user_id,
                title="Chore Rejected",
                message=f"'{chore_name}' was rejected: {reason}",
            )

    elif event_type == EVENT_REWARD_CLAIM_CLAIMED:
        # Notify parents that kid claimed a reward
        await notify_parents(
            hass,
            coordinator,
            title="Reward Claimed",
            message=f"{event_data.get('username', 'Someone')} claimed '{event_data.get('reward_name', 'a reward')}'",
        )

    elif event_type == EVENT_REWARD_CLAIM_APPROVED:
        # Notify kid their reward was approved
        user_id = event_data.get("user_id")
        reward_name = event_data.get("reward_name", "a reward")
        if user_id:
            await notify_user(
                hass,
                user_id,
                title="Reward Approved!",
                message=f"'{reward_name}' was approved!",
            )

    elif event_type == EVENT_REWARD_CLAIM_REJECTED:
        # Notify kid their reward was rejected
        user_id = event_data.get("user_id")
        reward_name = event_data.get("reward_name", "a reward")
        reason = event_data.get("reason", "")
        if user_id:
            await notify_user(
                hass,
                user_id,
                title="Reward Rejected",
                message=f"'{reward_name}' was rejected: {reason}",
            )


async def notify_parents(
    hass: HomeAssistant,
    _coordinator: ChoreControlDataUpdateCoordinator,
    title: str,
    message: str,
) -> None:
    """Send notification to all parents."""
    # Use persistent_notification for now
    # Future: Map HA users to ChoreControl users for targeted mobile notifications
    # (_coordinator will be used to look up parent users)
    try:
        await hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "title": title,
                "message": message,
                "notification_id": f"{DOMAIN}_{title.lower().replace(' ', '_')}",
            },
        )
        _LOGGER.debug("Sent parent notification: %s", title)
    except Exception as err:
        _LOGGER.error("Failed to send parent notification: %s", err)


async def notify_user(
    hass: HomeAssistant,
    user_id: int,
    title: str,
    message: str,
) -> None:
    """Send notification to specific user."""
    # Use persistent_notification for now
    # Future: Map ChoreControl user_id to HA user for mobile notifications
    try:
        await hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "title": title,
                "message": message,
                "notification_id": f"{DOMAIN}_{user_id}_{title.lower().replace(' ', '_')}",
            },
        )
        _LOGGER.debug("Sent notification to user %s: %s", user_id, title)
    except Exception as err:
        _LOGGER.error("Failed to send notification to user %s: %s", user_id, err)
