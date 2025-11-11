"""DataUpdateCoordinator for ChoreControl."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api_client import ChoreControlApiClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class ChoreControlDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching ChoreControl data from the add-on."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_client: ChoreControlApiClient,
        scan_interval: int | None = None,
    ) -> None:
        """Initialize the coordinator."""
        self.api_client = api_client

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=scan_interval or DEFAULT_SCAN_INTERVAL
            ),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the add-on API."""
        try:
            # Fetch all necessary data
            users = await self.api_client.get_users()
            chores = await self.api_client.get_chores()
            instances = await self.api_client.get_instances()
            rewards = await self.api_client.get_rewards()
            parent_dashboard = await self.api_client.get_parent_dashboard()

            # Organize data for easy access by entities
            return {
                "users": users,
                "chores": chores,
                "instances": instances,
                "rewards": rewards,
                "parent_dashboard": parent_dashboard,
            }

        except Exception as err:
            _LOGGER.error("Error fetching data from ChoreControl add-on: %s", err)
            raise UpdateFailed(f"Error communicating with API: {err}") from err
