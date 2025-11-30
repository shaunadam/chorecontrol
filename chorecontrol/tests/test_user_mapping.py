"""Tests for user auto-creation and mapping functionality."""

import pytest
from unittest.mock import patch, MagicMock
from models import User
from auth import auto_create_unmapped_user


class TestAutoCreateUnmappedUser:
    """Tests for auto_create_unmapped_user() function."""

    def test_auto_create_new_ha_user(self, db_session, app):
        """Test auto-creating a new HA user with role='unmapped'."""
        with app.app_context():
            # Mock the HA API to return a display name
            with patch('utils.ha_api.get_ha_user_display_name') as mock_get_name:
                mock_get_name.return_value = 'John Doe'

                # Auto-create user
                new_user = auto_create_unmapped_user('ha-user-123')

                # Verify user was created
                assert new_user is not None
                assert new_user.ha_user_id == 'ha-user-123'
                assert new_user.username == 'John Doe'
                assert new_user.role == 'unmapped'
                assert new_user.points == 0

                # Verify user is in database
                db_user = User.query.filter_by(ha_user_id='ha-user-123').first()
                assert db_user is not None
                assert db_user.username == 'John Doe'

    def test_auto_create_skips_existing_user(self, db_session, app):
        """Test that auto-create returns None if user already exists."""
        with app.app_context():
            # Create existing user
            existing_user = User(
                ha_user_id='ha-existing',
                username='Existing User',
                role='parent',
                points=0
            )
            db_session.add(existing_user)
            db_session.commit()

            # Try to auto-create same user
            result = auto_create_unmapped_user('ha-existing')

            # Should return None (user already exists)
            assert result is None

            # Verify role wasn't changed
            db_user = User.query.filter_by(ha_user_id='ha-existing').first()
            assert db_user.role == 'parent'  # Still parent, not unmapped

    def test_auto_create_skips_local_accounts(self, db_session, app):
        """Test that auto-create skips local- prefix accounts."""
        with app.app_context():
            # Try to auto-create local account
            result = auto_create_unmapped_user('local-admin')

            # Should return None (local accounts are skipped)
            assert result is None

            # Verify no user was created
            db_user = User.query.filter_by(ha_user_id='local-admin').first()
            assert db_user is None

    def test_auto_create_fallback_display_name(self, db_session, app):
        """Test fallback when HA API is unavailable."""
        with app.app_context():
            # Mock HA API to return None (API unavailable)
            with patch('utils.ha_api.get_ha_user_display_name') as mock_get_name:
                mock_get_name.return_value = 'Test User'  # Fallback formatting

                new_user = auto_create_unmapped_user('test_user_id')

                assert new_user is not None
                assert new_user.username == 'Test User'

    def test_auto_create_handles_race_condition(self, db_session, app):
        """Test graceful handling of race condition (concurrent creation)."""
        with app.app_context():
            # Create user first
            user1 = User(
                ha_user_id='ha-race-test',
                username='User 1',
                role='unmapped',
                points=0
            )
            db_session.add(user1)
            db_session.commit()

            # Try to auto-create same user (simulates race condition)
            result = auto_create_unmapped_user('ha-race-test')

            # Should return None gracefully
            assert result is None

    def test_auto_create_no_password_hash(self, db_session, app):
        """Test that auto-created HA users have no password hash."""
        with app.app_context():
            with patch('utils.ha_api.get_ha_user_display_name') as mock_get_name:
                mock_get_name.return_value = 'Test User'

                new_user = auto_create_unmapped_user('ha-no-password')

                assert new_user is not None
                assert new_user.password_hash is None  # No password for HA users


