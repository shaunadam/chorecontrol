"""Tests for ChoreControl webhook handling."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

from custom_components.chorecontrol import (
    handle_webhook,
    notify_parents,
    notify_user,
    process_webhook_event,
)
from custom_components.chorecontrol.const import (
    COORDINATOR,
    DOMAIN,
    EVENT_CHORE_INSTANCE_APPROVED,
    EVENT_CHORE_INSTANCE_CLAIMED,
    EVENT_CHORE_INSTANCE_REJECTED,
    EVENT_REWARD_CLAIM_APPROVED,
    EVENT_REWARD_CLAIM_CLAIMED,
    EVENT_REWARD_CLAIM_REJECTED,
    WEBHOOK_ID,
)


class TestHandleWebhook:
    """Tests for webhook handler."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock aiohttp request."""
        request = MagicMock(spec=web.Request)
        return request

    @pytest.fixture
    def mock_hass(self, mock_coordinator):
        """Create a mock hass instance with coordinator."""
        hass = MagicMock()
        hass.data = {
            DOMAIN: {
                "test_entry": {
                    COORDINATOR: mock_coordinator,
                }
            }
        }
        hass.bus = MagicMock()
        hass.bus.async_fire = MagicMock()
        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()
        return hass

    @pytest.mark.asyncio
    async def test_handle_webhook_valid_event(self, mock_hass, mock_request, mock_coordinator):
        """Test handling a valid webhook event."""
        event_data = {
            "event": "chore_instance_claimed",
            "timestamp": "2025-01-15T14:30:00Z",
            "data": {
                "instance_id": 42,
                "chore_name": "Take out trash",
                "user_id": 3,
                "username": "emma",
                "points": 5,
            },
        }
        mock_request.json = AsyncMock(return_value=event_data)

        response = await handle_webhook(mock_hass, WEBHOOK_ID, mock_request)

        assert response.status == 200
        assert response.text == "OK"
        mock_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_webhook_invalid_json(self, mock_hass, mock_request):
        """Test handling invalid JSON in webhook."""
        mock_request.json = AsyncMock(side_effect=ValueError("Invalid JSON"))

        response = await handle_webhook(mock_hass, WEBHOOK_ID, mock_request)

        assert response.status == 400
        assert "Invalid JSON" in response.text

    @pytest.mark.asyncio
    async def test_handle_webhook_no_coordinator(self, mock_request):
        """Test handling webhook when no coordinator found."""
        hass = MagicMock()
        hass.data = {DOMAIN: {}}  # No coordinator

        event_data = {
            "event": "chore_instance_claimed",
            "data": {"instance_id": 42},
        }
        mock_request.json = AsyncMock(return_value=event_data)

        response = await handle_webhook(hass, WEBHOOK_ID, mock_request)

        assert response.status == 500
        assert "No coordinator found" in response.text

    @pytest.mark.asyncio
    async def test_handle_webhook_fires_ha_event(self, mock_hass, mock_request, mock_coordinator):
        """Test that webhook fires HA event for automations."""
        event_data = {
            "event": "chore_instance_claimed",
            "timestamp": "2025-01-15T14:30:00Z",
            "data": {
                "instance_id": 42,
                "chore_name": "Take out trash",
                "user_id": 3,
                "username": "emma",
            },
        }
        mock_request.json = AsyncMock(return_value=event_data)

        await handle_webhook(mock_hass, WEBHOOK_ID, mock_request)

        mock_hass.bus.async_fire.assert_called_once_with(
            f"{DOMAIN}_chore_instance_claimed",
            event_data["data"],
        )


