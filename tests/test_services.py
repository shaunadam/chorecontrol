"""Tests for ChoreControl services."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.chorecontrol import async_setup_services
from custom_components.chorecontrol.const import (
    ATTR_APPROVER_USER_ID,
    ATTR_CHORE_INSTANCE_ID,
    ATTR_CLAIM_ID,
    ATTR_POINTS,
    ATTR_POINTS_DELTA,
    ATTR_REASON,
    ATTR_REWARD_ID,
    ATTR_USER_ID,
    DOMAIN,
    SERVICE_ADJUST_POINTS,
    SERVICE_APPROVE_CHORE,
    SERVICE_APPROVE_REWARD,
    SERVICE_CLAIM_CHORE,
    SERVICE_CLAIM_REWARD,
    SERVICE_REFRESH_DATA,
    SERVICE_REJECT_CHORE,
    SERVICE_REJECT_REWARD,
)


@pytest.fixture
def mock_hass():
    """Return a mocked Home Assistant instance."""
    hass = MagicMock()
    hass.services = MagicMock()
    hass.services.async_register = MagicMock()
    return hass


@pytest.fixture
async def setup_services(mock_hass, mock_coordinator):
    """Set up services for testing."""
    await async_setup_services(mock_hass, mock_coordinator)
    return mock_hass


class TestServiceRegistration:
    """Tests for service registration."""

    @pytest.mark.asyncio
    async def test_all_services_registered(self, setup_services):
        """Test that all services are registered."""
        hass = setup_services

        registered_services = [
            call[0][1]  # Second argument is service name
            for call in hass.services.async_register.call_args_list
        ]

        expected_services = [
            SERVICE_CLAIM_CHORE,
            SERVICE_APPROVE_CHORE,
            SERVICE_REJECT_CHORE,
            SERVICE_ADJUST_POINTS,
            SERVICE_CLAIM_REWARD,
            SERVICE_APPROVE_REWARD,
            SERVICE_REJECT_REWARD,
            SERVICE_REFRESH_DATA,
        ]

        for service in expected_services:
            assert service in registered_services, f"Service {service} not registered"


class TestClaimChoreService:
    """Tests for claim_chore service."""

    @pytest.mark.asyncio
    async def test_claim_chore_success(self, mock_hass, mock_coordinator):
        """Test successful chore claim."""
        await async_setup_services(mock_hass, mock_coordinator)

        # Get the handler
        handler = None
        for call in mock_hass.services.async_register.call_args_list:
            if call[0][1] == SERVICE_CLAIM_CHORE:
                handler = call[0][2]
                break

        assert handler is not None

        # Create mock service call
        call = MagicMock()
        call.data = {
            ATTR_CHORE_INSTANCE_ID: 42,
            ATTR_USER_ID: 3,
        }

        mock_coordinator.api_client.claim_chore.return_value = {"id": 42}

        await handler(call)

        mock_coordinator.api_client.claim_chore.assert_called_once_with(42, 3)
        mock_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_claim_chore_failure(self, mock_hass, mock_coordinator):
        """Test claim chore when API returns None."""
        await async_setup_services(mock_hass, mock_coordinator)

        handler = None
        for call in mock_hass.services.async_register.call_args_list:
            if call[0][1] == SERVICE_CLAIM_CHORE:
                handler = call[0][2]
                break

        call = MagicMock()
        call.data = {
            ATTR_CHORE_INSTANCE_ID: 42,
            ATTR_USER_ID: 3,
        }

        mock_coordinator.api_client.claim_chore.return_value = None

        with pytest.raises(HomeAssistantError):
            await handler(call)

    @pytest.mark.asyncio
    async def test_claim_chore_exception(self, mock_hass, mock_coordinator):
        """Test claim chore when API raises exception."""
        await async_setup_services(mock_hass, mock_coordinator)

        handler = None
        for call in mock_hass.services.async_register.call_args_list:
            if call[0][1] == SERVICE_CLAIM_CHORE:
                handler = call[0][2]
                break

        call = MagicMock()
        call.data = {
            ATTR_CHORE_INSTANCE_ID: 42,
            ATTR_USER_ID: 3,
        }

        mock_coordinator.api_client.claim_chore.side_effect = Exception("API error")

        with pytest.raises(HomeAssistantError) as exc_info:
            await handler(call)

        assert "API error" in str(exc_info.value)


class TestApproveChoreService:
    """Tests for approve_chore service."""

    @pytest.mark.asyncio
    async def test_approve_chore_success(self, mock_hass, mock_coordinator):
        """Test successful chore approval."""
        await async_setup_services(mock_hass, mock_coordinator)

        handler = None
        for call in mock_hass.services.async_register.call_args_list:
            if call[0][1] == SERVICE_APPROVE_CHORE:
                handler = call[0][2]
                break

        call = MagicMock()
        call.data = {
            ATTR_CHORE_INSTANCE_ID: 42,
            ATTR_APPROVER_USER_ID: 1,
        }

        mock_coordinator.api_client.approve_chore.return_value = {"id": 42}

        await handler(call)

        mock_coordinator.api_client.approve_chore.assert_called_once_with(42, 1, None)
        mock_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_approve_chore_with_points_override(self, mock_hass, mock_coordinator):
        """Test chore approval with points override."""
        await async_setup_services(mock_hass, mock_coordinator)

        handler = None
        for call in mock_hass.services.async_register.call_args_list:
            if call[0][1] == SERVICE_APPROVE_CHORE:
                handler = call[0][2]
                break

        call = MagicMock()
        call.data = {
            ATTR_CHORE_INSTANCE_ID: 42,
            ATTR_APPROVER_USER_ID: 1,
            ATTR_POINTS: 10,
        }

        mock_coordinator.api_client.approve_chore.return_value = {"id": 42}

        await handler(call)

        mock_coordinator.api_client.approve_chore.assert_called_once_with(42, 1, 10)

    @pytest.mark.asyncio
    async def test_approve_chore_failure(self, mock_hass, mock_coordinator):
        """Test approve chore when API returns None."""
        await async_setup_services(mock_hass, mock_coordinator)

        handler = None
        for call in mock_hass.services.async_register.call_args_list:
            if call[0][1] == SERVICE_APPROVE_CHORE:
                handler = call[0][2]
                break

        call = MagicMock()
        call.data = {
            ATTR_CHORE_INSTANCE_ID: 42,
            ATTR_APPROVER_USER_ID: 1,
        }

        mock_coordinator.api_client.approve_chore.return_value = None

        with pytest.raises(HomeAssistantError):
            await handler(call)


class TestRejectChoreService:
    """Tests for reject_chore service."""

    @pytest.mark.asyncio
    async def test_reject_chore_success(self, mock_hass, mock_coordinator):
        """Test successful chore rejection."""
        await async_setup_services(mock_hass, mock_coordinator)

        handler = None
        for call in mock_hass.services.async_register.call_args_list:
            if call[0][1] == SERVICE_REJECT_CHORE:
                handler = call[0][2]
                break

        call = MagicMock()
        call.data = {
            ATTR_CHORE_INSTANCE_ID: 42,
            ATTR_APPROVER_USER_ID: 1,
            ATTR_REASON: "Not done properly",
        }

        mock_coordinator.api_client.reject_chore.return_value = {"id": 42}

        await handler(call)

        mock_coordinator.api_client.reject_chore.assert_called_once_with(
            42, 1, "Not done properly"
        )
        mock_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_reject_chore_failure(self, mock_hass, mock_coordinator):
        """Test reject chore when API returns None."""
        await async_setup_services(mock_hass, mock_coordinator)

        handler = None
        for call in mock_hass.services.async_register.call_args_list:
            if call[0][1] == SERVICE_REJECT_CHORE:
                handler = call[0][2]
                break

        call = MagicMock()
        call.data = {
            ATTR_CHORE_INSTANCE_ID: 42,
            ATTR_APPROVER_USER_ID: 1,
            ATTR_REASON: "Not done properly",
        }

        mock_coordinator.api_client.reject_chore.return_value = None

        with pytest.raises(HomeAssistantError):
            await handler(call)


class TestAdjustPointsService:
    """Tests for adjust_points service."""

    @pytest.mark.asyncio
    async def test_adjust_points_success(self, mock_hass, mock_coordinator):
        """Test successful points adjustment."""
        await async_setup_services(mock_hass, mock_coordinator)

        handler = None
        for call in mock_hass.services.async_register.call_args_list:
            if call[0][1] == SERVICE_ADJUST_POINTS:
                handler = call[0][2]
                break

        call = MagicMock()
        call.data = {
            ATTR_USER_ID: 3,
            ATTR_POINTS_DELTA: -5,
            ATTR_REASON: "Left toys out",
        }

        mock_coordinator.api_client.adjust_points.return_value = {"user_id": 3}

        await handler(call)

        mock_coordinator.api_client.adjust_points.assert_called_once_with(
            3, -5, "Left toys out"
        )
        mock_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_adjust_points_positive(self, mock_hass, mock_coordinator):
        """Test positive points adjustment."""
        await async_setup_services(mock_hass, mock_coordinator)

        handler = None
        for call in mock_hass.services.async_register.call_args_list:
            if call[0][1] == SERVICE_ADJUST_POINTS:
                handler = call[0][2]
                break

        call = MagicMock()
        call.data = {
            ATTR_USER_ID: 3,
            ATTR_POINTS_DELTA: 10,
            ATTR_REASON: "Bonus for helping",
        }

        mock_coordinator.api_client.adjust_points.return_value = {"user_id": 3}

        await handler(call)

        mock_coordinator.api_client.adjust_points.assert_called_once_with(
            3, 10, "Bonus for helping"
        )


class TestClaimRewardService:
    """Tests for claim_reward service."""

    @pytest.mark.asyncio
    async def test_claim_reward_success(self, mock_hass, mock_coordinator):
        """Test successful reward claim."""
        await async_setup_services(mock_hass, mock_coordinator)

        handler = None
        for call in mock_hass.services.async_register.call_args_list:
            if call[0][1] == SERVICE_CLAIM_REWARD:
                handler = call[0][2]
                break

        call = MagicMock()
        call.data = {
            ATTR_REWARD_ID: 2,
            ATTR_USER_ID: 3,
        }

        mock_coordinator.api_client.claim_reward.return_value = {"id": 15}

        await handler(call)

        mock_coordinator.api_client.claim_reward.assert_called_once_with(2, 3)
        mock_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_claim_reward_failure(self, mock_hass, mock_coordinator):
        """Test claim reward when API returns None."""
        await async_setup_services(mock_hass, mock_coordinator)

        handler = None
        for call in mock_hass.services.async_register.call_args_list:
            if call[0][1] == SERVICE_CLAIM_REWARD:
                handler = call[0][2]
                break

        call = MagicMock()
        call.data = {
            ATTR_REWARD_ID: 2,
            ATTR_USER_ID: 3,
        }

        mock_coordinator.api_client.claim_reward.return_value = None

        with pytest.raises(HomeAssistantError):
            await handler(call)


class TestApproveRewardService:
    """Tests for approve_reward service."""

    @pytest.mark.asyncio
    async def test_approve_reward_success(self, mock_hass, mock_coordinator):
        """Test successful reward approval."""
        await async_setup_services(mock_hass, mock_coordinator)

        handler = None
        for call in mock_hass.services.async_register.call_args_list:
            if call[0][1] == SERVICE_APPROVE_REWARD:
                handler = call[0][2]
                break

        call = MagicMock()
        call.data = {
            ATTR_CLAIM_ID: 15,
            ATTR_APPROVER_USER_ID: 1,
        }

        mock_coordinator.api_client.approve_reward.return_value = {"id": 15}

        await handler(call)

        mock_coordinator.api_client.approve_reward.assert_called_once_with(15, 1)
        mock_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_approve_reward_failure(self, mock_hass, mock_coordinator):
        """Test approve reward when API returns None."""
        await async_setup_services(mock_hass, mock_coordinator)

        handler = None
        for call in mock_hass.services.async_register.call_args_list:
            if call[0][1] == SERVICE_APPROVE_REWARD:
                handler = call[0][2]
                break

        call = MagicMock()
        call.data = {
            ATTR_CLAIM_ID: 15,
            ATTR_APPROVER_USER_ID: 1,
        }

        mock_coordinator.api_client.approve_reward.return_value = None

        with pytest.raises(HomeAssistantError):
            await handler(call)

    @pytest.mark.asyncio
    async def test_approve_reward_exception(self, mock_hass, mock_coordinator):
        """Test approve reward when API raises exception."""
        await async_setup_services(mock_hass, mock_coordinator)

        handler = None
        for call in mock_hass.services.async_register.call_args_list:
            if call[0][1] == SERVICE_APPROVE_REWARD:
                handler = call[0][2]
                break

        call = MagicMock()
        call.data = {
            ATTR_CLAIM_ID: 15,
            ATTR_APPROVER_USER_ID: 1,
        }

        mock_coordinator.api_client.approve_reward.side_effect = Exception("API error")

        with pytest.raises(HomeAssistantError) as exc_info:
            await handler(call)

        assert "API error" in str(exc_info.value)


class TestRejectRewardService:
    """Tests for reject_reward service."""

    @pytest.mark.asyncio
    async def test_reject_reward_success(self, mock_hass, mock_coordinator):
        """Test successful reward rejection."""
        await async_setup_services(mock_hass, mock_coordinator)

        handler = None
        for call in mock_hass.services.async_register.call_args_list:
            if call[0][1] == SERVICE_REJECT_REWARD:
                handler = call[0][2]
                break

        call = MagicMock()
        call.data = {
            ATTR_CLAIM_ID: 15,
            ATTR_APPROVER_USER_ID: 1,
            ATTR_REASON: "Not enough good behavior",
        }

        mock_coordinator.api_client.reject_reward.return_value = {"id": 15}

        await handler(call)

        mock_coordinator.api_client.reject_reward.assert_called_once_with(
            15, 1, "Not enough good behavior"
        )
        mock_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_reject_reward_failure(self, mock_hass, mock_coordinator):
        """Test reject reward when API returns None."""
        await async_setup_services(mock_hass, mock_coordinator)

        handler = None
        for call in mock_hass.services.async_register.call_args_list:
            if call[0][1] == SERVICE_REJECT_REWARD:
                handler = call[0][2]
                break

        call = MagicMock()
        call.data = {
            ATTR_CLAIM_ID: 15,
            ATTR_APPROVER_USER_ID: 1,
            ATTR_REASON: "Not enough good behavior",
        }

        mock_coordinator.api_client.reject_reward.return_value = None

        with pytest.raises(HomeAssistantError):
            await handler(call)


class TestRefreshDataService:
    """Tests for refresh_data service."""

    @pytest.mark.asyncio
    async def test_refresh_data_success(self, mock_hass, mock_coordinator):
        """Test successful data refresh."""
        await async_setup_services(mock_hass, mock_coordinator)

        handler = None
        for call in mock_hass.services.async_register.call_args_list:
            if call[0][1] == SERVICE_REFRESH_DATA:
                handler = call[0][2]
                break

        call = MagicMock()
        call.data = {}

        await handler(call)

        mock_coordinator.async_request_refresh.assert_called_once()
