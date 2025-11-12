"""
Unit and integration tests for REST API endpoints.

Tests for:
- User endpoints
- Chore endpoints
- Chore instance endpoints
- Reward endpoints
- Points endpoints
- Calendar endpoints
- Dashboard endpoints
"""

import pytest


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    @pytest.mark.unit
    def test_health_check(self, client):
        """
        Test the /health endpoint.

        TODO: Implement once Flask app and health endpoint are ready

        Should test:
        - Endpoint returns 200 OK
        - Response contains expected health status
        - Database connectivity is checked
        """
        pytest.skip("Health endpoint not yet implemented")


class TestUserEndpoints:
    """Tests for /api/users endpoints."""

    @pytest.mark.integration
    def test_list_users(self, client, auth_headers):
        """
        Test GET /api/users.

        TODO: Implement once user endpoints are ready

        Should test:
        - Returns list of all users
        - Response format is correct
        - Authentication is required
        """
        pytest.skip("User endpoints not yet implemented")

    @pytest.mark.integration
    def test_create_user(self, client, parent_headers):
        """
        Test POST /api/users.

        TODO: Implement once user endpoints are ready

        Should test:
        - User can be created with valid data
        - Validation works for required fields
        - Only parents can create users
        """
        pytest.skip("User endpoints not yet implemented")

    @pytest.mark.integration
    def test_get_user(self, client, auth_headers, sample_user):
        """
        Test GET /api/users/{id}.

        TODO: Implement once user endpoints are ready

        Should test:
        - User details are returned
        - 404 for non-existent user
        """
        pytest.skip("User endpoints not yet implemented")

    @pytest.mark.integration
    def test_update_user(self, client, parent_headers, sample_user):
        """
        Test PUT /api/users/{id}.

        TODO: Implement once user endpoints are ready

        Should test:
        - User can be updated
        - Validation works
        - Authorization is enforced
        """
        pytest.skip("User endpoints not yet implemented")


class TestChoreEndpoints:
    """Tests for /api/chores endpoints."""

    @pytest.mark.integration
    def test_list_chores(self, client, auth_headers):
        """
        Test GET /api/chores.

        TODO: Implement once chore endpoints are ready

        Should test:
        - Returns list of active chores
        - Filtering by assignment works
        - Response format is correct
        """
        pytest.skip("Chore endpoints not yet implemented")

    @pytest.mark.integration
    def test_create_chore(self, client, parent_headers):
        """
        Test POST /api/chores.

        TODO: Implement once chore endpoints are ready

        Should test:
        - Chore can be created with valid data
        - Recurrence pattern validation works
        - Only parents can create chores
        """
        pytest.skip("Chore endpoints not yet implemented")

    @pytest.mark.integration
    def test_get_chore(self, client, auth_headers, sample_chore):
        """
        Test GET /api/chores/{id}.

        TODO: Implement once chore endpoints are ready

        Should test:
        - Chore details are returned
        - 404 for non-existent chore
        """
        pytest.skip("Chore endpoints not yet implemented")

    @pytest.mark.integration
    def test_update_chore(self, client, parent_headers, sample_chore):
        """
        Test PUT /api/chores/{id}.

        TODO: Implement once chore endpoints are ready

        Should test:
        - Chore can be updated
        - Validation works
        - Authorization is enforced
        """
        pytest.skip("Chore endpoints not yet implemented")

    @pytest.mark.integration
    def test_delete_chore(self, client, parent_headers, sample_chore):
        """
        Test DELETE /api/chores/{id}.

        TODO: Implement once chore endpoints are ready

        Should test:
        - Chore is soft-deleted (is_active = False)
        - Not actually removed from database
        - Authorization is enforced
        """
        pytest.skip("Chore endpoints not yet implemented")


