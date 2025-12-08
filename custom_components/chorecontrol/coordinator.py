"""DataUpdateCoordinator for ChoreControl."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api_client import ChoreControlApiClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, ROLE_KID

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
            # Check API health
            api_connected = await self.api_client.check_health()

            if not api_connected:
                _LOGGER.warning("ChoreControl API is not available")
                return {
                    "users": [],
                    "kids": [],
                    "chores": [],
                    "instances": [],
                    "rewards": [],
                    "api_connected": False,
                    "pending_approvals_count": 0,
                    "instances_by_user": {},
                    "claimable_instances": [],
                }

            # Fetch all necessary data
            users = await self.api_client.get_users()
            chores = await self.api_client.get_chores(active_only=True)
            instances = await self.api_client.get_instances()
            rewards = await self.api_client.get_rewards(active_only=True)
            pending_reward_claims = await self.api_client.get_reward_claims(
                status="pending"
            )

            # Extract kids from users
            kids = [u for u in users if u.get("role") == ROLE_KID]

            # Build chore lookup by ID for easy access
            chore_by_id = {c["id"]: c for c in chores}

            # Calculate pending approvals (instances with status 'claimed')
            pending_approvals_count = sum(
                1 for inst in instances if inst.get("status") == "claimed"
            )

            # Calculate pending reward approvals
            pending_reward_approvals_count = len(pending_reward_claims)

            # Build pending_reward_claims_by_user
            pending_reward_claims_by_user: dict[int, list[dict]] = {}
            for claim in pending_reward_claims:
                user_id = claim.get("user_id")
                if user_id:
                    if user_id not in pending_reward_claims_by_user:
                        pending_reward_claims_by_user[user_id] = []
                    pending_reward_claims_by_user[user_id].append(claim)

            # Build instances_by_user structure
            instances_by_user = self._build_instances_by_user(instances, kids)

            # Build claimable_instances list
            claimable_instances = self._build_claimable_instances(
                instances, chore_by_id
            )

            # Organize data for easy access by entities
            return {
                "users": users,
                "kids": kids,
                "chores": chores,
                "instances": instances,
                "rewards": rewards,
                "api_connected": True,
                "pending_approvals_count": pending_approvals_count,
                "pending_reward_approvals_count": pending_reward_approvals_count,
                "pending_reward_claims": pending_reward_claims,
                "pending_reward_claims_by_user": pending_reward_claims_by_user,
                "instances_by_user": instances_by_user,
                "claimable_instances": claimable_instances,
            }

        except Exception as err:
            _LOGGER.error("Error fetching data from ChoreControl add-on: %s", err)
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    def _build_instances_by_user(  # noqa: PLR0912
        self,
        instances: list[dict[str, Any]],
        kids: list[dict[str, Any]],
    ) -> dict[int, dict[str, list[dict[str, Any]]]]:
        """Build instances organized by user ID."""
        result: dict[int, dict[str, list[dict[str, Any]]]] = {}

        today = datetime.now().date()
        # Calculate start of current week (Monday)
        week_start = today - timedelta(days=today.weekday())

        for kid in kids:
            user_id = kid["id"]
            result[user_id] = {
                "assigned": [],
                "claimed": [],
                "approved_today": [],
                "approved_this_week": [],
                "due_today": [],
            }

        for inst in instances:
            status = inst.get("status", "")
            assigned_to = inst.get("assigned_to")
            claimed_by = inst.get("claimed_by")

            # Determine which user this instance belongs to
            user_id = claimed_by or assigned_to
            if not user_id or user_id not in result:
                continue

            if status == "assigned" and assigned_to == user_id:
                result[user_id]["assigned"].append(inst)
                # Track due_today: includes chores due today OR "anytime" chores (null due_date)
                due_date_str = inst.get("due_date")
                if due_date_str is None:
                    # "Anytime" chore - always due today
                    result[user_id]["due_today"].append(inst)
                else:
                    try:
                        if "T" in due_date_str:
                            due_date = datetime.fromisoformat(
                                due_date_str.replace("Z", "+00:00")
                            ).date()
                        else:
                            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                        if due_date == today:
                            result[user_id]["due_today"].append(inst)
                    except (ValueError, TypeError):
                        pass
            elif status == "claimed" and claimed_by == user_id:
                result[user_id]["claimed"].append(inst)
            elif status == "approved":
                # Check if approved today or this week
                approved_at_str = inst.get("approved_at")
                if approved_at_str:
                    try:
                        # Parse the timestamp
                        if "T" in approved_at_str:
                            approved_at = datetime.fromisoformat(
                                approved_at_str.replace("Z", "+00:00")
                            ).date()
                        else:
                            approved_at = datetime.strptime(
                                approved_at_str, "%Y-%m-%d"
                            ).date()

                        # Check if the approving user matches
                        if claimed_by == user_id:
                            if approved_at == today:
                                result[user_id]["approved_today"].append(inst)
                            if approved_at >= week_start:
                                result[user_id]["approved_this_week"].append(inst)
                    except (ValueError, TypeError) as e:
                        _LOGGER.debug("Could not parse approved_at: %s", e)

        return result

    def _build_claimable_instances(
        self,
        instances: list[dict[str, Any]],
        chore_by_id: dict[int, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build list of claimable instances."""
        claimable = []

        for inst in instances:
            if inst.get("status") != "assigned":
                continue

            chore_id = inst.get("chore_id")
            chore = chore_by_id.get(chore_id, {})

            # Get chore info, either from nested object or lookup
            chore_data = inst.get("chore", chore)
            chore_name = chore_data.get("name", "Unknown Chore")
            points = chore_data.get("points", 0)
            assignment_type = chore_data.get("assignment_type", "individual")

            claimable.append({
                "instance_id": inst["id"],
                "chore_name": chore_name,
                "chore_id": chore_id,
                "due_date": inst.get("due_date"),
                "points": points,
                "assigned_to": inst.get("assigned_to"),
                "assignment_type": assignment_type,
            })

        return claimable

    def get_user_by_id(self, user_id: int) -> dict[str, Any] | None:
        """Get user data by ID."""
        if not self.data or "users" not in self.data:
            return None
        for user in self.data["users"]:
            if user["id"] == user_id:
                return user
        return None

    def get_kid_stats(self, user_id: int) -> dict[str, Any]:
        """Get computed stats for a kid."""
        default_stats = {
            "points": 0,
            "pending_count": 0,
            "claimed_count": 0,
            "completed_today": 0,
            "completed_this_week": 0,
            "chores_due_today": 0,
            "pending_reward_claims": 0,
        }

        if not self.data:
            return default_stats

        # Get points from user data
        user = self.get_user_by_id(user_id)
        points = user.get("points", 0) if user else 0

        # Get instance counts
        instances_by_user = self.data.get("instances_by_user", {})
        user_instances = instances_by_user.get(user_id, {})

        # Get pending reward claims for this user
        pending_reward_claims_by_user = self.data.get("pending_reward_claims_by_user", {})
        user_pending_claims = pending_reward_claims_by_user.get(user_id, [])

        return {
            "points": points,
            "pending_count": len(user_instances.get("assigned", [])),
            "claimed_count": len(user_instances.get("claimed", [])),
            "completed_today": len(user_instances.get("approved_today", [])),
            "chores_due_today": len(user_instances.get("due_today", [])),
            "pending_reward_claims": len(user_pending_claims),
            "completed_this_week": len(user_instances.get("approved_this_week", [])),
        }

    def get_claimable_for_user(self, user_id: int) -> list[dict[str, Any]]:
        """Get claimable instances for a specific user."""
        if not self.data:
            return []

        claimable = self.data.get("claimable_instances", [])
        result = []

        for inst in claimable:
            # Individual chores: only for assigned user
            # Shared chores: for any kid
            if inst["assignment_type"] == "shared" or inst.get("assigned_to") == user_id:
                result.append(inst)

        return result
