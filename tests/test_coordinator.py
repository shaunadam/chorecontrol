"""Tests for ChoreControl coordinator."""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.chorecontrol.coordinator import ChoreControlDataUpdateCoordinator


@pytest.fixture
def coordinator_setup(mock_api_client):
    """Return a coordinator for testing."""
    hass = MagicMock()
    coordinator = ChoreControlDataUpdateCoordinator(
        hass,
        mock_api_client,
        scan_interval=30,
    )
    return coordinator


class TestAsyncUpdateData:
    """Tests for _async_update_data method."""

    @pytest.mark.asyncio
    async def test_update_data_success(self, coordinator_setup, mock_api_client):
        """Test successful data update."""
        coordinator = coordinator_setup

        result = await coordinator._async_update_data()

        assert result["api_connected"] is True
        assert "users" in result
        assert "kids" in result
        assert "chores" in result
        assert "instances" in result
        assert "rewards" in result
        assert "pending_approvals_count" in result
        assert "instances_by_user" in result
        assert "claimable_instances" in result

    @pytest.mark.asyncio
    async def test_update_data_api_down(self, coordinator_setup, mock_api_client):
        """Test data update when API is down."""
        coordinator = coordinator_setup
        mock_api_client.check_health.return_value = False

        result = await coordinator._async_update_data()

        assert result["api_connected"] is False
        assert result["users"] == []
        assert result["kids"] == []
        assert result["pending_approvals_count"] == 0

    @pytest.mark.asyncio
    async def test_kids_extraction(self, coordinator_setup, mock_api_client):
        """Test that kids are correctly extracted from users."""
        coordinator = coordinator_setup

        result = await coordinator._async_update_data()

        # Should have 2 kids (emma and jack)
        assert len(result["kids"]) == 2
        usernames = [k["username"] for k in result["kids"]]
        assert "emma" in usernames
        assert "jack" in usernames
        assert "parent1" not in usernames

    @pytest.mark.asyncio
    async def test_pending_approvals_count(self, coordinator_setup, mock_api_client):
        """Test pending approvals count calculation."""
        coordinator = coordinator_setup

        result = await coordinator._async_update_data()

        # One instance has status 'claimed'
        assert result["pending_approvals_count"] == 1


class TestBuildInstancesByUser:
    """Tests for _build_instances_by_user method."""

    @pytest.mark.asyncio
    async def test_instances_by_user_structure(self, coordinator_setup, mock_api_client):
        """Test instances_by_user has correct structure."""
        coordinator = coordinator_setup

        result = await coordinator._async_update_data()
        instances_by_user = result["instances_by_user"]

        # Should have entries for both kids
        assert 2 in instances_by_user
        assert 3 in instances_by_user

        # Each entry should have the expected keys
        for user_id in [2, 3]:
            assert "assigned" in instances_by_user[user_id]
            assert "claimed" in instances_by_user[user_id]
            assert "approved_today" in instances_by_user[user_id]
            assert "approved_this_week" in instances_by_user[user_id]

    @pytest.mark.asyncio
    async def test_assigned_instances(self, coordinator_setup, mock_api_client):
        """Test assigned instances are correctly categorized."""
        coordinator = coordinator_setup

        result = await coordinator._async_update_data()
        instances_by_user = result["instances_by_user"]

        # Emma (id=2) should have 1 assigned instance
        assert len(instances_by_user[2]["assigned"]) == 1
        assert instances_by_user[2]["assigned"][0]["id"] == 1

    @pytest.mark.asyncio
    async def test_claimed_instances(self, coordinator_setup, mock_api_client):
        """Test claimed instances are correctly categorized."""
        coordinator = coordinator_setup

        result = await coordinator._async_update_data()
        instances_by_user = result["instances_by_user"]

        # Emma (id=2) should have 1 claimed instance
        assert len(instances_by_user[2]["claimed"]) == 1
        assert instances_by_user[2]["claimed"][0]["id"] == 2

    @pytest.mark.asyncio
    async def test_approved_today(self, coordinator_setup, mock_api_client):
        """Test approved_today instances are correctly categorized."""
        coordinator = coordinator_setup

        result = await coordinator._async_update_data()
        instances_by_user = result["instances_by_user"]

        # Emma (id=2) should have 1 approved today (instance 4)
        assert len(instances_by_user[2]["approved_today"]) == 1
        assert instances_by_user[2]["approved_today"][0]["id"] == 4

    @pytest.mark.asyncio
    async def test_approved_this_week(self, coordinator_setup, mock_api_client):
        """Test approved_this_week instances are correctly categorized."""
        coordinator = coordinator_setup

        result = await coordinator._async_update_data()
        instances_by_user = result["instances_by_user"]

        # Emma should have at least 1 approved this week
        assert len(instances_by_user[2]["approved_this_week"]) >= 1


class TestBuildClaimableInstances:
    """Tests for _build_claimable_instances method."""

    @pytest.mark.asyncio
    async def test_claimable_instances(self, coordinator_setup, mock_api_client):
        """Test claimable instances are correctly built."""
        coordinator = coordinator_setup

        result = await coordinator._async_update_data()
        claimable = result["claimable_instances"]

        # Should have 2 claimable instances (id 1 and 3)
        assert len(claimable) == 2
        instance_ids = [c["instance_id"] for c in claimable]
        assert 1 in instance_ids
        assert 3 in instance_ids

    @pytest.mark.asyncio
    async def test_claimable_instance_structure(self, coordinator_setup, mock_api_client):
        """Test claimable instance has correct structure."""
        coordinator = coordinator_setup

        result = await coordinator._async_update_data()
        claimable = result["claimable_instances"]

        # Check first instance has all required fields
        inst = claimable[0]
        assert "instance_id" in inst
        assert "chore_name" in inst
        assert "chore_id" in inst
        assert "due_date" in inst
        assert "points" in inst
        assert "assigned_to" in inst
        assert "assignment_type" in inst

    @pytest.mark.asyncio
    async def test_individual_vs_shared(self, coordinator_setup, mock_api_client):
        """Test individual and shared assignments are identified."""
        coordinator = coordinator_setup

        result = await coordinator._async_update_data()
        claimable = result["claimable_instances"]

        individual = [c for c in claimable if c["assignment_type"] == "individual"]
        shared = [c for c in claimable if c["assignment_type"] == "shared"]

        assert len(individual) >= 1
        assert len(shared) >= 1


