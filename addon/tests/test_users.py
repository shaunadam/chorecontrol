"""Tests for user management API endpoints."""

import pytest
import json
from models import User, PointsHistory


class TestListUsers:
    """Tests for GET /api/users endpoint."""

    def test_list_users_success(self, client, parent_user, kid_user, parent_headers):
        """Test listing all users."""
        response = client.get('/api/users', headers=parent_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert 'data' in data
        assert len(data['data']) == 2
        assert data['total'] == 2

    def test_list_users_filter_by_role_parent(self, client, parent_user, kid_user, parent_headers):
        """Test filtering users by parent role."""
        response = client.get('/api/users?role=parent', headers=parent_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == 1
        assert data['data'][0]['role'] == 'parent'

    def test_list_users_filter_by_role_kid(self, client, parent_user, kid_user, kid_user_2, parent_headers):
        """Test filtering users by kid role."""
        response = client.get('/api/users?role=kid', headers=parent_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == 2
        assert all(u['role'] == 'kid' for u in data['data'])

    def test_list_users_invalid_role_filter(self, client, parent_headers):
        """Test invalid role filter returns error."""
        response = client.get('/api/users?role=invalid', headers=parent_headers)

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert data['error'] == 'BadRequest'

    def test_list_users_pagination(self, client, parent_headers, db_session):
        """Test pagination parameters."""
        # Create multiple users (in addition to the parent_user from fixture)
        for i in range(5):
            user = User(
                ha_user_id=f'test-user-{i}',
                username=f'Test User {i}',
                role='kid',
                points=0
            )
            db_session.add(user)
        db_session.commit()

        # Total users should be 6 (1 parent + 5 kids)
        # Test with limit
        response = client.get('/api/users?limit=3', headers=parent_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == 3
        assert data['limit'] == 3
        assert data['total'] == 6

        # Test with offset (offset 3 should give us 3 more users)
        response = client.get('/api/users?limit=3&offset=3', headers=parent_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == 3
        assert data['total'] == 6

    def test_list_users_unauthorized(self, client):
        """Test listing users without authentication."""
        response = client.get('/api/users')

        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data
        assert data['error'] == 'Unauthorized'


class TestCreateUser:
    """Tests for POST /api/users endpoint."""

    def test_create_user_success(self, client, parent_headers, db_session):
        """Test creating a new user."""
        user_data = {
            'ha_user_id': 'new-kid-001',
            'username': 'New Kid',
            'role': 'kid'
        }

        response = client.post(
            '/api/users',
            data=json.dumps(user_data),
            content_type='application/json',
            headers=parent_headers
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['username'] == 'New Kid'
        assert data['data']['role'] == 'kid'
        assert data['data']['points'] == 0

        # Verify user was created in database
        user = User.query.filter_by(ha_user_id='new-kid-001').first()
        assert user is not None
        assert user.username == 'New Kid'

    def test_create_parent_user(self, client, parent_headers):
        """Test creating a parent user."""
        user_data = {
            'ha_user_id': 'new-parent-001',
            'username': 'New Parent',
            'role': 'parent'
        }

        response = client.post(
            '/api/users',
            data=json.dumps(user_data),
            content_type='application/json',
            headers=parent_headers
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['role'] == 'parent'
        assert data['data']['points'] is None

    def test_create_user_duplicate_ha_user_id(self, client, parent_user, parent_headers):
        """Test creating a user with duplicate ha_user_id."""
        user_data = {
            'ha_user_id': parent_user.ha_user_id,
            'username': 'Duplicate User',
            'role': 'kid'
        }

        response = client.post(
            '/api/users',
            data=json.dumps(user_data),
            content_type='application/json',
            headers=parent_headers
        )

        assert response.status_code == 409
        data = response.get_json()
        assert data['error'] == 'Conflict'

    def test_create_user_missing_ha_user_id(self, client, parent_headers):
        """Test creating a user without ha_user_id."""
        user_data = {
            'username': 'No HA ID',
            'role': 'kid'
        }

        response = client.post(
            '/api/users',
            data=json.dumps(user_data),
            content_type='application/json',
            headers=parent_headers
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'ha_user_id is required' in data['message']

    def test_create_user_missing_username(self, client, parent_headers):
        """Test creating a user without username."""
        user_data = {
            'ha_user_id': 'no-username-001',
            'role': 'kid'
        }

        response = client.post(
            '/api/users',
            data=json.dumps(user_data),
            content_type='application/json',
            headers=parent_headers
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'username is required' in data['message']

    def test_create_user_invalid_role(self, client, parent_headers):
        """Test creating a user with invalid role."""
        user_data = {
            'ha_user_id': 'invalid-role-001',
            'username': 'Invalid Role',
            'role': 'admin'
        }

        response = client.post(
            '/api/users',
            data=json.dumps(user_data),
            content_type='application/json',
            headers=parent_headers
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'role is required and must be' in data['message']

    def test_create_user_requires_parent(self, client, kid_headers):
        """Test that only parents can create users."""
        user_data = {
            'ha_user_id': 'new-kid-002',
            'username': 'New Kid',
            'role': 'kid'
        }

        response = client.post(
            '/api/users',
            data=json.dumps(user_data),
            content_type='application/json',
            headers=kid_headers
        )

        assert response.status_code == 403
        data = response.get_json()
        assert data['error'] == 'Forbidden'

    def test_create_user_no_auth(self, client):
        """Test creating user without authentication."""
        user_data = {
            'ha_user_id': 'new-kid-003',
            'username': 'New Kid',
            'role': 'kid'
        }

        response = client.post(
            '/api/users',
            data=json.dumps(user_data),
            content_type='application/json'
        )

        assert response.status_code == 401


class TestGetUser:
    """Tests for GET /api/users/<id> endpoint."""

    def test_get_user_success(self, client, kid_user, parent_headers):
        """Test retrieving a user by ID."""
        response = client.get(f'/api/users/{kid_user.id}', headers=parent_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['id'] == kid_user.id
        assert data['data']['username'] == kid_user.username
        assert data['data']['role'] == 'kid'
        assert 'relationships' in data['data']

    def test_get_parent_user(self, client, parent_user, parent_headers):
        """Test retrieving a parent user shows parent-specific data."""
        response = client.get(f'/api/users/{parent_user.id}', headers=parent_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['role'] == 'parent'
        assert data['data']['points'] is None
        assert 'created_chores_count' in data['data']['relationships']
        assert 'approved_chores_count' in data['data']['relationships']

    def test_get_user_not_found(self, client, parent_headers):
        """Test retrieving a non-existent user."""
        response = client.get('/api/users/9999', headers=parent_headers)

        assert response.status_code == 404
        data = response.get_json()
        assert data['error'] == 'NotFound'
        assert '9999' in data['message']

    def test_get_user_unauthorized(self, client, kid_user):
        """Test retrieving user without authentication."""
        response = client.get(f'/api/users/{kid_user.id}')

        assert response.status_code == 401


class TestUpdateUser:
    """Tests for PUT /api/users/<id> endpoint."""

    def test_update_user_username(self, client, kid_user, parent_headers, db_session):
        """Test updating user's username."""
        update_data = {
            'username': 'Updated Kid Name'
        }

        response = client.put(
            f'/api/users/{kid_user.id}',
            data=json.dumps(update_data),
            content_type='application/json',
            headers=parent_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['username'] == 'Updated Kid Name'

        # Verify in database
        db_session.refresh(kid_user)
        assert kid_user.username == 'Updated Kid Name'

    def test_update_user_role(self, client, kid_user, parent_headers, db_session):
        """Test updating user's role."""
        update_data = {
            'role': 'parent'
        }

        response = client.put(
            f'/api/users/{kid_user.id}',
            data=json.dumps(update_data),
            content_type='application/json',
            headers=parent_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['role'] == 'parent'

    def test_update_parent_to_kid(self, client, parent_user, parent_headers, db_session):
        """Test changing parent to kid initializes points."""
        # Create a second parent to make the request
        second_parent = User(
            ha_user_id='parent-ha-002',
            username='Second Parent',
            role='parent',
            points=0
        )
        db_session.add(second_parent)
        db_session.commit()

        update_data = {
            'role': 'kid'
        }

        response = client.put(
            f'/api/users/{parent_user.id}',
            data=json.dumps(update_data),
            content_type='application/json',
            headers={'X-Ingress-User': second_parent.ha_user_id}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['role'] == 'kid'
        assert data['data']['points'] == 0

    def test_update_user_cannot_change_ha_user_id(self, client, kid_user, parent_headers):
        """Test that ha_user_id cannot be changed."""
        update_data = {
            'ha_user_id': 'new-ha-id'
        }

        response = client.put(
            f'/api/users/{kid_user.id}',
            data=json.dumps(update_data),
            content_type='application/json',
            headers=parent_headers
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'ha_user_id cannot be changed' in data['message']

    def test_update_user_invalid_role(self, client, kid_user, parent_headers):
        """Test updating with invalid role."""
        update_data = {
            'role': 'superuser'
        }

        response = client.put(
            f'/api/users/{kid_user.id}',
            data=json.dumps(update_data),
            content_type='application/json',
            headers=parent_headers
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'role must be' in data['message']

    def test_update_user_empty_username(self, client, kid_user, parent_headers):
        """Test updating with empty username."""
        update_data = {
            'username': ''
        }

        response = client.put(
            f'/api/users/{kid_user.id}',
            data=json.dumps(update_data),
            content_type='application/json',
            headers=parent_headers
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'username cannot be empty' in data['message']

    def test_update_user_not_found(self, client, parent_headers):
        """Test updating a non-existent user."""
        update_data = {
            'username': 'Ghost User'
        }

        response = client.put(
            '/api/users/9999',
            data=json.dumps(update_data),
            content_type='application/json',
            headers=parent_headers
        )

        assert response.status_code == 404

    def test_update_user_requires_parent(self, client, kid_user, kid_headers):
        """Test that only parents can update users."""
        update_data = {
            'username': 'Hacked Name'
        }

        response = client.put(
            f'/api/users/{kid_user.id}',
            data=json.dumps(update_data),
            content_type='application/json',
            headers=kid_headers
        )

        assert response.status_code == 403


class TestGetUserPoints:
    """Tests for GET /api/users/<id>/points endpoint."""

    def test_get_user_points_success(self, client, user_with_points_history, parent_headers):
        """Test retrieving user points and history."""
        response = client.get(
            f'/api/users/{user_with_points_history.id}/points',
            headers=parent_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'data' in data
        assert data['data']['user_id'] == user_with_points_history.id
        assert 'current_balance' in data['data']
        assert 'calculated_balance' in data['data']
        assert 'is_balanced' in data['data']
        assert 'history' in data['data']
        assert len(data['data']['history']) == 5

    def test_get_user_points_balance_verification(self, client, kid_user, parent_headers, db_session):
        """Test that points balance verification works correctly."""
        # Manually adjust points to match history
        kid_user.points = 50
        db_session.commit()

        # Add history that should total to 50
        history_entries = [
            PointsHistory(user_id=kid_user.id, points_delta=30, reason='Test 1'),
            PointsHistory(user_id=kid_user.id, points_delta=20, reason='Test 2')
        ]
        for entry in history_entries:
            db_session.add(entry)
        db_session.commit()

        response = client.get(f'/api/users/{kid_user.id}/points', headers=parent_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['current_balance'] == 50
        assert data['data']['calculated_balance'] == 50
        assert data['data']['is_balanced'] is True

    def test_get_user_points_imbalance_detection(self, client, kid_user, parent_headers, db_session):
        """Test that points imbalance is detected."""
        # Set points to wrong value
        kid_user.points = 100
        db_session.commit()

        # Add history that totals to 50
        history_entries = [
            PointsHistory(user_id=kid_user.id, points_delta=30, reason='Test 1'),
            PointsHistory(user_id=kid_user.id, points_delta=20, reason='Test 2')
        ]
        for entry in history_entries:
            db_session.add(entry)
        db_session.commit()

        response = client.get(f'/api/users/{kid_user.id}/points', headers=parent_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['current_balance'] == 100
        assert data['data']['calculated_balance'] == 50
        assert data['data']['is_balanced'] is False

    def test_get_user_points_pagination(self, client, kid_user, parent_headers, db_session):
        """Test pagination of points history."""
        # Add multiple history entries
        for i in range(10):
            entry = PointsHistory(
                user_id=kid_user.id,
                points_delta=5,
                reason=f'Test entry {i}'
            )
            db_session.add(entry)
        db_session.commit()

        # Test with limit
        response = client.get(
            f'/api/users/{kid_user.id}/points?limit=5',
            headers=parent_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']['history']) == 5
        assert data['data']['limit'] == 5

        # Test with offset
        response = client.get(
            f'/api/users/{kid_user.id}/points?limit=5&offset=5',
            headers=parent_headers
        )

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']['history']) == 5

    def test_get_user_points_not_found(self, client, parent_headers):
        """Test getting points for non-existent user."""
        response = client.get('/api/users/9999/points', headers=parent_headers)

        assert response.status_code == 404

    def test_get_user_points_unauthorized(self, client, kid_user):
        """Test getting points without authentication."""
        response = client.get(f'/api/users/{kid_user.id}/points')

        assert response.status_code == 401


class TestAuthenticationMiddleware:
    """Tests for authentication and authorization decorators."""

    def test_requires_auth_decorator(self, client, parent_user):
        """Test that requires_auth decorator works correctly."""
        # Without auth header
        response = client.get('/api/users')
        assert response.status_code == 401

        # With auth header for existing user
        response = client.get('/api/users', headers={'X-Ingress-User': parent_user.ha_user_id})
        assert response.status_code == 200

    def test_requires_auth_nonexistent_user(self, client):
        """Test requires_auth with HA user not in database."""
        response = client.get('/api/users', headers={'X-Ingress-User': 'nonexistent-user'})
        assert response.status_code == 401
        data = response.get_json()
        assert 'User not found in database' in data['message']

    def test_requires_parent_decorator(self, client, kid_user, parent_user):
        """Test that requires_parent decorator works correctly."""
        # Kid tries to create user
        response = client.post(
            '/api/users',
            data=json.dumps({'ha_user_id': 'new-kid-created', 'username': 'New', 'role': 'kid'}),
            content_type='application/json',
            headers={'X-Ingress-User': kid_user.ha_user_id}
        )
        assert response.status_code == 403

        # Parent can create user
        response = client.post(
            '/api/users',
            data=json.dumps({'ha_user_id': 'new-parent-created', 'username': 'New', 'role': 'kid'}),
            content_type='application/json',
            headers={'X-Ingress-User': parent_user.ha_user_id}
        )
        assert response.status_code == 201
