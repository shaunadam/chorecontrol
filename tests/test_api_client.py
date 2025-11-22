"""Tests for ChoreControl API client."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.chorecontrol.api_client import ChoreControlApiClient


class AsyncContextManagerMock:
    """Helper class to mock async context managers."""

    def __init__(self, return_value):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, *args):
        pass


@pytest.fixture
def api_client():
    """Return an API client for testing."""
    hass = MagicMock()
    mock_session = MagicMock()

    with patch(
        "custom_components.chorecontrol.api_client.async_get_clientsession",
        return_value=mock_session,
    ):
        client = ChoreControlApiClient(hass, "http://localhost:8099")

    return client, mock_session


class TestCheckHealth:
    """Tests for check_health method."""

    @pytest.mark.asyncio
    async def test_check_health_success(self, api_client):
        """Test health check returns True when API is available."""
        client, mock_session = api_client

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={"status": "ok"})

        mock_session.request.return_value = AsyncContextManagerMock(mock_response)

        result = await client.check_health()

        assert result is True
        mock_session.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_health_failure(self, api_client):
        """Test health check returns False when API is unavailable."""
        client, mock_session = api_client

        mock_session.request.side_effect = aiohttp.ClientError()

        result = await client.check_health()

        assert result is False


class TestGetUsers:
    """Tests for get_users method."""

    @pytest.mark.asyncio
    async def test_get_users_success(self, api_client):
        """Test getting users returns list."""
        client, mock_session = api_client

        expected_users = [
            {"id": 1, "username": "parent1", "role": "parent"},
            {"id": 2, "username": "emma", "role": "kid"},
        ]

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value=expected_users)

        mock_session.request.return_value = AsyncContextManagerMock(mock_response)

        result = await client.get_users()

        assert result == expected_users
        mock_session.request.assert_called_with(
            "GET",
            "http://localhost:8099/api/users",
            json=None,
            timeout=aiohttp.ClientTimeout(total=10),
        )


class TestGetUser:
    """Tests for get_user method."""

    @pytest.mark.asyncio
    async def test_get_user_success(self, api_client):
        """Test getting single user by ID."""
        client, mock_session = api_client

        expected_user = {"id": 2, "username": "emma", "role": "kid", "points": 45}

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value=expected_user)

        mock_session.request.return_value = AsyncContextManagerMock(mock_response)

        result = await client.get_user(2)

        assert result == expected_user
        mock_session.request.assert_called_with(
            "GET",
            "http://localhost:8099/api/users/2",
            json=None,
            timeout=aiohttp.ClientTimeout(total=10),
        )


class TestGetChores:
    """Tests for get_chores method."""

    @pytest.mark.asyncio
    async def test_get_chores_active_only(self, api_client):
        """Test getting active chores."""
        client, mock_session = api_client

        expected_chores = [
            {"id": 1, "name": "Take out trash", "is_active": True},
        ]

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value=expected_chores)

        mock_session.request.return_value = AsyncContextManagerMock(mock_response)

        result = await client.get_chores(active_only=True)

        assert result == expected_chores
        mock_session.request.assert_called_with(
            "GET",
            "http://localhost:8099/api/chores?is_active=true",
            json=None,
            timeout=aiohttp.ClientTimeout(total=10),
        )

    @pytest.mark.asyncio
    async def test_get_chores_all(self, api_client):
        """Test getting all chores."""
        client, mock_session = api_client

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value=[])

        mock_session.request.return_value = AsyncContextManagerMock(mock_response)

        await client.get_chores(active_only=False)

        mock_session.request.assert_called_with(
            "GET",
            "http://localhost:8099/api/chores",
            json=None,
            timeout=aiohttp.ClientTimeout(total=10),
        )


class TestGetInstances:
    """Tests for get_instances method."""

    @pytest.mark.asyncio
    async def test_get_instances_no_filters(self, api_client):
        """Test getting all instances without filters."""
        client, mock_session = api_client

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value=[])

        mock_session.request.return_value = AsyncContextManagerMock(mock_response)

        await client.get_instances()

        mock_session.request.assert_called_with(
            "GET",
            "http://localhost:8099/api/instances",
            json=None,
            timeout=aiohttp.ClientTimeout(total=10),
        )

    @pytest.mark.asyncio
    async def test_get_instances_with_filters(self, api_client):
        """Test getting instances with filters."""
        client, mock_session = api_client

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value=[])

        mock_session.request.return_value = AsyncContextManagerMock(mock_response)

        await client.get_instances(status="assigned", user_id=2)

        call_args = mock_session.request.call_args
        url = call_args[0][1]
        assert "status=assigned" in url
        assert "user_id=2" in url


class TestClaimChore:
    """Tests for claim_chore method."""

    @pytest.mark.asyncio
    async def test_claim_chore_success(self, api_client):
        """Test claiming a chore."""
        client, mock_session = api_client

        expected_result = {"id": 1, "status": "claimed", "claimed_by": 2}

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value=expected_result)

        mock_session.request.return_value = AsyncContextManagerMock(mock_response)

        result = await client.claim_chore(1, 2)

        assert result == expected_result
        mock_session.request.assert_called_with(
            "POST",
            "http://localhost:8099/api/instances/1/claim",
            json={"user_id": 2},
            timeout=aiohttp.ClientTimeout(total=10),
        )


class TestApproveChore:
    """Tests for approve_chore method."""

    @pytest.mark.asyncio
    async def test_approve_chore_without_points(self, api_client):
        """Test approving a chore without points override."""
        client, mock_session = api_client

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={})

        mock_session.request.return_value = AsyncContextManagerMock(mock_response)

        await client.approve_chore(1, 1)

        mock_session.request.assert_called_with(
            "POST",
            "http://localhost:8099/api/instances/1/approve",
            json={"approver_user_id": 1},
            timeout=aiohttp.ClientTimeout(total=10),
        )

    @pytest.mark.asyncio
    async def test_approve_chore_with_points(self, api_client):
        """Test approving a chore with points override."""
        client, mock_session = api_client

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={})

        mock_session.request.return_value = AsyncContextManagerMock(mock_response)

        await client.approve_chore(1, 1, points=10)

        call_args = mock_session.request.call_args
        assert call_args[1]["json"] == {"approver_user_id": 1, "points": 10}


class TestRejectChore:
    """Tests for reject_chore method."""

    @pytest.mark.asyncio
    async def test_reject_chore_success(self, api_client):
        """Test rejecting a chore."""
        client, mock_session = api_client

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={})

        mock_session.request.return_value = AsyncContextManagerMock(mock_response)

        await client.reject_chore(1, 1, "Not done properly")

        mock_session.request.assert_called_with(
            "POST",
            "http://localhost:8099/api/instances/1/reject",
            json={
                "approver_user_id": 1,
                "reason": "Not done properly",
            },
            timeout=aiohttp.ClientTimeout(total=10),
        )


class TestRewardMethods:
    """Tests for reward-related methods."""

    @pytest.mark.asyncio
    async def test_claim_reward(self, api_client):
        """Test claiming a reward."""
        client, mock_session = api_client

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={})

        mock_session.request.return_value = AsyncContextManagerMock(mock_response)

        await client.claim_reward(1, 2)

        mock_session.request.assert_called_with(
            "POST",
            "http://localhost:8099/api/rewards/1/claim",
            json={"user_id": 2},
            timeout=aiohttp.ClientTimeout(total=10),
        )

    @pytest.mark.asyncio
    async def test_approve_reward(self, api_client):
        """Test approving a reward claim."""
        client, mock_session = api_client

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={})

        mock_session.request.return_value = AsyncContextManagerMock(mock_response)

        await client.approve_reward(1, 1)

        mock_session.request.assert_called_with(
            "POST",
            "http://localhost:8099/api/reward-claims/1/approve",
            json={"approver_user_id": 1},
            timeout=aiohttp.ClientTimeout(total=10),
        )

    @pytest.mark.asyncio
    async def test_reject_reward(self, api_client):
        """Test rejecting a reward claim."""
        client, mock_session = api_client

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={})

        mock_session.request.return_value = AsyncContextManagerMock(mock_response)

        await client.reject_reward(1, 1, "Not enough points")

        mock_session.request.assert_called_with(
            "POST",
            "http://localhost:8099/api/reward-claims/1/reject",
            json={
                "approver_user_id": 1,
                "reason": "Not enough points",
            },
            timeout=aiohttp.ClientTimeout(total=10),
        )


class TestAdjustPoints:
    """Tests for adjust_points method."""

    @pytest.mark.asyncio
    async def test_adjust_points(self, api_client):
        """Test adjusting points."""
        client, mock_session = api_client

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={})

        mock_session.request.return_value = AsyncContextManagerMock(mock_response)

        await client.adjust_points(2, -5, "Penalty for bad behavior")

        mock_session.request.assert_called_with(
            "POST",
            "http://localhost:8099/api/points/adjust",
            json={
                "user_id": 2,
                "points_delta": -5,
                "reason": "Penalty for bad behavior",
            },
            timeout=aiohttp.ClientTimeout(total=10),
        )


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_connection_error(self, api_client):
        """Test handling of connection errors."""
        client, mock_session = api_client

        mock_session.request.side_effect = aiohttp.ClientError(
            "Connection refused"
        )

        with pytest.raises(aiohttp.ClientError):
            await client.get_users()

    @pytest.mark.asyncio
    async def test_http_error(self, api_client):
        """Test handling of HTTP errors."""
        client, mock_session = api_client

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=500,
        )
        mock_response.json = AsyncMock(return_value={})

        mock_session.request.return_value = AsyncContextManagerMock(mock_response)

        with pytest.raises(aiohttp.ClientResponseError):
            await client.get_users()
