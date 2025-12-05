"""Tests for role-based access control."""

import pytest
from models import User


class TestUIAccessControl:
    """Tests for UI route access control (parent and claim_only)."""

    def test_parent_can_access_dashboard(self, client, parent_headers):
        """Test that parents can access the dashboard."""
        response = client.get('/', headers=parent_headers)
        assert response.status_code == 200

    def test_claim_only_redirected_from_dashboard_to_today(self, client, claim_only_headers):
        """Test that claim_only users are redirected from dashboard to today page."""
        response = client.get('/', headers=claim_only_headers, follow_redirects=False)
        assert response.status_code == 302
        assert '/today' in response.location

    def test_claim_only_can_access_today_page(self, client, claim_only_headers):
        """Test that claim_only users can access the today page."""
        response = client.get('/today', headers=claim_only_headers)
        assert response.status_code == 200
        assert b'Today' in response.data

    def test_kid_redirected_from_dashboard(self, client, kid_headers):
        """Test that kids are redirected to access_restricted page."""
        response = client.get('/', headers=kid_headers)

        assert response.status_code == 403
        assert b'Kids use the Home Assistant integration' in response.data
        assert b'Kid User' in response.data  # Should show role badge

    def test_unmapped_redirected_from_dashboard(self, client, unmapped_headers):
        """Test that unmapped users see mapping instructions."""
        response = client.get('/', headers=unmapped_headers)

        assert response.status_code == 403
        assert b'Account Needs Mapping' in response.data
        assert b'unmapped' in response.data.lower()

    def test_parent_can_access_chores_list(self, client, parent_headers):
        """Test that parents can access chores list."""
        response = client.get('/chores', headers=parent_headers)
        assert response.status_code == 200

    def test_claim_only_redirected_from_chores_to_today(self, client, claim_only_headers):
        """Test that claim_only users are redirected from chores to today."""
        response = client.get('/chores', headers=claim_only_headers, follow_redirects=False)
        assert response.status_code == 302
        assert '/today' in response.location

    def test_kid_cannot_access_chores_list(self, client, kid_headers):
        """Test that kids cannot access chores UI."""
        response = client.get('/chores', headers=kid_headers)
        assert response.status_code == 403

    def test_parent_can_access_users_list(self, client, parent_headers):
        """Test that parents can access users list."""
        response = client.get('/users', headers=parent_headers)
        assert response.status_code == 200

    def test_kid_cannot_access_users_list(self, client, kid_headers):
        """Test that kids cannot access users UI."""
        response = client.get('/users', headers=kid_headers)
        assert response.status_code == 403

    def test_parent_can_access_rewards_list(self, client, parent_headers):
        """Test that parents can access rewards list."""
        response = client.get('/rewards', headers=parent_headers)
        assert response.status_code == 200

    def test_kid_cannot_access_rewards_list(self, client, kid_headers):
        """Test that kids cannot access rewards UI."""
        response = client.get('/rewards', headers=kid_headers)
        assert response.status_code == 403

    def test_parent_can_access_approval_queue(self, client, parent_headers):
        """Test that parents can access approval queue."""
        response = client.get('/approvals', headers=parent_headers)
        assert response.status_code == 200

    def test_kid_cannot_access_approval_queue(self, client, kid_headers):
        """Test that kids cannot access approval queue."""
        response = client.get('/approvals', headers=kid_headers)
        assert response.status_code == 403

    def test_parent_can_access_calendar(self, client, parent_headers):
        """Test that parents can access calendar."""
        response = client.get('/calendar', headers=parent_headers)
        assert response.status_code == 200

    def test_kid_cannot_access_calendar(self, client, kid_headers):
        """Test that kids cannot access calendar."""
        response = client.get('/calendar', headers=kid_headers)
        assert response.status_code == 403

    def test_unmapped_cannot_access_any_ui_route(self, client, unmapped_headers):
        """Test that unmapped users cannot access any UI routes."""
        ui_routes = ['/', '/chores', '/users', '/rewards', '/approvals', '/calendar', '/today']

        for route in ui_routes:
            response = client.get(route, headers=unmapped_headers)
            assert response.status_code == 403, f"Route {route} should deny unmapped users"

    def test_claim_only_redirected_from_all_routes_except_today(self, client, claim_only_headers):
        """Test that claim_only users are redirected to /today from all other routes."""
        restricted_routes = ['/', '/chores', '/users', '/rewards', '/approvals', '/calendar', '/available', '/settings']

        for route in restricted_routes:
            response = client.get(route, headers=claim_only_headers, follow_redirects=False)
            assert response.status_code == 302, f"Route {route} should redirect claim_only users"
            assert '/today' in response.location, f"Route {route} should redirect to /today"


