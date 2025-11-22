"""Tests for ChoreControl binary sensors."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from custom_components.chorecontrol.binary_sensor import ChoreControlApiConnectedSensor
from custom_components.chorecontrol.const import DOMAIN


class TestApiConnectedSensor:
    """Tests for API connected binary sensor."""

    def test_is_on_when_connected(self, mock_coordinator):
        """Test sensor returns True when API is connected."""
        sensor = ChoreControlApiConnectedSensor(mock_coordinator)
        assert sensor.is_on is True

    def test_is_off_when_disconnected(self, mock_coordinator):
        """Test sensor returns False when API is disconnected."""
        mock_coordinator.data["api_connected"] = False
        sensor = ChoreControlApiConnectedSensor(mock_coordinator)
        assert sensor.is_on is False

    def test_is_off_when_no_data(self, mock_coordinator):
        """Test sensor returns False when coordinator has no data."""
        mock_coordinator.data = None
        sensor = ChoreControlApiConnectedSensor(mock_coordinator)
        assert sensor.is_on is False

    def test_is_off_when_empty_data(self, mock_coordinator):
        """Test sensor returns False when coordinator has empty data."""
        mock_coordinator.data = {}
        sensor = ChoreControlApiConnectedSensor(mock_coordinator)
        assert sensor.is_on is False

    def test_unique_id(self, mock_coordinator):
        """Test sensor has correct unique ID."""
        sensor = ChoreControlApiConnectedSensor(mock_coordinator)
        assert sensor._attr_unique_id == f"{DOMAIN}_api_connected"

    def test_name(self, mock_coordinator):
        """Test sensor has correct name."""
        sensor = ChoreControlApiConnectedSensor(mock_coordinator)
        assert sensor._attr_name == "API connected"

    def test_device_info(self, mock_coordinator):
        """Test sensor has correct device info."""
        sensor = ChoreControlApiConnectedSensor(mock_coordinator)
        device_info = sensor.device_info

        assert "identifiers" in device_info
        assert (DOMAIN, "chorecontrol") in device_info["identifiers"]
        assert device_info["name"] == "ChoreControl"
        assert device_info["manufacturer"] == "ChoreControl"
        assert device_info["model"] == "Chore Management System"

    def test_has_entity_name(self, mock_coordinator):
        """Test sensor has entity name enabled."""
        sensor = ChoreControlApiConnectedSensor(mock_coordinator)
        assert sensor._attr_has_entity_name is True