class TestChoreInstanceEndpoints:
    """Tests for /api/instances endpoints."""

    @pytest.mark.integration
    def test_list_instances(self, client, auth_headers):
        """
        Test GET /api/instances.

        TODO: Implement once instance endpoints are ready

        Should test:
        - Returns list of chore instances
        - Filtering by status works
        - Filtering by user works
        - Date range filtering works
        """
        pytest.skip("Instance endpoints not yet implemented")

    @pytest.mark.integration
    def test_claim_instance(self, client, kid_headers):
        """
        Test POST /api/instances/{id}/claim.

        TODO: Implement once instance endpoints are ready

        Should test:
        - Kid can claim assigned chore
        - Status changes to 'claimed'
        - Timestamps are set correctly
        - Notification is triggered
        """
        pytest.skip("Instance endpoints not yet implemented")

    @pytest.mark.integration
    def test_approve_instance(self, client, parent_headers):
        """
        Test POST /api/instances/{id}/approve.

        TODO: Implement once instance endpoints are ready

        Should test:
        - Parent can approve claimed chore
        - Points are awarded
        - Status changes to 'approved'
        - Notification is triggered
        """
        pytest.skip("Instance endpoints not yet implemented")

    @pytest.mark.integration
    def test_reject_instance(self, client, parent_headers):
        """
        Test POST /api/instances/{id}/reject.

        TODO: Implement once instance endpoints are ready

        Should test:
        - Parent can reject claimed chore
        - Rejection reason is stored
        - Status changes to 'rejected'
        - No points awarded
        - Notification is triggered
        """
        pytest.skip("Instance endpoints not yet implemented")


class TestRewardEndpoints:
    """Tests for /api/rewards endpoints."""

    @pytest.mark.integration
    def test_list_rewards(self, client, auth_headers):
        """
        Test GET /api/rewards.

        TODO: Implement once reward endpoints are ready

        Should test:
        - Returns list of active rewards
        - Response format is correct
        """
        pytest.skip("Reward endpoints not yet implemented")

    @pytest.mark.integration
    def test_create_reward(self, client, parent_headers):
        """
        Test POST /api/rewards.

        TODO: Implement once reward endpoints are ready

        Should test:
        - Reward can be created
        - Validation works
        - Only parents can create rewards
        """
        pytest.skip("Reward endpoints not yet implemented")

    @pytest.mark.integration
    def test_claim_reward(self, client, kid_headers):
        """
        Test POST /api/rewards/{id}/claim.

        TODO: Implement once reward endpoints are ready

        Should test:
        - Kid can claim reward if enough points
        - Points are deducted
        - Cooldown is enforced
        - Claim limits are enforced
        - Notification is triggered
        """
        pytest.skip("Reward endpoints not yet implemented")


class TestPointsEndpoints:
    """Tests for /api/points endpoints."""

    @pytest.mark.integration
    def test_adjust_points(self, client, parent_headers):
        """
        Test POST /api/points/adjust.

        TODO: Implement once points endpoints are ready

        Should test:
        - Parent can adjust points manually
        - Positive and negative adjustments work
        - Points history is recorded
        - Only parents can adjust points
        """
        pytest.skip("Points endpoints not yet implemented")

    @pytest.mark.integration
    def test_points_history(self, client, auth_headers, sample_user):
        """
        Test GET /api/points/history/{user_id}.

        TODO: Implement once points endpoints are ready

        Should test:
        - Returns points history for user
        - History includes all transactions
        - Sorted by date (newest first)
        """
        pytest.skip("Points endpoints not yet implemented")


class TestCalendarEndpoints:
    """Tests for /api/calendar endpoints."""

    @pytest.mark.integration
    def test_calendar_ics_generation(self, client, sample_user):
        """
        Test GET /api/calendar/{user_id}.ics.

        TODO: Implement once calendar endpoint is ready

        Should test:
        - ICS feed is generated
        - Content-Type is text/calendar
        - Valid ICS format
        - Includes upcoming chores (next 30 days)
        """
        pytest.skip("Calendar endpoint not yet implemented")


class TestDashboardEndpoints:
    """Tests for /api/dashboard endpoints."""

    @pytest.mark.integration
    def test_kid_dashboard(self, client, kid_headers):
        """
        Test GET /api/dashboard/kid/{user_id}.

        TODO: Implement once dashboard endpoint is ready

        Should test:
        - Returns kid's dashboard data
        - Includes points balance
        - Includes assigned chores
        - Includes available rewards
        """
        pytest.skip("Dashboard endpoint not yet implemented")

    @pytest.mark.integration
    def test_parent_dashboard(self, client, parent_headers):
        """
        Test GET /api/dashboard/parent.

        TODO: Implement once dashboard endpoint is ready

        Should test:
        - Returns parent dashboard data
        - Includes pending approvals
        - Includes recent activity
        - Includes kids overview
        """
        pytest.skip("Dashboard endpoint not yet implemented")


# More test scenarios to add:
# - Test authentication/authorization for all endpoints
# - Test input validation and error responses
# - Test pagination for list endpoints
# - Test concurrent request handling
# - Test rate limiting (if implemented)
