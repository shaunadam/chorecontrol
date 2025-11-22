"""Tests for ChoreControl config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.chorecontrol.config_flow import (
    CannotConnect,
    ConfigFlow,
    validate_input,
)
from custom_components.chorecontrol.const import (
    CONF_ADDON_URL,
    CONF_SCAN_INTERVAL,
    DEFAULT_ADDON_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)


class AsyncContextManagerMock:
    """Helper class to mock async context managers."""

    def __init__(self, return_value):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, *args):
        pass


class TestValidateInput:
    """Tests for validate_input function."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_validate_input_success(self, mock_hass):
        """Test successful validation."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200

            mock_session = MagicMock()
            mock_session.get.return_value = AsyncContextManagerMock(mock_response)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session

            data = {
                CONF_ADDON_URL: "http://localhost:8099",
                CONF_SCAN_INTERVAL: 30,
            }

            result = await validate_input(mock_hass, data)

            assert result["title"] == "ChoreControl"
            assert result[CONF_ADDON_URL] == "http://localhost:8099"

    @pytest.mark.asyncio
    async def test_validate_input_strips_trailing_slash(self, mock_hass):
        """Test that trailing slash is stripped from URL."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 200

            mock_session = MagicMock()
            mock_session.get.return_value = AsyncContextManagerMock(mock_response)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session

            data = {
                CONF_ADDON_URL: "http://localhost:8099/",
                CONF_SCAN_INTERVAL: 30,
            }

            result = await validate_input(mock_hass, data)

            assert result[CONF_ADDON_URL] == "http://localhost:8099"

    @pytest.mark.asyncio
    async def test_validate_input_connection_error(self, mock_hass):
        """Test validation fails on connection error."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.get.side_effect = aiohttp.ClientError("Connection refused")
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session

            data = {
                CONF_ADDON_URL: "http://localhost:8099",
                CONF_SCAN_INTERVAL: 30,
            }

            with pytest.raises(CannotConnect) as exc_info:
                await validate_input(mock_hass, data)

            assert "Cannot connect" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_input_non_200_status(self, mock_hass):
        """Test validation fails on non-200 status."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_response = MagicMock()
            mock_response.status = 500

            mock_session = MagicMock()
            mock_session.get.return_value = AsyncContextManagerMock(mock_response)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session

            data = {
                CONF_ADDON_URL: "http://localhost:8099",
                CONF_SCAN_INTERVAL: 30,
            }

            with pytest.raises(CannotConnect) as exc_info:
                await validate_input(mock_hass, data)

            assert "status 500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_input_unexpected_error(self, mock_hass):
        """Test validation fails on unexpected error."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = MagicMock()
            mock_session.get.side_effect = RuntimeError("Unexpected error")
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session

            data = {
                CONF_ADDON_URL: "http://localhost:8099",
                CONF_SCAN_INTERVAL: 30,
            }

            with pytest.raises(CannotConnect) as exc_info:
                await validate_input(mock_hass, data)

            assert "Unexpected error" in str(exc_info.value)


class TestConfigFlow:
    """Tests for ConfigFlow class."""

    @pytest.fixture
    def config_flow(self):
        """Create a ConfigFlow instance."""
        flow = ConfigFlow()
        flow.hass = MagicMock()
        return flow

    @pytest.mark.asyncio
    async def test_async_step_user_shows_form(self, config_flow):
        """Test that user step shows form when no input."""
        result = await config_flow.async_step_user()

        assert result["type"] == "form"
        assert result["step_id"] == "user"
        assert "data_schema" in result

    @pytest.mark.asyncio
    async def test_async_step_user_creates_entry_on_success(self, config_flow):
        """Test that user step creates entry on successful validation."""
        with patch(
            "custom_components.chorecontrol.config_flow.validate_input"
        ) as mock_validate:
            mock_validate.return_value = {
                "title": "ChoreControl",
                CONF_ADDON_URL: "http://localhost:8099",
            }

            user_input = {
                CONF_ADDON_URL: "http://localhost:8099",
                CONF_SCAN_INTERVAL: 30,
            }

            result = await config_flow.async_step_user(user_input)

            assert result["type"] == "create_entry"
            assert result["title"] == "ChoreControl"
            assert result["data"] == user_input

    @pytest.mark.asyncio
    async def test_async_step_user_shows_error_on_cannot_connect(self, config_flow):
        """Test that user step shows error on connection failure."""
        with patch(
            "custom_components.chorecontrol.config_flow.validate_input"
        ) as mock_validate:
            mock_validate.side_effect = CannotConnect("Connection refused")

            user_input = {
                CONF_ADDON_URL: "http://localhost:8099",
                CONF_SCAN_INTERVAL: 30,
            }

            result = await config_flow.async_step_user(user_input)

            assert result["type"] == "form"
            assert result["errors"]["base"] == "cannot_connect"

    @pytest.mark.asyncio
    async def test_async_step_user_shows_error_on_unknown_exception(self, config_flow):
        """Test that user step shows error on unknown exception."""
        with patch(
            "custom_components.chorecontrol.config_flow.validate_input"
        ) as mock_validate:
            mock_validate.side_effect = RuntimeError("Unknown error")

            user_input = {
                CONF_ADDON_URL: "http://localhost:8099",
                CONF_SCAN_INTERVAL: 30,
            }

            result = await config_flow.async_step_user(user_input)

            assert result["type"] == "form"
            assert result["errors"]["base"] == "unknown"

    def test_config_flow_version(self, config_flow):
        """Test config flow version."""
        assert config_flow.VERSION == 1


class TestCannotConnectException:
    """Tests for CannotConnect exception."""

    def test_cannot_connect_is_home_assistant_error(self):
        """Test CannotConnect inherits from HomeAssistantError."""
        from homeassistant.exceptions import HomeAssistantError

        assert issubclass(CannotConnect, HomeAssistantError)

    def test_cannot_connect_message(self):
        """Test CannotConnect preserves message."""
        error = CannotConnect("Test message")
        assert str(error) == "Test message"


class TestDefaultConstants:
    """Tests for default configuration constants."""

    def test_default_addon_url(self):
        """Test default add-on URL."""
        assert DEFAULT_ADDON_URL == "http://chorecontrol"

    def test_default_scan_interval(self):
        """Test default scan interval."""
        assert DEFAULT_SCAN_INTERVAL == 30

    def test_domain(self):
        """Test domain constant."""
        assert DOMAIN == "chorecontrol"


class TestDataSchemaValidation:
    """Tests for data schema validation."""

    def test_schema_requires_addon_url(self):
        """Test that schema requires addon_url."""
        from custom_components.chorecontrol.config_flow import STEP_USER_DATA_SCHEMA

        # addon_url should have a default
        schema_keys = list(STEP_USER_DATA_SCHEMA.schema.keys())
        key_names = [str(k) for k in schema_keys]
        assert any(CONF_ADDON_URL in k for k in key_names)

    def test_schema_has_scan_interval(self):
        """Test that schema includes scan_interval."""
        from custom_components.chorecontrol.config_flow import STEP_USER_DATA_SCHEMA

        schema_keys = list(STEP_USER_DATA_SCHEMA.schema.keys())
        key_names = [str(k) for k in schema_keys]
        assert any(CONF_SCAN_INTERVAL in k for k in key_names)

    def test_scan_interval_has_valid_range(self):
        """Test that scan_interval validates range."""
        from custom_components.chorecontrol.config_flow import STEP_USER_DATA_SCHEMA
        import voluptuous as vol

        # This should not raise
        STEP_USER_DATA_SCHEMA({CONF_ADDON_URL: "http://test", CONF_SCAN_INTERVAL: 30})

        # Values outside range should raise
        with pytest.raises(vol.MultipleInvalid):
            STEP_USER_DATA_SCHEMA({CONF_ADDON_URL: "http://test", CONF_SCAN_INTERVAL: 5})

        with pytest.raises(vol.MultipleInvalid):
            STEP_USER_DATA_SCHEMA(
                {CONF_ADDON_URL: "http://test", CONF_SCAN_INTERVAL: 500}
            )