class TestProcessWebhookEvent:
    """Tests for webhook event processing."""

    @pytest.fixture
    def mock_hass(self, mock_coordinator):
        """Create a mock hass instance."""
        hass = MagicMock()
        hass.bus = MagicMock()
        hass.bus.async_fire = MagicMock()
        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()
        return hass

    @pytest.mark.asyncio
    async def test_process_chore_claimed_event(self, mock_hass, mock_coordinator):
        """Test processing chore claimed event sends parent notification."""
        event_data = {
            "username": "emma",
            "chore_name": "Take out trash",
            "instance_id": 42,
        }

        await process_webhook_event(
            mock_hass,
            mock_coordinator,
            EVENT_CHORE_INSTANCE_CLAIMED,
            event_data,
        )

        # Check HA event fired
        mock_hass.bus.async_fire.assert_called_once()

        # Check notification sent
        mock_hass.services.async_call.assert_called_once()
        call_args = mock_hass.services.async_call.call_args
        assert call_args[0][0] == "persistent_notification"
        assert call_args[0][1] == "create"
        assert "emma" in call_args[0][2]["message"]
        assert "Take out trash" in call_args[0][2]["message"]

    @pytest.mark.asyncio
    async def test_process_chore_approved_event(self, mock_hass, mock_coordinator):
        """Test processing chore approved event sends user notification."""
        event_data = {
            "user_id": 3,
            "chore_name": "Take out trash",
            "points_awarded": 5,
        }

        await process_webhook_event(
            mock_hass,
            mock_coordinator,
            EVENT_CHORE_INSTANCE_APPROVED,
            event_data,
        )

        # Check notification sent to user
        mock_hass.services.async_call.assert_called_once()
        call_args = mock_hass.services.async_call.call_args
        assert "Approved" in call_args[0][2]["title"]
        assert "+5 points" in call_args[0][2]["message"]

    @pytest.mark.asyncio
    async def test_process_chore_rejected_event(self, mock_hass, mock_coordinator):
        """Test processing chore rejected event sends user notification."""
        event_data = {
            "user_id": 3,
            "chore_name": "Take out trash",
            "reason": "Not done properly",
        }

        await process_webhook_event(
            mock_hass,
            mock_coordinator,
            EVENT_CHORE_INSTANCE_REJECTED,
            event_data,
        )

        # Check notification sent to user
        mock_hass.services.async_call.assert_called_once()
        call_args = mock_hass.services.async_call.call_args
        assert "Rejected" in call_args[0][2]["title"]
        assert "Not done properly" in call_args[0][2]["message"]

    @pytest.mark.asyncio
    async def test_process_reward_claimed_event(self, mock_hass, mock_coordinator):
        """Test processing reward claimed event sends parent notification."""
        event_data = {
            "username": "emma",
            "reward_name": "Ice cream",
        }

        await process_webhook_event(
            mock_hass,
            mock_coordinator,
            EVENT_REWARD_CLAIM_CLAIMED,
            event_data,
        )

        # Check notification sent
        mock_hass.services.async_call.assert_called_once()
        call_args = mock_hass.services.async_call.call_args
        assert "Reward Claimed" in call_args[0][2]["title"]
        assert "emma" in call_args[0][2]["message"]
        assert "Ice cream" in call_args[0][2]["message"]

    @pytest.mark.asyncio
    async def test_process_reward_approved_event(self, mock_hass, mock_coordinator):
        """Test processing reward approved event sends user notification."""
        event_data = {
            "user_id": 3,
            "reward_name": "Ice cream",
        }

        await process_webhook_event(
            mock_hass,
            mock_coordinator,
            EVENT_REWARD_CLAIM_APPROVED,
            event_data,
        )

        # Check notification sent to user
        mock_hass.services.async_call.assert_called_once()
        call_args = mock_hass.services.async_call.call_args
        assert "Reward Approved" in call_args[0][2]["title"]
        assert "Ice cream" in call_args[0][2]["message"]

    @pytest.mark.asyncio
    async def test_process_reward_rejected_event(self, mock_hass, mock_coordinator):
        """Test processing reward rejected event sends user notification."""
        event_data = {
            "user_id": 3,
            "reward_name": "Movie night",
            "reason": "Not enough points",
        }

        await process_webhook_event(
            mock_hass,
            mock_coordinator,
            EVENT_REWARD_CLAIM_REJECTED,
            event_data,
        )

        # Check notification sent to user
        mock_hass.services.async_call.assert_called_once()
        call_args = mock_hass.services.async_call.call_args
        assert "Reward Rejected" in call_args[0][2]["title"]
        assert "Not enough points" in call_args[0][2]["message"]

    @pytest.mark.asyncio
    async def test_process_event_no_user_id_skips_notification(self, mock_hass, mock_coordinator):
        """Test that events without user_id don't send user notifications."""
        event_data = {
            "chore_name": "Take out trash",
            "points_awarded": 5,
            # No user_id
        }

        await process_webhook_event(
            mock_hass,
            mock_coordinator,
            EVENT_CHORE_INSTANCE_APPROVED,
            event_data,
        )

        # Should not send notification (no user_id)
        mock_hass.services.async_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_event_with_missing_data_uses_defaults(self, mock_hass, mock_coordinator):
        """Test that missing event data uses default values."""
        event_data = {}  # Empty event data

        await process_webhook_event(
            mock_hass,
            mock_coordinator,
            EVENT_CHORE_INSTANCE_CLAIMED,
            event_data,
        )

        # Should still send notification with defaults
        mock_hass.services.async_call.assert_called_once()
        call_args = mock_hass.services.async_call.call_args
        assert "Someone" in call_args[0][2]["message"]
        assert "a chore" in call_args[0][2]["message"]


