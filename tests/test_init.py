"""Tests for ChoreControl integration setup."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.chorecontrol import (
    async_setup_entry,
    async_unload_entry,
    async_setup_services,
)
from custom_components.chorecontrol.const import (
    CONF_ADDON_URL,
    CONF_SCAN_INTERVAL,
    COORDINATOR,
    DOMAIN,
    PLATFORMS,
    SERVICE_ADJUST_POINTS,
    SERVICE_APPROVE_CHORE,
    SERVICE_APPROVE_REWARD,
    SERVICE_CLAIM_CHORE,
    SERVICE_CLAIM_REWARD,
    SERVICE_REFRESH_DATA,
    SERVICE_REJECT_CHORE,
    SERVICE_REJECT_REWARD,
    WEBHOOK_ID,
)


class TestAsyncSetupEntry:
    """Tests for async_setup_entry function."""

    @pytest.fixture
    def mock_config_entry(self):
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.data = {
            CONF_ADDON_URL: "http://localhost:8099",
            CONF_SCAN_INTERVAL: 30,
        }
        return entry

    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = MagicMock()
        hass.data = {}
        hass.services = MagicMock()
        hass.services.async_register = MagicMock()
        hass.config_entries = MagicMock()
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        return hass

    @pytest.mark.asyncio
    async def test_setup_entry_creates_coordinator(
        self, mock_hass, mock_config_entry, mock_api_client
    ):
        """Test that setup creates a coordinator."""
        with patch(
            "custom_components.chorecontrol.ChoreControlApiClient",
            return_value=mock_api_client,
        ), patch(
            "custom_components.chorecontrol.ChoreControlDataUpdateCoordinator"
        ) as mock_coordinator_class:
            mock_coordinator = MagicMock()
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator.api_client = mock_api_client
            mock_coordinator_class.return_value = mock_coordinator

            result = await async_setup_entry(mock_hass, mock_config_entry)

            assert result is True
            mock_coordinator_class.assert_called_once()
            mock_coordinator.async_config_entry_first_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_entry_stores_coordinator(
        self, mock_hass, mock_config_entry, mock_api_client
    ):
        """Test that setup stores coordinator in hass.data."""
        with patch(
            "custom_components.chorecontrol.ChoreControlApiClient",
            return_value=mock_api_client,
        ), patch(
            "custom_components.chorecontrol.ChoreControlDataUpdateCoordinator"
        ) as mock_coordinator_class:
            mock_coordinator = MagicMock()
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator.api_client = mock_api_client
            mock_coordinator_class.return_value = mock_coordinator

            await async_setup_entry(mock_hass, mock_config_entry)

            assert DOMAIN in mock_hass.data
            assert mock_config_entry.entry_id in mock_hass.data[DOMAIN]
            assert COORDINATOR in mock_hass.data[DOMAIN][mock_config_entry.entry_id]

    @pytest.mark.asyncio
    async def test_setup_entry_registers_webhook(
        self, mock_hass, mock_config_entry, mock_api_client
    ):
        """Test that setup registers webhook."""
        with patch(
            "custom_components.chorecontrol.ChoreControlApiClient",
            return_value=mock_api_client,
        ), patch(
            "custom_components.chorecontrol.ChoreControlDataUpdateCoordinator"
        ) as mock_coordinator_class:
            mock_coordinator = MagicMock()
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator.api_client = mock_api_client
            mock_coordinator_class.return_value = mock_coordinator

            await async_setup_entry(mock_hass, mock_config_entry)

            # Verify webhook URL is stored
            assert "webhook_url" in mock_hass.data[DOMAIN][mock_config_entry.entry_id]

    @pytest.mark.asyncio
    async def test_setup_entry_forwards_platforms(
        self, mock_hass, mock_config_entry, mock_api_client
    ):
        """Test that setup forwards entry to platforms."""
        with patch(
            "custom_components.chorecontrol.ChoreControlApiClient",
            return_value=mock_api_client,
        ), patch(
            "custom_components.chorecontrol.ChoreControlDataUpdateCoordinator"
        ) as mock_coordinator_class:
            mock_coordinator = MagicMock()
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator.api_client = mock_api_client
            mock_coordinator_class.return_value = mock_coordinator

            await async_setup_entry(mock_hass, mock_config_entry)

            mock_hass.config_entries.async_forward_entry_setups.assert_called_once_with(
                mock_config_entry, PLATFORMS
            )

    @pytest.mark.asyncio
    async def test_setup_entry_registers_services(
        self, mock_hass, mock_config_entry, mock_api_client
    ):
        """Test that setup registers all services."""
        with patch(
            "custom_components.chorecontrol.ChoreControlApiClient",
            return_value=mock_api_client,
        ), patch(
            "custom_components.chorecontrol.ChoreControlDataUpdateCoordinator"
        ) as mock_coordinator_class:
            mock_coordinator = MagicMock()
            mock_coordinator.async_config_entry_first_refresh = AsyncMock()
            mock_coordinator.api_client = mock_api_client
            mock_coordinator_class.return_value = mock_coordinator

            await async_setup_entry(mock_hass, mock_config_entry)

            # Verify services were registered
            registered_services = [
                call[0][1]
                for call in mock_hass.services.async_register.call_args_list
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


class TestAsyncUnloadEntry:
    """Tests for async_unload_entry function."""

    @pytest.fixture
    def mock_config_entry(self):
        """Create a mock config entry."""
        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        return entry

    @pytest.fixture
    def mock_hass_with_entry(self, mock_coordinator):
        """Create a mock hass with entry data."""
        hass = MagicMock()
        hass.data = {
            DOMAIN: {
                "test_entry_id": {
                    COORDINATOR: mock_coordinator,
                    "webhook_url": "http://test",
                }
            }
        }
        hass.config_entries = MagicMock()
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        return hass

    @pytest.mark.asyncio
    async def test_unload_entry_success(
        self, mock_hass_with_entry, mock_config_entry
    ):
        """Test successful unload."""
        result = await async_unload_entry(mock_hass_with_entry, mock_config_entry)

        assert result is True

    @pytest.mark.asyncio
    async def test_unload_entry_removes_data(
        self, mock_hass_with_entry, mock_config_entry
    ):
        """Test unload removes entry data."""
        await async_unload_entry(mock_hass_with_entry, mock_config_entry)

        assert mock_config_entry.entry_id not in mock_hass_with_entry.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_unload_entry_unloads_platforms(
        self, mock_hass_with_entry, mock_config_entry
    ):
        """Test unload unloads platforms."""
        await async_unload_entry(mock_hass_with_entry, mock_config_entry)

        mock_hass_with_entry.config_entries.async_unload_platforms.assert_called_once_with(
            mock_config_entry, PLATFORMS
        )

    @pytest.mark.asyncio
    async def test_unload_entry_failure_preserves_data(
        self, mock_hass_with_entry, mock_config_entry
    ):
        """Test that unload failure preserves entry data."""
        mock_hass_with_entry.config_entries.async_unload_platforms = AsyncMock(
            return_value=False
        )

        result = await async_unload_entry(mock_hass_with_entry, mock_config_entry)

        assert result is False
        # Data should still be present
        assert mock_config_entry.entry_id in mock_hass_with_entry.data[DOMAIN]


class TestPlatformsConstant:
    """Tests for PLATFORMS constant."""

    def test_platforms_contains_sensor(self):
        """Test that PLATFORMS includes sensor."""
        assert "sensor" in PLATFORMS

    def test_platforms_contains_button(self):
        """Test that PLATFORMS includes button."""
        assert "button" in PLATFORMS

    def test_platforms_contains_binary_sensor(self):
        """Test that PLATFORMS includes binary_sensor."""
        assert "binary_sensor" in PLATFORMS


class TestWebhookIdConstant:
    """Tests for WEBHOOK_ID constant."""

    def test_webhook_id_format(self):
        """Test webhook ID has correct format."""
        assert WEBHOOK_ID == f"{DOMAIN}_events"
        assert WEBHOOK_ID.startswith(DOMAIN)
