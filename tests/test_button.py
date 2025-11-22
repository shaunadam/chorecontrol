"""Tests for ChoreControl button entities."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from custom_components.chorecontrol.button import ChoreControlClaimButton
from custom_components.chorecontrol.const import DOMAIN


class TestClaimButton:
    """Tests for claim button entity."""

    def test_button_creation_with_individual_chore(self, mock_coordinator):
        """Test button is created correctly for individual chore."""
        instance = {
            "instance_id": 1,
            "chore_name": "Take out trash",
            "chore_id": 1,
            "due_date": "2025-01-15",
            "points": 5,
            "assigned_to": 2,
            "assignment_type": "individual",
        }
        button = ChoreControlClaimButton(mock_coordinator, instance, 2, "emma")

        assert button.instance_id == 1
        assert button.chore_name == "Take out trash"
        assert button.user_id == 2
        assert button.username == "emma"
        assert button.points == 5

    def test_button_unique_id(self, mock_coordinator):
        """Test button has correct unique ID."""
        instance = {
            "instance_id": 42,
            "chore_name": "Test chore",
            "chore_id": 1,
            "points": 5,
            "assigned_to": 3,
            "assignment_type": "individual",
        }
        button = ChoreControlClaimButton(mock_coordinator, instance, 3, "jack")

        assert button._attr_unique_id == f"{DOMAIN}_claim_42_3"

    def test_button_name(self, mock_coordinator):
        """Test button has correct name format."""
        instance = {
            "instance_id": 1,
            "chore_name": "Make bed",
            "chore_id": 2,
            "points": 3,
            "assigned_to": 2,
            "assignment_type": "individual",
        }
        button = ChoreControlClaimButton(mock_coordinator, instance, 2, "emma")

        assert button._attr_name == "Claim Make bed (emma)"

    def test_button_icon(self, mock_coordinator):
        """Test button has correct icon."""
        instance = {
            "instance_id": 1,
            "chore_name": "Test",
            "chore_id": 1,
            "points": 5,
            "assigned_to": 2,
            "assignment_type": "individual",
        }
        button = ChoreControlClaimButton(mock_coordinator, instance, 2, "emma")

        assert button._attr_icon == "mdi:checkbox-marked-circle-outline"

    @pytest.mark.asyncio
    async def test_button_press_claims_chore(self, mock_coordinator):
        """Test button press calls claim_chore API method."""
        instance = {
            "instance_id": 42,
            "chore_name": "Test chore",
            "chore_id": 1,
            "points": 5,
            "assigned_to": 2,
            "assignment_type": "individual",
        }
        button = ChoreControlClaimButton(mock_coordinator, instance, 2, "emma")

        await button.async_press()

        mock_coordinator.api_client.claim_chore.assert_called_once_with(42, 2)
        mock_coordinator.async_request_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_button_press_refreshes_data(self, mock_coordinator):
        """Test button press triggers coordinator refresh."""
        instance = {
            "instance_id": 1,
            "chore_name": "Test",
            "chore_id": 1,
            "points": 5,
            "assigned_to": 3,
            "assignment_type": "individual",
        }
        button = ChoreControlClaimButton(mock_coordinator, instance, 3, "jack")

        await button.async_press()

        mock_coordinator.async_request_refresh.assert_called_once()

    def test_extra_state_attributes(self, mock_coordinator):
        """Test button has correct extra state attributes."""
        instance = {
            "instance_id": 10,
            "chore_name": "Feed dog",
            "chore_id": 3,
            "points": 4,
            "assigned_to": None,
            "assignment_type": "shared",
        }
        button = ChoreControlClaimButton(mock_coordinator, instance, 2, "emma")
        attrs = button.extra_state_attributes

        assert attrs["instance_id"] == 10
        assert attrs["chore_name"] == "Feed dog"
        assert attrs["user_id"] == 2
        assert attrs["username"] == "emma"
        assert attrs["points"] == 4

    def test_device_info(self, mock_coordinator):
        """Test button has correct device info for kid device."""
        instance = {
            "instance_id": 1,
            "chore_name": "Test",
            "chore_id": 1,
            "points": 5,
            "assigned_to": 2,
            "assignment_type": "individual",
        }
        button = ChoreControlClaimButton(mock_coordinator, instance, 2, "emma")
        device_info = button.device_info

        assert "identifiers" in device_info
        assert (DOMAIN, "kid_2") in device_info["identifiers"]
        assert device_info["name"] == "emma"
        assert device_info["manufacturer"] == "ChoreControl"
        assert device_info["model"] == "Kid"
        assert device_info["via_device"] == (DOMAIN, "chorecontrol")

    def test_button_with_missing_points(self, mock_coordinator):
        """Test button handles missing points gracefully."""
        instance = {
            "instance_id": 1,
            "chore_name": "Test",
            "chore_id": 1,
            "assigned_to": 2,
            "assignment_type": "individual",
            # points not provided
        }
        button = ChoreControlClaimButton(mock_coordinator, instance, 2, "emma")

        assert button.points == 0

    def test_has_entity_name(self, mock_coordinator):
        """Test button has entity name enabled."""
        instance = {
            "instance_id": 1,
            "chore_name": "Test",
            "chore_id": 1,
            "points": 5,
            "assigned_to": 2,
            "assignment_type": "individual",
        }
        button = ChoreControlClaimButton(mock_coordinator, instance, 2, "emma")

        assert button._attr_has_entity_name is True


class TestButtonCreationLogic:
    """Tests for button creation/removal logic."""

    def test_claimable_instances_fixture_has_individual_chore(self, mock_coordinator):
        """Test fixture includes individual chore instance."""
        claimable = mock_coordinator.data["claimable_instances"]

        individual_chores = [
            c for c in claimable if c["assignment_type"] == "individual"
        ]
        assert len(individual_chores) >= 1

        # Check individual chore has assigned_to set
        individual = individual_chores[0]
        assert individual["assigned_to"] is not None

    def test_claimable_instances_fixture_has_shared_chore(self, mock_coordinator):
        """Test fixture includes shared chore instance."""
        claimable = mock_coordinator.data["claimable_instances"]

        shared_chores = [
            c for c in claimable if c["assignment_type"] == "shared"
        ]
        assert len(shared_chores) >= 1

        # Check shared chore has no assigned_to
        shared = shared_chores[0]
        assert shared["assigned_to"] is None

    def test_coordinator_has_kids_data(self, mock_coordinator):
        """Test coordinator has kids data for shared chore buttons."""
        kids = mock_coordinator.data["kids"]

        assert len(kids) >= 2
        assert all("id" in kid for kid in kids)
        assert all("username" in kid for kid in kids)

    def test_get_user_by_id_returns_user(self, mock_coordinator):
        """Test get_user_by_id returns correct user."""
        user = mock_coordinator.get_user_by_id(2)

        assert user is not None
        assert user["username"] == "emma"
        assert user["role"] == "kid"

    def test_get_user_by_id_returns_none_for_missing(self, mock_coordinator):
        """Test get_user_by_id returns None for unknown user."""
        user = mock_coordinator.get_user_by_id(999)

        assert user is None