class TestNotifyParents:
    """Tests for parent notification function."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock hass instance."""
        hass = MagicMock()
        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()
        return hass

    @pytest.mark.asyncio
    async def test_notify_parents_creates_notification(self, mock_hass, mock_coordinator):
        """Test that notify_parents creates a persistent notification."""
        await notify_parents(
            mock_hass,
            mock_coordinator,
            title="Test Title",
            message="Test message",
        )

        mock_hass.services.async_call.assert_called_once_with(
            "persistent_notification",
            "create",
            {
                "title": "Test Title",
                "message": "Test message",
                "notification_id": f"{DOMAIN}_test_title",
            },
        )

    @pytest.mark.asyncio
    async def test_notify_parents_handles_error(self, mock_hass, mock_coordinator):
        """Test that notify_parents handles service call errors."""
        mock_hass.services.async_call = AsyncMock(side_effect=Exception("Service error"))

        # Should not raise exception
        await notify_parents(
            mock_hass,
            mock_coordinator,
            title="Test Title",
            message="Test message",
        )


class TestNotifyUser:
    """Tests for user notification function."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock hass instance."""
        hass = MagicMock()
        hass.services = MagicMock()
        hass.services.async_call = AsyncMock()
        return hass

    @pytest.mark.asyncio
    async def test_notify_user_creates_notification(self, mock_hass):
        """Test that notify_user creates a persistent notification."""
        await notify_user(
            mock_hass,
            user_id=3,
            title="Test Title",
            message="Test message",
        )

        mock_hass.services.async_call.assert_called_once_with(
            "persistent_notification",
            "create",
            {
                "title": "Test Title",
                "message": "Test message",
                "notification_id": f"{DOMAIN}_3_test_title",
            },
        )

    @pytest.mark.asyncio
    async def test_notify_user_handles_error(self, mock_hass):
        """Test that notify_user handles service call errors."""
        mock_hass.services.async_call = AsyncMock(side_effect=Exception("Service error"))

        # Should not raise exception
        await notify_user(
            mock_hass,
            user_id=3,
            title="Test Title",
            message="Test message",
        )


class TestWebhookRegistration:
    """Tests for webhook registration/unregistration."""

    @pytest.mark.asyncio
    async def test_webhook_registered_on_setup(self):
        """Test that webhook is registered during setup."""
        # This test would require more complex setup with actual HA
        # For now, we verify the constants are correct
        assert f"{DOMAIN}_events" == WEBHOOK_ID

    @pytest.mark.asyncio
    async def test_webhook_id_format(self):
        """Test webhook ID follows correct format."""
        assert WEBHOOK_ID.startswith(DOMAIN)
        assert "events" in WEBHOOK_ID
