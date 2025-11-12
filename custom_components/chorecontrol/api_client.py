"""API client for ChoreControl add-on."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    API_CHORES,
    API_DASHBOARD,
    API_HEALTH,
    API_INSTANCES,
    API_POINTS,
    API_REWARDS,
    API_USERS,
)

_LOGGER = logging.getLogger(__name__)


class ChoreControlApiClient:
    """API client for ChoreControl add-on."""

    def __init__(self, hass: HomeAssistant, addon_url: str) -> None:
        """Initialize the API client."""
        self.hass = hass
        self.addon_url = addon_url.rstrip("/")
        self.session = async_get_clientsession(hass)

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a request to the add-on API."""
        url = f"{self.addon_url}{endpoint}"

        try:
            async with self.session.request(
                method,
                url,
                json=data,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error communicating with API: %s", err)
            raise
        except Exception as err:
            _LOGGER.exception("Unexpected error communicating with API")
            raise

    async def health_check(self) -> dict[str, Any]:
        """Check add-on health."""
        return await self._request("GET", API_HEALTH)

    # User endpoints
    async def get_users(self) -> list[dict[str, Any]]:
        """Get all users."""
        return await self._request("GET", API_USERS)

    async def get_user(self, user_id: int) -> dict[str, Any]:
        """Get user by ID."""
        return await self._request("GET", f"{API_USERS}/{user_id}")

    # Chore endpoints
    async def get_chores(self) -> list[dict[str, Any]]:
        """Get all chores."""
        return await self._request("GET", API_CHORES)

    async def get_chore(self, chore_id: int) -> dict[str, Any]:
        """Get chore by ID."""
        return await self._request("GET", f"{API_CHORES}/{chore_id}")

    # Chore instance endpoints
    async def get_instances(
        self,
        status: str | None = None,
        user_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get chore instances with optional filters."""
        params = {}
        if status:
            params["status"] = status
        if user_id:
            params["user_id"] = user_id

        # For now, just get all instances
        # TODO: Add query parameter support
        return await self._request("GET", API_INSTANCES)

    async def claim_chore(
        self,
        instance_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        """Claim a chore instance."""
        return await self._request(
            "POST",
            f"{API_INSTANCES}/{instance_id}/claim",
            data={"user_id": user_id},
        )

    async def approve_chore(
        self,
        instance_id: int,
        approver_user_id: int,
    ) -> dict[str, Any]:
        """Approve a claimed chore."""
        return await self._request(
            "POST",
            f"{API_INSTANCES}/{instance_id}/approve",
            data={"approver_user_id": approver_user_id},
        )

    async def reject_chore(
        self,
        instance_id: int,
        approver_user_id: int,
        reason: str,
    ) -> dict[str, Any]:
        """Reject a claimed chore."""
        return await self._request(
            "POST",
            f"{API_INSTANCES}/{instance_id}/reject",
            data={
                "approver_user_id": approver_user_id,
                "reason": reason,
            },
        )

    # Reward endpoints
    async def get_rewards(self) -> list[dict[str, Any]]:
        """Get all rewards."""
        return await self._request("GET", API_REWARDS)

    async def claim_reward(
        self,
        reward_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        """Claim a reward."""
        return await self._request(
            "POST",
            f"{API_REWARDS}/{reward_id}/claim",
            data={"user_id": user_id},
        )

    # Points endpoints
    async def adjust_points(
        self,
        user_id: int,
        points_delta: int,
        reason: str,
    ) -> dict[str, Any]:
        """Adjust user points."""
        return await self._request(
            "POST",
            f"{API_POINTS}/adjust",
            data={
                "user_id": user_id,
                "points_delta": points_delta,
                "reason": reason,
            },
        )

    async def get_points_history(
        self,
        user_id: int,
    ) -> list[dict[str, Any]]:
        """Get points history for a user."""
        return await self._request("GET", f"{API_POINTS}/history/{user_id}")

    # Dashboard endpoints
    async def get_kid_dashboard(
        self,
        user_id: int,
    ) -> dict[str, Any]:
        """Get dashboard data for a kid."""
        return await self._request("GET", f"{API_DASHBOARD}/kid/{user_id}")

    async def get_parent_dashboard(self) -> dict[str, Any]:
        """Get dashboard data for parents."""
        return await self._request("GET", f"{API_DASHBOARD}/parent")
