"""Config flow for ChoreControl integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_ADDON_URL,
    CONF_SCAN_INTERVAL,
    DEFAULT_ADDON_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Configuration step schemas
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ADDON_URL, default=DEFAULT_ADDON_URL): cv.string,
        vol.Optional(
            CONF_SCAN_INTERVAL,
            default=DEFAULT_SCAN_INTERVAL,
        ): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
    }
)


async def validate_input(
    hass: HomeAssistant,  # noqa: ARG001
    data: dict[str, Any],
) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    addon_url = data[CONF_ADDON_URL].rstrip("/")

    # Test connection to add-on
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                f"{addon_url}/health",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status != 200:
                    raise CannotConnect(
                        f"Add-on returned status {response.status}"
                    )
        except aiohttp.ClientError as err:
            _LOGGER.error("Cannot connect to ChoreControl add-on: %s", err)
            raise CannotConnect(f"Cannot connect to add-on: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error connecting to add-on")
            raise CannotConnect(f"Unexpected error: {err}") from err

    # Return info to store in config entry
    return {
        "title": "ChoreControl",
        CONF_ADDON_URL: addon_url,
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ChoreControl."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Create the config entry
                return self.async_create_entry(
                    title=info["title"],
                    data=user_input,
                )

        # Show configuration form
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
