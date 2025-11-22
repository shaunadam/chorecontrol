"""Fixtures for ChoreControl tests."""
from __future__ import annotations

import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

# Mock homeassistant.components.webhook before any imports
# to avoid circular import issues
mock_webhook = MagicMock()
mock_webhook.async_generate_url = MagicMock(
    return_value="http://localhost:8123/api/webhook/chorecontrol_events"
)
mock_webhook.async_register = MagicMock()
mock_webhook.async_unregister = MagicMock()
sys.modules["homeassistant.components.webhook"] = mock_webhook


@pytest.fixture
def mock_api_client():
    """Return a mocked API client."""
    client = AsyncMock()

    # Default responses
    client.check_health.return_value = True
    client.get_users.return_value = [
        {"id": 1, "username": "parent1", "role": "parent", "points": 0},
        {"id": 2, "username": "emma", "role": "kid", "points": 45},
        {"id": 3, "username": "jack", "role": "kid", "points": 30},
    ]
    client.get_chores.return_value = [
        {"id": 1, "name": "Take out trash", "points": 5, "is_active": True, "assignment_type": "individual"},
        {"id": 2, "name": "Make bed", "points": 3, "is_active": True, "assignment_type": "individual"},
        {"id": 3, "name": "Feed dog", "points": 4, "is_active": True, "assignment_type": "shared"},
    ]

    today = datetime.now().strftime("%Y-%m-%d")
    client.get_instances.return_value = [
        {
            "id": 1,
            "chore_id": 1,
            "status": "assigned",
            "assigned_to": 2,
            "claimed_by": None,
            "due_date": today,
            "chore": {"name": "Take out trash", "points": 5, "assignment_type": "individual"},
        },
        {
            "id": 2,
            "chore_id": 2,
            "status": "claimed",
            "assigned_to": 2,
            "claimed_by": 2,
            "due_date": today,
            "chore": {"name": "Make bed", "points": 3, "assignment_type": "individual"},
        },
        {
            "id": 3,
            "chore_id": 3,
            "status": "assigned",
            "assigned_to": None,
            "claimed_by": None,
            "due_date": today,
            "chore": {"name": "Feed dog", "points": 4, "assignment_type": "shared"},
        },
        {
            "id": 4,
            "chore_id": 1,
            "status": "approved",
            "assigned_to": 2,
            "claimed_by": 2,
            "due_date": today,
            "approved_at": f"{today}T10:00:00Z",
            "chore": {"name": "Take out trash", "points": 5, "assignment_type": "individual"},
        },
    ]
    client.get_rewards.return_value = [
        {"id": 1, "name": "Ice cream", "points_cost": 20, "is_active": True},
        {"id": 2, "name": "Movie night", "points_cost": 50, "is_active": True},
    ]

    return client


@pytest.fixture
def mock_coordinator(mock_api_client):
    """Return a mocked coordinator with test data."""
    coordinator = MagicMock()
    coordinator.api_client = mock_api_client

    # Pre-computed data that coordinator would produce
    coordinator.data = {
        "users": mock_api_client.get_users.return_value,
        "kids": [u for u in mock_api_client.get_users.return_value if u["role"] == "kid"],
        "chores": mock_api_client.get_chores.return_value,
        "instances": mock_api_client.get_instances.return_value,
        "rewards": mock_api_client.get_rewards.return_value,
        "api_connected": True,
        "pending_approvals_count": 1,  # One claimed instance
        "instances_by_user": {
            2: {
                "assigned": [mock_api_client.get_instances.return_value[0]],
                "claimed": [mock_api_client.get_instances.return_value[1]],
                "approved_today": [mock_api_client.get_instances.return_value[3]],
                "approved_this_week": [mock_api_client.get_instances.return_value[3]],
            },
            3: {
                "assigned": [],
                "claimed": [],
                "approved_today": [],
                "approved_this_week": [],
            },
        },
        "claimable_instances": [
            {
                "instance_id": 1,
                "chore_name": "Take out trash",
                "chore_id": 1,
                "due_date": datetime.now().strftime("%Y-%m-%d"),
                "points": 5,
                "assigned_to": 2,
                "assignment_type": "individual",
            },
            {
                "instance_id": 3,
                "chore_name": "Feed dog",
                "chore_id": 3,
                "due_date": datetime.now().strftime("%Y-%m-%d"),
                "points": 4,
                "assigned_to": None,
                "assignment_type": "shared",
            },
        ],
    }

    def get_kid_stats(user_id):
        if user_id == 2:
            return {
                "points": 45,
                "pending_count": 1,
                "claimed_count": 1,
                "completed_today": 1,
                "completed_this_week": 1,
            }
        elif user_id == 3:
            return {
                "points": 30,
                "pending_count": 0,
                "claimed_count": 0,
                "completed_today": 0,
                "completed_this_week": 0,
            }
        return {
            "points": 0,
            "pending_count": 0,
            "claimed_count": 0,
            "completed_today": 0,
            "completed_this_week": 0,
        }

    coordinator.get_kid_stats = get_kid_stats
    coordinator.get_user_by_id = lambda uid: next(
        (u for u in coordinator.data["users"] if u["id"] == uid), None
    )
    coordinator.async_request_refresh = AsyncMock()

    return coordinator
