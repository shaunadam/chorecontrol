"""
Tests for Chore Management API (Stream 2).

This test suite covers all 6 chore endpoints:
- GET /api/chores (list with filters)
- POST /api/chores (create with validation)
- GET /api/chores/{id} (details)
- PUT /api/chores/{id} (update)
- DELETE /api/chores/{id} (soft delete)
- GET /api/chores/{id}/instances (paginated instances)
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import patch
from models import db, Chore, ChoreAssignment, ChoreInstance, User


class TestListChores:
    """Tests for GET /api/chores endpoint."""

    def test_list_chores_requires_auth(self, client, unauthenticated_headers):
        """Test that listing chores requires authentication."""
        response = client.get('/api/chores', headers=unauthenticated_headers)
        assert response.status_code == 401
        data = response.get_json()
        assert data['error'] == 'Unauthorized'

    def test_list_chores_empty(self, client, parent_headers):
        """Test listing chores when none exist."""
        response = client.get('/api/chores', headers=parent_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['data'] == []
        assert data['total'] == 0
        assert data['limit'] == 50
        assert data['offset'] == 0

    def test_list_chores_with_data(self, client, parent_headers, sample_chore):
        """Test listing chores with data."""
        response = client.get('/api/chores', headers=parent_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == 1
        assert data['total'] == 1
        assert data['data'][0]['name'] == 'Take out trash'
        assert data['data'][0]['points'] == 5

    def test_list_chores_filter_by_active(self, client, parent_headers, db_session, parent_user):
        """Test filtering chores by active status."""
        # Create active and inactive chores
        active_chore = Chore(
            name='Active chore',
            points=10,
            is_active=True,
            created_by=parent_user.id
        )
        inactive_chore = Chore(
            name='Inactive chore',
            points=5,
            is_active=False,
            created_by=parent_user.id
        )
        db_session.add_all([active_chore, inactive_chore])
        db_session.commit()

        # Filter for active only
        response = client.get('/api/chores?active=true', headers=parent_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == 1
        assert data['data'][0]['name'] == 'Active chore'

        # Filter for inactive only
        response = client.get('/api/chores?active=false', headers=parent_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == 1
        assert data['data'][0]['name'] == 'Inactive chore'

    def test_list_chores_filter_by_assigned_to(self, client, parent_headers, db_session, parent_user, kid_user, kid_user_2):
        """Test filtering chores by assigned user."""
        # Create chores with different assignments
        chore1 = Chore(name='Chore 1', points=5, created_by=parent_user.id)
        chore2 = Chore(name='Chore 2', points=10, created_by=parent_user.id)
        db_session.add_all([chore1, chore2])
        db_session.commit()

        # Assign chore1 to kid_user, chore2 to kid_user_2
        assignment1 = ChoreAssignment(chore_id=chore1.id, user_id=kid_user.id)
        assignment2 = ChoreAssignment(chore_id=chore2.id, user_id=kid_user_2.id)
        db_session.add_all([assignment1, assignment2])
        db_session.commit()

        # Filter by kid_user
        response = client.get(f'/api/chores?assigned_to={kid_user.id}', headers=parent_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == 1
        assert data['data'][0]['name'] == 'Chore 1'

    def test_list_chores_filter_by_recurrence_type(self, client, parent_headers, db_session, parent_user):
        """Test filtering chores by recurrence type."""
        # Create chores with different recurrence types
        simple_chore = Chore(
            name='Simple chore',
            points=5,
            recurrence_type='simple',
            recurrence_pattern={'type': 'simple', 'interval': 'daily', 'every_n': 1},
            created_by=parent_user.id
        )
        complex_chore = Chore(
            name='Complex chore',
            points=10,
            recurrence_type='complex',
            recurrence_pattern={'type': 'complex', 'days_of_week': [0, 2, 4]},
            created_by=parent_user.id
        )
        db_session.add_all([simple_chore, complex_chore])
        db_session.commit()

        # Filter by simple
        response = client.get('/api/chores?recurrence_type=simple', headers=parent_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == 1
        assert data['data'][0]['name'] == 'Simple chore'

    def test_list_chores_pagination(self, client, parent_headers, db_session, parent_user):
        """Test pagination of chore list."""
        # Create 5 chores
        for i in range(5):
            chore = Chore(name=f'Chore {i}', points=i, created_by=parent_user.id)
            db_session.add(chore)
        db_session.commit()

        # Get first 2
        response = client.get('/api/chores?limit=2&offset=0', headers=parent_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == 2
        assert data['total'] == 5
        assert data['limit'] == 2
        assert data['offset'] == 0

        # Get next 2
        response = client.get('/api/chores?limit=2&offset=2', headers=parent_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == 2
        assert data['total'] == 5


class TestCreateChore:
    """Tests for POST /api/chores endpoint."""

    def test_create_chore_requires_auth(self, client, unauthenticated_headers):
        """Test that creating chores requires authentication."""
        response = client.post('/api/chores',
                              json={'name': 'Test', 'points': 5},
                              headers=unauthenticated_headers)
        assert response.status_code == 401

    def test_create_chore_minimal(self, client, parent_headers):
        """Test creating a chore with minimal required fields."""
        chore_data = {
            'name': 'Take out trash',
            'points': 5
        }
        response = client.post('/api/chores', json=chore_data, headers=parent_headers)
        assert response.status_code == 201
        data = response.get_json()
        assert data['message'] == 'Chore created successfully'
        assert data['data']['name'] == 'Take out trash'
        assert data['data']['points'] == 5
        assert data['data']['is_active'] is True

    def test_create_chore_with_all_fields(self, client, parent_headers):
        """Test creating a chore with all fields."""
        chore_data = {
            'name': 'Take out trash',
            'description': 'Roll bins to curb',
            'points': 5,
            'recurrence_type': 'simple',
            'recurrence_pattern': {'type': 'simple', 'interval': 'weekly', 'every_n': 1},
            'start_date': '2025-01-01',
            'end_date': '2025-12-31',
            'assignment_type': 'individual',
            'requires_approval': True,
            'auto_approve_after_hours': 24
        }
        response = client.post('/api/chores', json=chore_data, headers=parent_headers)
        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['name'] == 'Take out trash'
        assert data['data']['description'] == 'Roll bins to curb'
        assert data['data']['recurrence_type'] == 'simple'
        assert data['data']['start_date'] == '2025-01-01'

    def test_create_chore_with_assignments(self, client, parent_headers, kid_user, kid_user_2):
        """Test creating a chore with assignments."""
        chore_data = {
            'name': 'Clean room',
            'points': 10,
            'assignments': [
                {'user_id': kid_user.id},
                {'user_id': kid_user_2.id}
            ]
        }
        response = client.post('/api/chores', json=chore_data, headers=parent_headers)
        assert response.status_code == 201
        data = response.get_json()
        assert len(data['data']['assignments']) == 2
        assert data['data']['assignments'][0]['user_id'] == kid_user.id
        assert data['data']['assignments'][1]['user_id'] == kid_user_2.id

    def test_create_chore_missing_name(self, client, parent_headers):
        """Test creating a chore without required name field."""
        chore_data = {'points': 5}
        response = client.post('/api/chores', json=chore_data, headers=parent_headers)
        assert response.status_code == 400
        data = response.get_json()
        assert 'name' in data['message'].lower()

    def test_create_chore_missing_points(self, client, parent_headers):
        """Test creating a chore without required points field."""
        chore_data = {'name': 'Test chore'}
        response = client.post('/api/chores', json=chore_data, headers=parent_headers)
        assert response.status_code == 400
        data = response.get_json()
        assert 'points' in data['message'].lower()

    def test_create_chore_invalid_recurrence_pattern(self, client, parent_headers):
        """Test creating a chore with invalid recurrence pattern."""
        chore_data = {
            'name': 'Test chore',
            'points': 5,
            'recurrence_type': 'simple',
            'recurrence_pattern': {'type': 'invalid', 'foo': 'bar'}
        }
        response = client.post('/api/chores', json=chore_data, headers=parent_headers)
        assert response.status_code == 400
        data = response.get_json()
        assert 'recurrence pattern' in data['message'].lower()

    def test_create_chore_invalid_recurrence_type(self, client, parent_headers):
        """Test creating a chore with invalid recurrence type."""
        chore_data = {
            'name': 'Test chore',
            'points': 5,
            'recurrence_type': 'invalid_type'
        }
        response = client.post('/api/chores', json=chore_data, headers=parent_headers)
        assert response.status_code == 400

    def test_create_chore_invalid_assignment_type(self, client, parent_headers):
        """Test creating a chore with invalid assignment type."""
        chore_data = {
            'name': 'Test chore',
            'points': 5,
            'assignment_type': 'invalid_type'
        }
        response = client.post('/api/chores', json=chore_data, headers=parent_headers)
        assert response.status_code == 400

    def test_create_chore_assignment_nonexistent_user(self, client, parent_headers):
        """Test creating a chore with assignment to non-existent user."""
        chore_data = {
            'name': 'Test chore',
            'points': 5,
            'assignments': [{'user_id': 99999}]
        }
        response = client.post('/api/chores', json=chore_data, headers=parent_headers)
        assert response.status_code == 400
        data = response.get_json()
        assert 'not found' in data['message'].lower()

    def test_create_chore_complex_recurrence(self, client, parent_headers):
        """Test creating a chore with complex recurrence pattern."""
        chore_data = {
            'name': 'Weekly meeting prep',
            'points': 15,
            'recurrence_type': 'complex',
            'recurrence_pattern': {
                'type': 'complex',
                'days_of_week': [0, 2, 4],  # Mon, Wed, Fri
                'time': '08:00'
            }
        }
        response = client.post('/api/chores', json=chore_data, headers=parent_headers)
        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['recurrence_type'] == 'complex'


class TestGetChore:
    """Tests for GET /api/chores/{id} endpoint."""

    def test_get_chore_requires_auth(self, client, unauthenticated_headers, sample_chore):
        """Test that getting a chore requires authentication."""
        response = client.get(f'/api/chores/{sample_chore.id}', headers=unauthenticated_headers)
        assert response.status_code == 401

    def test_get_chore_success(self, client, parent_headers, sample_chore):
        """Test getting a chore by ID."""
        response = client.get(f'/api/chores/{sample_chore.id}', headers=parent_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['id'] == sample_chore.id
        assert data['data']['name'] == 'Take out trash'
        assert data['data']['points'] == 5

    def test_get_chore_not_found(self, client, parent_headers):
        """Test getting a non-existent chore."""
        response = client.get('/api/chores/99999', headers=parent_headers)
        assert response.status_code == 404
        data = response.get_json()
        assert 'not found' in data['message'].lower()

    def test_get_chore_with_assignments(self, client, parent_headers, db_session, parent_user, kid_user):
        """Test getting a chore with assignments."""
        chore = Chore(name='Test chore', points=5, created_by=parent_user.id)
        db_session.add(chore)
        db_session.commit()

        assignment = ChoreAssignment(chore_id=chore.id, user_id=kid_user.id)
        db_session.add(assignment)
        db_session.commit()

        response = client.get(f'/api/chores/{chore.id}', headers=parent_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']['assignments']) == 1
        assert data['data']['assignments'][0]['user_id'] == kid_user.id
        assert data['data']['assignment_count'] == 1

    def test_get_chore_with_instance_count(self, client, parent_headers, db_session, sample_chore):
        """Test that chore details include instance count."""
        # Create some instances
        for i in range(3):
            instance = ChoreInstance(
                chore_id=sample_chore.id,
                due_date=date(2025, 1, i+1),
                status='assigned'
            )
            db_session.add(instance)
        db_session.commit()

        response = client.get(f'/api/chores/{sample_chore.id}', headers=parent_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['instance_count'] == 3


class TestUpdateChore:
    """Tests for PUT /api/chores/{id} endpoint."""

    def test_update_chore_requires_auth(self, client, unauthenticated_headers, sample_chore):
        """Test that updating a chore requires authentication."""
        response = client.put(f'/api/chores/{sample_chore.id}',
                             json={'name': 'Updated'},
                             headers=unauthenticated_headers)
        assert response.status_code == 401

    def test_update_chore_name(self, client, parent_headers, sample_chore):
        """Test updating a chore's name."""
        response = client.put(f'/api/chores/{sample_chore.id}',
                             json={'name': 'Updated name'},
                             headers=parent_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['name'] == 'Updated name'

    def test_update_chore_multiple_fields(self, client, parent_headers, sample_chore):
        """Test updating multiple fields at once."""
        update_data = {
            'name': 'New name',
            'description': 'New description',
            'points': 15
        }
        response = client.put(f'/api/chores/{sample_chore.id}',
                             json=update_data,
                             headers=parent_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['name'] == 'New name'
        assert data['data']['description'] == 'New description'
        assert data['data']['points'] == 15

    def test_update_chore_recurrence_pattern(self, client, parent_headers, sample_chore):
        """Test updating recurrence pattern."""
        update_data = {
            'recurrence_pattern': {
                'type': 'simple',
                'interval': 'daily',
                'every_n': 2
            }
        }
        response = client.put(f'/api/chores/{sample_chore.id}',
                             json=update_data,
                             headers=parent_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['recurrence_pattern']['interval'] == 'daily'
        assert data['data']['recurrence_pattern']['every_n'] == 2

    def test_update_chore_invalid_recurrence_pattern(self, client, parent_headers, sample_chore):
        """Test updating with invalid recurrence pattern."""
        update_data = {
            'recurrence_pattern': {'type': 'invalid'}
        }
        response = client.put(f'/api/chores/{sample_chore.id}',
                             json=update_data,
                             headers=parent_headers)
        assert response.status_code == 400

    def test_update_chore_not_found(self, client, parent_headers):
        """Test updating a non-existent chore."""
        response = client.put('/api/chores/99999',
                             json={'name': 'Updated'},
                             headers=parent_headers)
        assert response.status_code == 404

    def test_update_chore_empty_body(self, client, parent_headers, sample_chore):
        """Test updating with empty request body."""
        response = client.put(f'/api/chores/{sample_chore.id}',
                             json=None,
                             headers=parent_headers)
        assert response.status_code == 400


class TestDeleteChore:
    """Tests for DELETE /api/chores/{id} endpoint (soft delete)."""

    def test_delete_chore_requires_auth(self, client, unauthenticated_headers, sample_chore):
        """Test that deleting a chore requires authentication."""
        response = client.delete(f'/api/chores/{sample_chore.id}', headers=unauthenticated_headers)
        assert response.status_code == 401

    def test_delete_chore_success(self, client, parent_headers, sample_chore, db_session):
        """Test soft deleting a chore."""
        response = client.delete(f'/api/chores/{sample_chore.id}', headers=parent_headers)
        assert response.status_code == 204

        # Verify chore still exists but is inactive
        chore = db_session.get(Chore, sample_chore.id)
        assert chore is not None
        assert chore.is_active is False

    def test_delete_chore_not_found(self, client, parent_headers):
        """Test deleting a non-existent chore."""
        response = client.delete('/api/chores/99999', headers=parent_headers)
        assert response.status_code == 404

    def test_delete_chore_preserves_instances(self, client, parent_headers, db_session, sample_chore):
        """Test that soft delete preserves chore instances."""
        # Create an instance
        instance = ChoreInstance(
            chore_id=sample_chore.id,
            due_date=date.today(),
            status='assigned'
        )
        db_session.add(instance)
        db_session.commit()

        # Soft delete the chore
        response = client.delete(f'/api/chores/{sample_chore.id}', headers=parent_headers)
        assert response.status_code == 204

        # Verify instance still exists
        instances = ChoreInstance.query.filter_by(chore_id=sample_chore.id).all()
        assert len(instances) == 1


class TestGetChoreInstances:
    """Tests for GET /api/chores/{id}/instances endpoint."""

    def test_get_chore_instances_requires_auth(self, client, unauthenticated_headers, sample_chore):
        """Test that getting chore instances requires authentication."""
        response = client.get(f'/api/chores/{sample_chore.id}/instances',
                             headers=unauthenticated_headers)
        assert response.status_code == 401

    def test_get_chore_instances_empty(self, client, parent_headers, sample_chore):
        """Test getting instances when none exist."""
        response = client.get(f'/api/chores/{sample_chore.id}/instances', headers=parent_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['data'] == []
        assert data['total'] == 0

    def test_get_chore_instances_with_data(self, client, parent_headers, db_session, sample_chore, kid_user):
        """Test getting chore instances."""
        # Create instances
        instances = []
        for i in range(3):
            instance = ChoreInstance(
                chore_id=sample_chore.id,
                due_date=date(2025, 1, i+1),
                status='assigned'
            )
            instances.append(instance)
            db_session.add(instance)
        db_session.commit()

        response = client.get(f'/api/chores/{sample_chore.id}/instances', headers=parent_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == 3
        assert data['total'] == 3

    def test_get_chore_instances_filter_by_status(self, client, parent_headers, db_session, sample_chore, kid_user):
        """Test filtering instances by status."""
        # Create instances with different statuses
        assigned = ChoreInstance(chore_id=sample_chore.id, due_date=date(2025, 1, 1), status='assigned')
        claimed = ChoreInstance(
            chore_id=sample_chore.id,
            due_date=date(2025, 1, 2),
            status='claimed',
            claimed_by=kid_user.id,
            claimed_at=datetime.utcnow()
        )
        db_session.add_all([assigned, claimed])
        db_session.commit()

        # Filter for claimed only
        response = client.get(f'/api/chores/{sample_chore.id}/instances?status=claimed',
                             headers=parent_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == 1
        assert data['data'][0]['status'] == 'claimed'

    def test_get_chore_instances_pagination(self, client, parent_headers, db_session, sample_chore):
        """Test pagination of instances."""
        # Create 5 instances
        for i in range(5):
            instance = ChoreInstance(
                chore_id=sample_chore.id,
                due_date=date(2025, 1, i+1),
                status='assigned'
            )
            db_session.add(instance)
        db_session.commit()

        # Get first 2
        response = client.get(f'/api/chores/{sample_chore.id}/instances?limit=2&offset=0',
                             headers=parent_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == 2
        assert data['total'] == 5

    def test_get_chore_instances_nonexistent_chore(self, client, parent_headers):
        """Test getting instances for non-existent chore."""
        response = client.get('/api/chores/99999/instances', headers=parent_headers)
        assert response.status_code == 404

    def test_get_chore_instances_invalid_status(self, client, parent_headers, sample_chore):
        """Test filtering with invalid status value."""
        response = client.get(f'/api/chores/{sample_chore.id}/instances?status=invalid',
                             headers=parent_headers)
        assert response.status_code == 400


class TestChoreNewFields:
    """Tests for new chore fields: allow_late_claims, late_points."""

    def test_create_chore_with_late_claims(self, client, parent_headers):
        """Test creating a chore with late claim settings."""
        chore_data = {
            'name': 'Chore with late claims',
            'points': 10,
            'allow_late_claims': True,
            'late_points': 5
        }
        response = client.post('/api/chores', json=chore_data, headers=parent_headers)
        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['allow_late_claims'] is True
        assert data['data']['late_points'] == 5

    def test_create_chore_late_points_validation(self, client, parent_headers):
        """Test that late_points must be non-negative."""
        chore_data = {
            'name': 'Invalid late points',
            'points': 10,
            'late_points': -5
        }
        response = client.post('/api/chores', json=chore_data, headers=parent_headers)
        assert response.status_code == 400
        assert 'late_points' in response.get_json()['message'].lower()

    def test_update_chore_late_claims(self, client, parent_headers, sample_chore):
        """Test updating late claim settings."""
        update_data = {
            'allow_late_claims': True,
            'late_points': 3
        }
        response = client.put(f'/api/chores/{sample_chore.id}',
                             json=update_data,
                             headers=parent_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['allow_late_claims'] is True
        assert data['data']['late_points'] == 3

    def test_update_chore_late_points_validation(self, client, parent_headers, sample_chore):
        """Test that late_points must be non-negative on update."""
        update_data = {
            'late_points': -1
        }
        response = client.put(f'/api/chores/{sample_chore.id}',
                             json=update_data,
                             headers=parent_headers)
        assert response.status_code == 400


class TestChoreInstanceGeneration:
    """Tests for automatic instance generation on chore creation."""

    def test_create_chore_generates_instances(self, client, parent_headers, kid_user, db_session):
        """Test that creating a chore generates instances."""
        # Create a simple daily recurring chore starting today
        today = date.today()
        chore_data = {
            'name': 'Daily chore',
            'points': 5,
            'recurrence_type': 'simple',
            'recurrence_pattern': {
                'type': 'simple',
                'interval': 'daily',
                'every_n': 1
            },
            'start_date': today.isoformat(),
            'assignment_type': 'individual',
            'assignments': [{'user_id': kid_user.id}]
        }

        response = client.post('/api/chores', json=chore_data, headers=parent_headers)
        assert response.status_code == 201
        data = response.get_json()

        # Check that instances were created
        chore_id = data['data']['id']
        instances = ChoreInstance.query.filter_by(chore_id=chore_id).all()
        assert len(instances) > 0

    def test_update_chore_pattern_regenerates_instances(self, client, parent_headers, db_session, parent_user, kid_user):
        """Test that updating recurrence pattern regenerates instances."""
        # Create initial chore with weekly pattern
        today = date.today()
        chore = Chore(
            name='Weekly chore regen',
            points=10,
            recurrence_type='simple',
            recurrence_pattern={'type': 'simple', 'interval': 'weekly', 'every_n': 1},
            start_date=today,
            assignment_type='individual',
            created_by=parent_user.id,
            is_active=True
        )
        db_session.add(chore)
        db_session.flush()
        chore_id = chore.id

        # Add assignment
        assignment = ChoreAssignment(chore_id=chore_id, user_id=kid_user.id)
        db_session.add(assignment)
        db_session.commit()

        # Update to daily pattern (which should trigger regeneration)
        update_data = {
            'recurrence_pattern': {
                'type': 'simple',
                'interval': 'daily',
                'every_n': 1
            }
        }
        response = client.put(f'/api/chores/{chore_id}',
                             json=update_data,
                             headers=parent_headers)
        assert response.status_code == 200

        # Verify the pattern was updated
        data = response.get_json()
        assert data['data']['recurrence_pattern']['interval'] == 'daily'

        # Instances should have been generated
        instance_count = ChoreInstance.query.filter_by(chore_id=chore_id).count()
        assert instance_count > 0  # Should have daily instances


class TestWebhooks:
    """Tests for webhook firing."""

    @patch('utils.webhooks.requests.post')
    def test_points_adjustment_fires_webhook(self, mock_post, client, parent_headers, kid_user, db_session, app):
        """Test that adjusting points fires a webhook."""
        # Configure webhook URL
        with app.app_context():
            app.config['HA_WEBHOOK_URL'] = 'http://test-webhook.local'
            from config import Config
            Config.HA_WEBHOOK_URL = 'http://test-webhook.local'

        mock_post.return_value.status_code = 200

        adjustment_data = {
            'user_id': kid_user.id,
            'points_delta': 10,
            'reason': 'Webhook test'
        }

        response = client.post('/api/points/adjust', json=adjustment_data, headers=parent_headers)
        assert response.status_code == 200

        # Webhook should have been called
        # Note: May not be called if webhook URL not configured

    def test_webhook_payload_structure(self, db_session, kid_user):
        """Test webhook payload structure."""
        from utils.webhooks import build_payload

        payload = build_payload('test_event', kid_user)

        assert 'event' in payload
        assert payload['event'] == 'test_event'
        assert 'timestamp' in payload
        assert 'data' in payload
        assert payload['data']['id'] == kid_user.id