class TestHelperMethods:
    """Tests for coordinator helper methods."""

    @pytest.mark.asyncio
    async def test_get_user_by_id_found(self, coordinator_setup, mock_api_client):
        """Test get_user_by_id when user exists."""
        coordinator = coordinator_setup
        coordinator.data = await coordinator._async_update_data()

        user = coordinator.get_user_by_id(2)

        assert user is not None
        assert user["id"] == 2
        assert user["username"] == "emma"

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, coordinator_setup, mock_api_client):
        """Test get_user_by_id when user doesn't exist."""
        coordinator = coordinator_setup
        coordinator.data = await coordinator._async_update_data()

        user = coordinator.get_user_by_id(999)

        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_id_no_data(self, coordinator_setup):
        """Test get_user_by_id when no data loaded."""
        coordinator = coordinator_setup
        coordinator.data = None

        user = coordinator.get_user_by_id(2)

        assert user is None

    @pytest.mark.asyncio
    async def test_get_kid_stats_found(self, coordinator_setup, mock_api_client):
        """Test get_kid_stats for existing kid."""
        coordinator = coordinator_setup
        coordinator.data = await coordinator._async_update_data()

        stats = coordinator.get_kid_stats(2)

        assert stats["points"] == 45
        assert stats["pending_count"] == 1
        assert stats["claimed_count"] == 1
        assert stats["completed_today"] == 1
        assert stats["completed_this_week"] >= 1

    @pytest.mark.asyncio
    async def test_get_kid_stats_no_data(self, coordinator_setup):
        """Test get_kid_stats when no data loaded."""
        coordinator = coordinator_setup
        coordinator.data = None

        stats = coordinator.get_kid_stats(2)

        assert stats["points"] == 0
        assert stats["pending_count"] == 0
        assert stats["claimed_count"] == 0
        assert stats["completed_today"] == 0
        assert stats["completed_this_week"] == 0

    @pytest.mark.asyncio
    async def test_get_kid_stats_user_not_found(self, coordinator_setup, mock_api_client):
        """Test get_kid_stats for non-existent user."""
        coordinator = coordinator_setup
        coordinator.data = await coordinator._async_update_data()

        stats = coordinator.get_kid_stats(999)

        assert stats["points"] == 0

    @pytest.mark.asyncio
    async def test_get_claimable_for_user_individual(self, coordinator_setup, mock_api_client):
        """Test get_claimable_for_user for individual chores."""
        coordinator = coordinator_setup
        coordinator.data = await coordinator._async_update_data()

        # Emma (id=2) should see the individual chore assigned to her
        claimable = coordinator.get_claimable_for_user(2)

        individual_ids = [
            c["instance_id"]
            for c in claimable
            if c["assignment_type"] == "individual"
        ]
        assert 1 in individual_ids  # Take out trash is assigned to emma

    @pytest.mark.asyncio
    async def test_get_claimable_for_user_shared(self, coordinator_setup, mock_api_client):
        """Test get_claimable_for_user includes shared chores."""
        coordinator = coordinator_setup
        coordinator.data = await coordinator._async_update_data()

        # Both kids should see the shared chore
        emma_claimable = coordinator.get_claimable_for_user(2)
        jack_claimable = coordinator.get_claimable_for_user(3)

        emma_shared = [c for c in emma_claimable if c["assignment_type"] == "shared"]
        jack_shared = [c for c in jack_claimable if c["assignment_type"] == "shared"]

        assert len(emma_shared) >= 1
        assert len(jack_shared) >= 1

    @pytest.mark.asyncio
    async def test_get_claimable_for_user_no_data(self, coordinator_setup):
        """Test get_claimable_for_user when no data loaded."""
        coordinator = coordinator_setup
        coordinator.data = None

        claimable = coordinator.get_claimable_for_user(2)

        assert claimable == []


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_empty_users(self, coordinator_setup, mock_api_client):
        """Test handling of empty users list."""
        coordinator = coordinator_setup
        mock_api_client.get_users.return_value = []

        result = await coordinator._async_update_data()

        assert result["kids"] == []
        assert result["instances_by_user"] == {}

    @pytest.mark.asyncio
    async def test_empty_instances(self, coordinator_setup, mock_api_client):
        """Test handling of empty instances list."""
        coordinator = coordinator_setup
        mock_api_client.get_instances.return_value = []

        result = await coordinator._async_update_data()

        assert result["pending_approvals_count"] == 0
        assert result["claimable_instances"] == []

    @pytest.mark.asyncio
    async def test_malformed_approved_at(self, coordinator_setup, mock_api_client):
        """Test handling of malformed approved_at date."""
        coordinator = coordinator_setup

        # Add an instance with malformed date
        mock_api_client.get_instances.return_value.append({
            "id": 5,
            "chore_id": 1,
            "status": "approved",
            "assigned_to": 2,
            "claimed_by": 2,
            "approved_at": "invalid-date",
            "chore": {"name": "Test", "points": 1, "assignment_type": "individual"},
        })

        # Should not raise an exception
        result = await coordinator._async_update_data()

        assert result["api_connected"] is True