class TestUserMappingRoutes:
    """Tests for user mapping UI routes."""

    def test_mapping_page_requires_parent(self, client, kid_headers):
        """Test that mapping page requires parent role."""
        response = client.get('/users/mapping', headers=kid_headers)

        # Kids should be denied access to mapping page
        assert response.status_code == 403

    def test_mapping_page_accessible_to_parent(self, client, parent_headers):
        """Test that parent can access mapping page."""
        response = client.get('/users/mapping', headers=parent_headers)

        assert response.status_code == 200
        assert b'User Mapping' in response.data

    def test_mapping_page_shows_unmapped_users(self, client, parent_headers, db_session):
        """Test that unmapped users are displayed prominently."""
        # Create unmapped user
        unmapped = User(
            ha_user_id='ha-unmapped-001',
            username='Unmapped User',
            role='unmapped',
            points=0
        )
        db_session.add(unmapped)
        db_session.commit()

        response = client.get('/users/mapping', headers=parent_headers)

        assert response.status_code == 200
        assert b'Unmapped User' in response.data
        assert b'unmapped' in response.data.lower()

    def test_update_mappings_changes_roles(self, client, parent_headers, db_session):
        """Test bulk updating user roles."""
        # Create unmapped users
        user1 = User(ha_user_id='ha-map-1', username='User 1', role='unmapped', points=0)
        user2 = User(ha_user_id='ha-map-2', username='User 2', role='unmapped', points=0)
        db_session.add_all([user1, user2])
        db_session.commit()

        # Update roles via mapping form
        response = client.post('/users/mapping/update',
                             headers=parent_headers,
                             data={
                                 f'role_{user1.id}': 'parent',
                                 f'role_{user2.id}': 'kid'
                             },
                             follow_redirects=True)

        assert response.status_code == 200

        # Verify roles were updated
        db_user1 = User.query.get(user1.id)
        db_user2 = User.query.get(user2.id)

        assert db_user1.role == 'parent'
        assert db_user2.role == 'kid'
        assert db_user2.points == 0  # Points initialized for kid

    def test_update_mappings_prevents_local_account_changes(self, client, parent_headers, db_session):
        """Test that local accounts cannot be changed via mapping."""
        # Create local account
        local_user = User(
            ha_user_id='local-test',
            username='Local User',
            role='parent',
            points=0
        )
        db_session.add(local_user)
        db_session.commit()

        # Try to change role
        response = client.post('/users/mapping/update',
                             headers=parent_headers,
                             data={f'role_{local_user.id}': 'kid'},
                             follow_redirects=True)

        assert response.status_code == 200

        # Verify role was NOT changed
        db_user = User.query.get(local_user.id)
        assert db_user.role == 'parent'  # Still parent

    def test_update_mappings_initializes_kid_points(self, client, parent_headers, db_session):
        """Test that changing to kid role initializes points to 0."""
        # Create parent user
        user = User(ha_user_id='ha-parent-to-kid', username='User', role='parent', points=0)
        db_session.add(user)
        db_session.commit()

        # Change to kid
        response = client.post('/users/mapping/update',
                             headers=parent_headers,
                             data={f'role_{user.id}': 'kid'},
                             follow_redirects=True)

        assert response.status_code == 200

        # Verify points initialized
        db_user = User.query.get(user.id)
        assert db_user.role == 'kid'
        assert db_user.points == 0

    def test_update_mappings_rejects_invalid_role(self, client, parent_headers, db_session):
        """Test that invalid roles are rejected."""
        user = User(ha_user_id='ha-invalid-role', username='User', role='unmapped', points=0)
        db_session.add(user)
        db_session.commit()

        # Try to set invalid role
        response = client.post('/users/mapping/update',
                             headers=parent_headers,
                             data={f'role_{user.id}': 'invalid_role'},
                             follow_redirects=True)

        assert response.status_code == 200

        # Verify role was NOT changed
        db_user = User.query.get(user.id)
        assert db_user.role == 'unmapped'  # Still unmapped

    def test_refresh_cache_endpoint(self, client, parent_headers):
        """Test cache refresh endpoint."""
        with patch('routes.user_mapping.clear_ha_user_cache') as mock_clear:
            response = client.post('/users/mapping/refresh-cache',
                                 headers=parent_headers,
                                 follow_redirects=True)

            assert response.status_code == 200
            mock_clear.assert_called_once()


class TestMiddlewareAutoCreate:
    """Tests for middleware auto-create integration."""

    def test_middleware_auto_creates_new_ha_user(self, client, app, db_session):
        """Test that middleware auto-creates users from X-Ingress-User header."""
        with patch('utils.ha_api.get_ha_user_display_name') as mock_get_name:
            mock_get_name.return_value = 'New HA User'

            # Make request with new HA user header
            response = client.get('/health', headers={'X-Ingress-User': 'ha-new-user-001'})

            # Request should succeed
            assert response.status_code == 200

            # User should be auto-created in database
            with app.app_context():
                user = User.query.filter_by(ha_user_id='ha-new-user-001').first()
                assert user is not None
                assert user.username == 'New HA User'
                assert user.role == 'unmapped'

    def test_middleware_skips_local_users(self, client, app, db_session):
        """Test that middleware skips auto-create for local- accounts."""
        # Make request with local user header
        response = client.get('/health', headers={'X-Ingress-User': 'local-manual-user'})

        # Should not auto-create
        with app.app_context():
            user = User.query.filter_by(ha_user_id='local-manual-user').first()
            assert user is None  # Not auto-created

    def test_middleware_idempotent_for_existing_users(self, client, app, parent_user):
        """Test that middleware doesn't duplicate existing users."""
        initial_count = User.query.count()

        # Make multiple requests with same HA user
        for _ in range(3):
            client.get('/health', headers={'X-Ingress-User': parent_user.ha_user_id})

        # User count should not increase
        final_count = User.query.count()
        assert final_count == initial_count


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