class TestAPIAccessControl:
    """Tests for API route access control (all authenticated users)."""

    def test_parent_can_access_api_users(self, client, parent_headers):
        """Test that parents can access API endpoints."""
        response = client.get('/api/users', headers=parent_headers)
        assert response.status_code == 200

    def test_kid_can_access_api_users(self, client, kid_headers):
        """Test that kids can access API endpoints (needed for HA integration)."""
        response = client.get('/api/users', headers=kid_headers)
        assert response.status_code == 200

    def test_claim_only_can_access_api(self, client, claim_only_headers):
        """Test that claim_only users can access API endpoints (for claiming chores)."""
        response = client.get('/api/users', headers=claim_only_headers)
        assert response.status_code == 200

    def test_unmapped_can_access_api_users(self, client, unmapped_headers):
        """Test that even unmapped users can access API (though actions may be restricted)."""
        response = client.get('/api/users', headers=unmapped_headers)
        assert response.status_code == 200

    def test_kid_can_access_api_instances(self, client, kid_headers):
        """Test that kids can access instances API (for claiming chores)."""
        response = client.get('/api/instances', headers=kid_headers)
        assert response.status_code == 200

    def test_kid_can_access_api_rewards(self, client, kid_headers):
        """Test that kids can access rewards API (for claiming rewards)."""
        response = client.get('/api/rewards', headers=kid_headers)
        assert response.status_code == 200

    def test_unauthenticated_cannot_access_api(self, client):
        """Test that unauthenticated requests are denied."""
        response = client.get('/api/users')  # No headers
        assert response.status_code == 401


class TestAccessRestrictedPage:
    """Tests for the access_restricted.html template content."""

    def test_kid_sees_points_on_restricted_page(self, client, kid_user, kid_headers):
        """Test that kids see their current points on the restricted page."""
        response = client.get('/', headers=kid_headers)

        assert response.status_code == 403
        assert b'50' in response.data  # Kid has 50 points from fixture
        assert b'Current Points:' in response.data

    def test_kid_sees_ha_integration_instructions(self, client, kid_headers):
        """Test that kids see instructions to use HA integration."""
        response = client.get('/', headers=kid_headers)

        assert b'Claim chores' in response.data
        assert b'Home Assistant dashboard' in response.data
        assert b'View your points' in response.data

    def test_unmapped_sees_mapping_instructions(self, client, unmapped_headers):
        """Test that unmapped users see instructions for getting mapped."""
        response = client.get('/', headers=unmapped_headers)

        assert b'A parent user needs to log in' in response.data
        assert b'User Mapping' in response.data
        assert b'Unmapped User' in response.data  # Shows role badge

    def test_unmapped_sees_ha_user_id(self, client, unmapped_user, unmapped_headers):
        """Test that unmapped users see their HA User ID for troubleshooting."""
        response = client.get('/', headers=unmapped_headers)

        assert unmapped_user.ha_user_id.encode() in response.data
        assert b'HA User ID:' in response.data

    def test_restricted_page_has_logout_button(self, client, kid_headers):
        """Test that restricted page includes logout button."""
        response = client.get('/', headers=kid_headers)

        assert b'Logout' in response.data
        assert b'/logout' in response.data


