"""Tests for ChoreControl sensors."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.chorecontrol.const import DOMAIN
from custom_components.chorecontrol.sensor import (
    ChoreControlActiveChoresSensor,
    ChoreControlClaimedChoresSensor,
    ChoreControlCompletedThisWeekSensor,
    ChoreControlCompletedTodaySensor,
    ChoreControlPendingApprovalsSensor,
    ChoreControlPendingChoresSensor,
    ChoreControlPointsSensor,
    ChoreControlTotalKidsSensor,
)


class TestPendingApprovalsSensor:
    """Tests for pending approvals sensor."""

    def test_native_value(self, mock_coordinator):
        """Test sensor returns correct value."""
        sensor = ChoreControlPendingApprovalsSensor(mock_coordinator)
        assert sensor.native_value == 1

    def test_native_value_no_data(self, mock_coordinator):
        """Test sensor returns 0 when no data."""
        mock_coordinator.data = None
        sensor = ChoreControlPendingApprovalsSensor(mock_coordinator)
        assert sensor.native_value == 0

    def test_native_value_missing_key(self, mock_coordinator):
        """Test sensor returns 0 when key is missing."""
        mock_coordinator.data = {}
        sensor = ChoreControlPendingApprovalsSensor(mock_coordinator)
        assert sensor.native_value == 0

    def test_unique_id(self, mock_coordinator):
        """Test sensor has correct unique_id."""
        sensor = ChoreControlPendingApprovalsSensor(mock_coordinator)
        assert sensor.unique_id == f"{DOMAIN}_pending_approvals"

    def test_device_info(self, mock_coordinator):
        """Test sensor has correct device_info."""
        sensor = ChoreControlPendingApprovalsSensor(mock_coordinator)
        device_info = sensor.device_info
        assert device_info["identifiers"] == {(DOMAIN, "chorecontrol")}
        assert device_info["name"] == "ChoreControl"


class TestTotalKidsSensor:
    """Tests for total kids sensor."""

    def test_native_value(self, mock_coordinator):
        """Test sensor returns correct value."""
        sensor = ChoreControlTotalKidsSensor(mock_coordinator)
        assert sensor.native_value == 2

    def test_native_value_no_data(self, mock_coordinator):
        """Test sensor returns 0 when no data."""
        mock_coordinator.data = None
        sensor = ChoreControlTotalKidsSensor(mock_coordinator)
        assert sensor.native_value == 0

    def test_native_value_empty_kids(self, mock_coordinator):
        """Test sensor returns 0 when kids list is empty."""
        mock_coordinator.data = {"kids": []}
        sensor = ChoreControlTotalKidsSensor(mock_coordinator)
        assert sensor.native_value == 0

    def test_unique_id(self, mock_coordinator):
        """Test sensor has correct unique_id."""
        sensor = ChoreControlTotalKidsSensor(mock_coordinator)
        assert sensor.unique_id == f"{DOMAIN}_total_kids"


class TestActiveChoresSensor:
    """Tests for active chores sensor."""

    def test_native_value(self, mock_coordinator):
        """Test sensor returns correct value."""
        sensor = ChoreControlActiveChoresSensor(mock_coordinator)
        assert sensor.native_value == 3

    def test_native_value_no_data(self, mock_coordinator):
        """Test sensor returns 0 when no data."""
        mock_coordinator.data = None
        sensor = ChoreControlActiveChoresSensor(mock_coordinator)
        assert sensor.native_value == 0

    def test_native_value_empty_chores(self, mock_coordinator):
        """Test sensor returns 0 when chores list is empty."""
        mock_coordinator.data = {"chores": []}
        sensor = ChoreControlActiveChoresSensor(mock_coordinator)
        assert sensor.native_value == 0

    def test_unique_id(self, mock_coordinator):
        """Test sensor has correct unique_id."""
        sensor = ChoreControlActiveChoresSensor(mock_coordinator)
        assert sensor.unique_id == f"{DOMAIN}_active_chores"


class TestPointsSensor:
    """Tests for kid points sensor."""

    def test_native_value_emma(self, mock_coordinator):
        """Test sensor returns correct points for Emma."""
        user = {"id": 2, "username": "emma", "role": "kid", "points": 45}
        sensor = ChoreControlPointsSensor(mock_coordinator, user)
        assert sensor.native_value == 45

    def test_native_value_jack(self, mock_coordinator):
        """Test sensor returns correct points for Jack."""
        user = {"id": 3, "username": "jack", "role": "kid", "points": 30}
        sensor = ChoreControlPointsSensor(mock_coordinator, user)
        assert sensor.native_value == 30

    def test_extra_state_attributes(self, mock_coordinator):
        """Test sensor has correct attributes."""
        user = {"id": 2, "username": "emma", "role": "kid", "points": 45}
        sensor = ChoreControlPointsSensor(mock_coordinator, user)
        attrs = sensor.extra_state_attributes
        assert attrs["user_id"] == 2
        assert attrs["username"] == "emma"

    def test_unique_id(self, mock_coordinator):
        """Test sensor has correct unique_id."""
        user = {"id": 2, "username": "emma", "role": "kid", "points": 45}
        sensor = ChoreControlPointsSensor(mock_coordinator, user)
        assert sensor.unique_id == f"{DOMAIN}_emma_points"

    def test_device_info(self, mock_coordinator):
        """Test sensor has correct device_info for kid device."""
        user = {"id": 2, "username": "emma", "role": "kid", "points": 45}
        sensor = ChoreControlPointsSensor(mock_coordinator, user)
        device_info = sensor.device_info
        assert device_info["identifiers"] == {(DOMAIN, "kid_2")}
        assert device_info["name"] == "emma"
        assert device_info["via_device"] == (DOMAIN, "chorecontrol")


class TestPendingChoresSensor:
    """Tests for kid pending chores sensor."""

    def test_native_value_emma(self, mock_coordinator):
        """Test sensor returns correct pending count for Emma."""
        user = {"id": 2, "username": "emma", "role": "kid", "points": 45}
        sensor = ChoreControlPendingChoresSensor(mock_coordinator, user)
        assert sensor.native_value == 1

    def test_native_value_jack(self, mock_coordinator):
        """Test sensor returns correct pending count for Jack."""
        user = {"id": 3, "username": "jack", "role": "kid", "points": 30}
        sensor = ChoreControlPendingChoresSensor(mock_coordinator, user)
        assert sensor.native_value == 0

    def test_extra_state_attributes(self, mock_coordinator):
        """Test sensor has correct attributes."""
        user = {"id": 2, "username": "emma", "role": "kid", "points": 45}
        sensor = ChoreControlPendingChoresSensor(mock_coordinator, user)
        attrs = sensor.extra_state_attributes
        assert attrs["user_id"] == 2
        assert attrs["username"] == "emma"

    def test_unique_id(self, mock_coordinator):
        """Test sensor has correct unique_id."""
        user = {"id": 2, "username": "emma", "role": "kid", "points": 45}
        sensor = ChoreControlPendingChoresSensor(mock_coordinator, user)
        assert sensor.unique_id == f"{DOMAIN}_emma_pending_chores"


class TestClaimedChoresSensor:
    """Tests for kid claimed chores sensor."""

    def test_native_value_emma(self, mock_coordinator):
        """Test sensor returns correct claimed count for Emma."""
        user = {"id": 2, "username": "emma", "role": "kid", "points": 45}
        sensor = ChoreControlClaimedChoresSensor(mock_coordinator, user)
        assert sensor.native_value == 1

    def test_native_value_jack(self, mock_coordinator):
        """Test sensor returns correct claimed count for Jack."""
        user = {"id": 3, "username": "jack", "role": "kid", "points": 30}
        sensor = ChoreControlClaimedChoresSensor(mock_coordinator, user)
        assert sensor.native_value == 0

    def test_extra_state_attributes(self, mock_coordinator):
        """Test sensor has correct attributes."""
        user = {"id": 2, "username": "emma", "role": "kid", "points": 45}
        sensor = ChoreControlClaimedChoresSensor(mock_coordinator, user)
        attrs = sensor.extra_state_attributes
        assert attrs["user_id"] == 2
        assert attrs["username"] == "emma"

    def test_unique_id(self, mock_coordinator):
        """Test sensor has correct unique_id."""
        user = {"id": 2, "username": "emma", "role": "kid", "points": 45}
        sensor = ChoreControlClaimedChoresSensor(mock_coordinator, user)
        assert sensor.unique_id == f"{DOMAIN}_emma_claimed_chores"


class TestCompletedTodaySensor:
    """Tests for kid completed today sensor."""

    def test_native_value_emma(self, mock_coordinator):
        """Test sensor returns correct completed today count for Emma."""
        user = {"id": 2, "username": "emma", "role": "kid", "points": 45}
        sensor = ChoreControlCompletedTodaySensor(mock_coordinator, user)
        assert sensor.native_value == 1

    def test_native_value_jack(self, mock_coordinator):
        """Test sensor returns correct completed today count for Jack."""
        user = {"id": 3, "username": "jack", "role": "kid", "points": 30}
        sensor = ChoreControlCompletedTodaySensor(mock_coordinator, user)
        assert sensor.native_value == 0

    def test_extra_state_attributes(self, mock_coordinator):
        """Test sensor has correct attributes."""
        user = {"id": 2, "username": "emma", "role": "kid", "points": 45}
        sensor = ChoreControlCompletedTodaySensor(mock_coordinator, user)
        attrs = sensor.extra_state_attributes
        assert attrs["user_id"] == 2
        assert attrs["username"] == "emma"

    def test_unique_id(self, mock_coordinator):
        """Test sensor has correct unique_id."""
        user = {"id": 2, "username": "emma", "role": "kid", "points": 45}
        sensor = ChoreControlCompletedTodaySensor(mock_coordinator, user)
        assert sensor.unique_id == f"{DOMAIN}_emma_completed_today"


class TestCompletedThisWeekSensor:
    """Tests for kid completed this week sensor."""

    def test_native_value_emma(self, mock_coordinator):
        """Test sensor returns correct completed this week count for Emma."""
        user = {"id": 2, "username": "emma", "role": "kid", "points": 45}
        sensor = ChoreControlCompletedThisWeekSensor(mock_coordinator, user)
        assert sensor.native_value == 1

    def test_native_value_jack(self, mock_coordinator):
        """Test sensor returns correct completed this week count for Jack."""
        user = {"id": 3, "username": "jack", "role": "kid", "points": 30}
        sensor = ChoreControlCompletedThisWeekSensor(mock_coordinator, user)
        assert sensor.native_value == 0

    def test_extra_state_attributes(self, mock_coordinator):
        """Test sensor has correct attributes."""
        user = {"id": 2, "username": "emma", "role": "kid", "points": 45}
        sensor = ChoreControlCompletedThisWeekSensor(mock_coordinator, user)
        attrs = sensor.extra_state_attributes
        assert attrs["user_id"] == 2
        assert attrs["username"] == "emma"

    def test_unique_id(self, mock_coordinator):
        """Test sensor has correct unique_id."""
        user = {"id": 2, "username": "emma", "role": "kid", "points": 45}
        sensor = ChoreControlCompletedThisWeekSensor(mock_coordinator, user)
        assert sensor.unique_id == f"{DOMAIN}_emma_completed_this_week"

    def test_device_info(self, mock_coordinator):
        """Test sensor has correct device_info for kid device."""
        user = {"id": 2, "username": "emma", "role": "kid", "points": 45}
        sensor = ChoreControlCompletedThisWeekSensor(mock_coordinator, user)
        device_info = sensor.device_info
        assert device_info["identifiers"] == {(DOMAIN, "kid_2")}
        assert device_info["name"] == "emma"
        assert device_info["model"] == "Kid"


class TestUnknownUserStats:
    """Tests for handling unknown user IDs."""

    def test_unknown_user_returns_defaults(self, mock_coordinator):
        """Test that unknown user IDs return default stats."""
        user = {"id": 999, "username": "unknown", "role": "kid", "points": 0}
        sensor = ChoreControlPointsSensor(mock_coordinator, user)
        # The mock_coordinator.get_kid_stats returns defaults for unknown users
        assert sensor.native_value == 0