class TestParentRequiredDecorator:
    """Tests for @parent_required decorator on specific routes."""

    def test_user_mapping_requires_parent(self, client, kid_headers, unmapped_headers):
        """Test that user mapping page requires parent role."""
        # Kid should be denied
        response = client.get('/users/mapping', headers=kid_headers)
        assert response.status_code == 403

        # Unmapped should be denied
        response = client.get('/users/mapping', headers=unmapped_headers)
        assert response.status_code == 403

    def test_user_mapping_update_requires_parent(self, client, kid_headers):
        """Test that user mapping update requires parent role."""
        response = client.post('/users/mapping/update',
                             headers=kid_headers,
                             data={'role_1': 'parent'})
        assert response.status_code == 403

    def test_parent_can_update_mappings(self, client, parent_headers):
        """Test that parents can update user mappings."""
        response = client.post('/users/mapping/update',
                             headers=parent_headers,
                             data={},
                             follow_redirects=True)
        assert response.status_code == 200


class TestUnauthenticatedAccess:
    """Tests for unauthenticated access attempts."""

    def test_unauthenticated_redirected_to_login_ui(self, client):
        """Test that unauthenticated UI requests redirect to login."""
        response = client.get('/')

        # Should redirect to login (no X-Ingress-User header means unauthorized)
        # 401 because user doesn't exist in DB (no header means no user)
        assert response.status_code in [302, 401]
        if response.status_code == 302:
            assert '/login' in response.location

    def test_unauthenticated_denied_api_access(self, client):
        """Test that unauthenticated API requests get 401."""
        response = client.get('/api/users')

        assert response.status_code == 401
        data = response.get_json()
        assert data['error'] == 'Unauthorized'

    def test_unauthenticated_cannot_access_mapping(self, client):
        """Test that unauthenticated requests cannot access mapping."""
        response = client.get('/users/mapping')

        # Should redirect to login or return 401
        assert response.status_code in [302, 401]
        if response.status_code == 302:
            assert '/login' in response.location


class TestRoleBasedUIElements:
    """Tests for role-based UI element visibility."""

    def test_parent_sees_navigation(self, client, parent_headers):
        """Test that parents see full navigation."""
        response = client.get('/', headers=parent_headers)

        assert b'Dashboard' in response.data
        assert b'Chores' in response.data
        assert b'Rewards' in response.data
        assert b'Users' in response.data

    def test_parent_sees_user_mapping_link(self, client, parent_headers):
        """Test that parents see User Mapping nav link."""
        response = client.get('/', headers=parent_headers)

        assert b'User Mapping' in response.data
        assert b'/users/mapping' in response.data

    def test_claim_only_sees_only_today_tab(self, client, claim_only_headers):
        """Test that claim_only users see only the Today tab in navigation."""
        response = client.get('/today', headers=claim_only_headers)

        # Should see Today tab
        assert b'Today' in response.data

        # Should NOT see other navigation tabs
        assert b'Dashboard' not in response.data or b'Today' in response.data
        # Note: Can't check for "Chores" or "Rewards" as they might appear in content
        # But we can check that User Mapping and Settings are not visible
        assert b'/users/mapping' not in response.data
        assert b'/settings' not in response.data

    def test_claim_only_sees_role_badge(self, client, claim_only_headers):
        """Test that claim_only users see their role badge."""
        response = client.get('/today', headers=claim_only_headers)

        assert b'CLAIM ONLY' in response.data or b'Claim Only' in response.data


# Fixtures for access control tests
@pytest.fixture
def unmapped_user(db_session):
    """Create an unmapped user for testing."""
    user = User(
        ha_user_id='unmapped-ha-001',
        username='Unmapped User',
        role='unmapped',
        points=0
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def unmapped_headers(unmapped_user):
    """Create headers for unmapped user authentication."""
    return {'X-Ingress-User': unmapped_user.ha_user_id}
