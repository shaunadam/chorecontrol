"""Tests for Instance Workflow API (Stream 3).

This module tests the core chore instance workflow:
- Listing and retrieving instances
- Claiming chores
- Approving chores (with points awarding)
- Rejecting chores (with re-claim ability)
- State machine enforcement
- Permission checks
"""

import pytest
from datetime import date, datetime, timedelta
from models import db, ChoreInstance, ChoreAssignment, User, PointsHistory


@pytest.fixture
def assigned_instance(db_session, sample_chore, kid_user):
    """Create an assigned chore instance for testing."""
    # Check if assignment already exists to avoid unique constraint violation
    assignment = ChoreAssignment.query.filter_by(
        chore_id=sample_chore.id,
        user_id=kid_user.id,
        due_date=date.today()
    ).first()

    if not assignment:
        assignment = ChoreAssignment(
            chore_id=sample_chore.id,
            user_id=kid_user.id,
            due_date=date.today()
        )
        db_session.add(assignment)

    # Create instance
    instance = ChoreInstance(
        chore_id=sample_chore.id,
        due_date=date.today(),
        status='assigned'
    )
    db_session.add(instance)
    db_session.commit()
    return instance


@pytest.fixture
def claimed_instance(db_session, sample_chore, kid_user):
    """Create a claimed chore instance for testing."""
    # Check if assignment already exists to avoid unique constraint violation
    assignment = ChoreAssignment.query.filter_by(
        chore_id=sample_chore.id,
        user_id=kid_user.id,
        due_date=date.today()
    ).first()

    if not assignment:
        assignment = ChoreAssignment(
            chore_id=sample_chore.id,
            user_id=kid_user.id,
            due_date=date.today()
        )
        db_session.add(assignment)

    # Create instance
    instance = ChoreInstance(
        chore_id=sample_chore.id,
        due_date=date.today(),
        status='claimed',
        claimed_by=kid_user.id,
        claimed_at=datetime.utcnow()
    )
    db_session.add(instance)
    db_session.commit()
    return instance


@pytest.fixture
def approved_instance(db_session, sample_chore, kid_user, parent_user):
    """Create an approved chore instance for testing."""
    # Check if assignment already exists to avoid unique constraint violation
    assignment = ChoreAssignment.query.filter_by(
        chore_id=sample_chore.id,
        user_id=kid_user.id,
        due_date=date.today()
    ).first()

    if not assignment:
        assignment = ChoreAssignment(
            chore_id=sample_chore.id,
            user_id=kid_user.id,
            due_date=date.today()
        )
        db_session.add(assignment)

    # Create instance
    instance = ChoreInstance(
        chore_id=sample_chore.id,
        due_date=date.today(),
        status='approved',
        claimed_by=kid_user.id,
        claimed_at=datetime.utcnow(),
        approved_by=parent_user.id,
        approved_at=datetime.utcnow(),
        points_awarded=5
    )
    db_session.add(instance)
    db_session.commit()
    return instance


@pytest.fixture
def rejected_instance(db_session, sample_chore, kid_user, parent_user):
    """Create a rejected chore instance for testing."""
    # Check if assignment already exists to avoid unique constraint violation
    assignment = ChoreAssignment.query.filter_by(
        chore_id=sample_chore.id,
        user_id=kid_user.id,
        due_date=date.today()
    ).first()

    if not assignment:
        assignment = ChoreAssignment(
            chore_id=sample_chore.id,
            user_id=kid_user.id,
            due_date=date.today()
        )
        db_session.add(assignment)

    # Create instance - status is 'assigned' after rejection (can re-claim)
    instance = ChoreInstance(
        chore_id=sample_chore.id,
        due_date=date.today(),
        status='assigned',  # Set back to assigned after rejection
        rejected_by=parent_user.id,
        rejected_at=datetime.utcnow(),
        rejection_reason='Needs to be done properly'
    )
    db_session.add(instance)
    db_session.commit()
    return instance


# ============================================================================
# GET /api/instances - List instances
# ============================================================================

def test_list_instances_success(client, kid_headers, assigned_instance, claimed_instance):
    """Test listing all instances."""
    response = client.get('/api/instances', headers=kid_headers)

    assert response.status_code == 200
    data = response.get_json()

    assert 'data' in data
    assert 'total' in data
    assert 'limit' in data
    assert 'offset' in data
    assert data['total'] == 2
    assert len(data['data']) == 2


def test_list_instances_filter_by_status(client, kid_headers, assigned_instance, claimed_instance):
    """Test filtering instances by status."""
    response = client.get('/api/instances?status=claimed', headers=kid_headers)

    assert response.status_code == 200
    data = response.get_json()

    assert data['total'] == 1
    assert data['data'][0]['status'] == 'claimed'


def test_list_instances_filter_by_user(client, kid_headers, kid_user, claimed_instance):
    """Test filtering instances by user_id."""
    response = client.get(f'/api/instances?user_id={kid_user.id}', headers=kid_headers)

    assert response.status_code == 200
    data = response.get_json()

    assert data['total'] == 1
    assert data['data'][0]['claimed_by'] == kid_user.id


def test_list_instances_filter_by_chore(client, kid_headers, sample_chore, assigned_instance):
    """Test filtering instances by chore_id."""
    response = client.get(f'/api/instances?chore_id={sample_chore.id}', headers=kid_headers)

    assert response.status_code == 200
    data = response.get_json()

    assert data['total'] == 1
    assert data['data'][0]['chore_id'] == sample_chore.id


def test_list_instances_filter_by_date_range(client, kid_headers, assigned_instance):
    """Test filtering instances by date range."""
    today = date.today()
    tomorrow = today + timedelta(days=1)
    yesterday = today - timedelta(days=1)

    response = client.get(
        f'/api/instances?start_date={yesterday.isoformat()}&end_date={tomorrow.isoformat()}',
        headers=kid_headers
    )

    assert response.status_code == 200
    data = response.get_json()

    assert data['total'] >= 1


def test_list_instances_invalid_date_format(client, kid_headers):
    """Test error handling for invalid date format."""
    response = client.get('/api/instances?start_date=invalid-date', headers=kid_headers)

    assert response.status_code == 400
    data = response.get_json()
    assert 'Invalid start_date format' in data['message']


def test_list_instances_pagination(client, kid_headers, db_session, sample_chore, kid_user):
    """Test pagination of instance listing."""
    # Create 10 instances
    for i in range(10):
        instance = ChoreInstance(
            chore_id=sample_chore.id,
            due_date=date.today() + timedelta(days=i),
            status='assigned'
        )
        db_session.add(instance)
    db_session.commit()

    # Test first page
    response = client.get('/api/instances?limit=5&offset=0', headers=kid_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert len(data['data']) == 5
    assert data['limit'] == 5
    assert data['offset'] == 0

    # Test second page
    response = client.get('/api/instances?limit=5&offset=5', headers=kid_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert len(data['data']) == 5
    assert data['offset'] == 5


def test_list_instances_requires_auth(client):
    """Test that listing instances requires authentication."""
    response = client.get('/api/instances')
    assert response.status_code == 401


# ============================================================================
# GET /api/instances/{id} - Get instance details
# ============================================================================

def test_get_instance_success(client, kid_headers, assigned_instance):
    """Test getting a specific instance with details."""
    response = client.get(f'/api/instances/{assigned_instance.id}', headers=kid_headers)

    assert response.status_code == 200
    data = response.get_json()

    assert 'data' in data
    assert data['data']['id'] == assigned_instance.id
    assert data['data']['status'] == 'assigned'
    # Should include chore details
    assert 'chore' in data['data']
    assert data['data']['chore']['name'] == 'Take out trash'


def test_get_instance_not_found(client, kid_headers):
    """Test getting a non-existent instance."""
    response = client.get('/api/instances/99999', headers=kid_headers)

    assert response.status_code == 404
    data = response.get_json()
    assert 'not found' in data['message'].lower()


def test_get_instance_requires_auth(client, assigned_instance):
    """Test that getting instance details requires authentication."""
    response = client.get(f'/api/instances/{assigned_instance.id}')
    assert response.status_code == 401


# ============================================================================
# POST /api/instances/{id}/claim - Claim chore
# ============================================================================

def test_claim_instance_success(client, kid_headers, kid_user, assigned_instance):
    """Test successfully claiming an assigned chore."""
    initial_points = kid_user.points

    response = client.post(
        f'/api/instances/{assigned_instance.id}/claim',
        headers=kid_headers,
        json={'user_id': kid_user.id}
    )

    assert response.status_code == 200
    data = response.get_json()

    assert data['data']['status'] == 'claimed'
    assert data['data']['claimed_by'] == kid_user.id
    assert data['data']['claimed_at'] is not None
    assert 'claimed successfully' in data['message'].lower()

    # Points should not change yet (only on approval)
    db.session.refresh(kid_user)
    assert kid_user.points == initial_points


def test_claim_instance_auto_detect_user(client, kid_headers, kid_user, assigned_instance):
    """Test claiming without providing user_id (auto-detect from auth)."""
    response = client.post(
        f'/api/instances/{assigned_instance.id}/claim',
        headers=kid_headers,
        json={}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['data']['claimed_by'] == kid_user.id


def test_claim_instance_already_claimed(client, kid_headers, kid_user, claimed_instance):
    """Test that claiming an already claimed chore fails."""
    response = client.post(
        f'/api/instances/{claimed_instance.id}/claim',
        headers=kid_headers,
        json={'user_id': kid_user.id}
    )

    assert response.status_code == 400
    data = response.get_json()
    assert 'claimed' in data['message'].lower()


def test_claim_instance_not_assigned(client, kid_user_2, assigned_instance):
    """Test that claiming a chore you're not assigned to fails."""
    # kid_user_2 is NOT assigned to this chore
    headers = {'X-Ingress-User': kid_user_2.ha_user_id}

    response = client.post(
        f'/api/instances/{assigned_instance.id}/claim',
        headers=headers,
        json={'user_id': kid_user_2.id}
    )

    assert response.status_code == 403
    data = response.get_json()
    assert 'not assigned' in data['message'].lower()


def test_claim_instance_not_found(client, kid_headers, kid_user):
    """Test claiming a non-existent instance."""
    response = client.post(
        '/api/instances/99999/claim',
        headers=kid_headers,
        json={'user_id': kid_user.id}
    )

    assert response.status_code == 404


def test_claim_instance_requires_auth(client, assigned_instance):
    """Test that claiming requires authentication."""
    response = client.post(
        f'/api/instances/{assigned_instance.id}/claim',
        json={}
    )
    assert response.status_code == 401


# ============================================================================
# POST /api/instances/{id}/approve - Approve chore
# ============================================================================

def test_approve_instance_success(client, parent_headers, parent_user, kid_user, claimed_instance):
    """Test successfully approving a claimed chore and awarding points."""
    initial_points = kid_user.points

    response = client.post(
        f'/api/instances/{claimed_instance.id}/approve',
        headers=parent_headers,
        json={'approver_id': parent_user.id}
    )

    assert response.status_code == 200
    data = response.get_json()

    assert data['data']['status'] == 'approved'
    assert data['data']['approved_by'] == parent_user.id
    assert data['data']['approved_at'] is not None
    assert data['data']['points_awarded'] == 5
    assert 'approved' in data['message'].lower()
    assert '5 points' in data['message'].lower()

    # Verify points were awarded
    db.session.refresh(kid_user)
    assert kid_user.points == initial_points + 5

    # Verify points history entry was created
    history = PointsHistory.query.filter_by(
        user_id=kid_user.id,
        chore_instance_id=claimed_instance.id
    ).first()
    assert history is not None
    assert history.points_delta == 5
    assert history.created_by == parent_user.id
    assert 'Take out trash' in history.reason


def test_approve_instance_with_custom_points(client, parent_headers, parent_user, kid_user, claimed_instance):
    """Test approving with custom points (bonus/penalty)."""
    initial_points = kid_user.points

    response = client.post(
        f'/api/instances/{claimed_instance.id}/approve',
        headers=parent_headers,
        json={'approver_id': parent_user.id, 'points': 10}  # Double points as bonus
    )

    assert response.status_code == 200
    data = response.get_json()

    assert data['data']['points_awarded'] == 10

    # Verify custom points were awarded
    db.session.refresh(kid_user)
    assert kid_user.points == initial_points + 10


def test_approve_instance_auto_detect_parent(client, parent_headers, parent_user, claimed_instance):
    """Test approving without providing approver_id (auto-detect from auth)."""
    response = client.post(
        f'/api/instances/{claimed_instance.id}/approve',
        headers=parent_headers,
        json={}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['data']['approved_by'] == parent_user.id


def test_approve_instance_not_claimed(client, parent_headers, parent_user, assigned_instance):
    """Test that approving an assigned (not claimed) chore fails."""
    response = client.post(
        f'/api/instances/{assigned_instance.id}/approve',
        headers=parent_headers,
        json={'approver_id': parent_user.id}
    )

    assert response.status_code == 400
    data = response.get_json()
    assert 'claimed' in data['message'].lower()


def test_approve_instance_kid_cannot_approve(client, kid_headers, kid_user, claimed_instance):
    """Test that kids cannot approve their own chores."""
    response = client.post(
        f'/api/instances/{claimed_instance.id}/approve',
        headers=kid_headers,
        json={'approver_id': kid_user.id}
    )

    assert response.status_code == 403
    data = response.get_json()
    assert 'parent' in data['message'].lower()


def test_approve_instance_not_found(client, parent_headers, parent_user):
    """Test approving a non-existent instance."""
    response = client.post(
        '/api/instances/99999/approve',
        headers=parent_headers,
        json={'approver_id': parent_user.id}
    )

    assert response.status_code == 404


def test_approve_instance_requires_auth(client, claimed_instance):
    """Test that approving requires authentication."""
    response = client.post(
        f'/api/instances/{claimed_instance.id}/approve',
        json={}
    )
    assert response.status_code == 401


# ============================================================================
# POST /api/instances/{id}/reject - Reject chore
# ============================================================================

def test_reject_instance_success(client, parent_headers, parent_user, kid_user, claimed_instance):
    """Test successfully rejecting a claimed chore."""
    initial_points = kid_user.points

    response = client.post(
        f'/api/instances/{claimed_instance.id}/reject',
        headers=parent_headers,
        json={
            'approver_id': parent_user.id,
            'reason': 'Trash was not taken to curb, left in driveway'
        }
    )

    assert response.status_code == 200
    data = response.get_json()

    # After rejection, status should be 'assigned' to allow re-claim
    assert data['data']['status'] == 'assigned'
    assert data['data']['rejected_by'] == parent_user.id
    assert data['data']['rejected_at'] is not None
    assert data['data']['rejection_reason'] == 'Trash was not taken to curb, left in driveway'
    # Claim data should be cleared
    assert data['data']['claimed_by'] is None
    assert data['data']['claimed_at'] is None
    assert 'rejected' in data['message'].lower()

    # Points should not change on rejection
    db.session.refresh(kid_user)
    assert kid_user.points == initial_points


def test_reject_instance_can_reclaim_after(client, parent_headers, kid_headers, parent_user, kid_user, claimed_instance):
    """Test that a chore can be re-claimed after rejection."""
    # First reject
    response = client.post(
        f'/api/instances/{claimed_instance.id}/reject',
        headers=parent_headers,
        json={
            'approver_id': parent_user.id,
            'reason': 'Needs improvement'
        }
    )
    assert response.status_code == 200

    # Verify status is 'assigned'
    db.session.refresh(claimed_instance)
    assert claimed_instance.status == 'assigned'

    # Now kid can re-claim
    response = client.post(
        f'/api/instances/{claimed_instance.id}/claim',
        headers=kid_headers,
        json={'user_id': kid_user.id}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['data']['status'] == 'claimed'


def test_reject_instance_missing_reason(client, parent_headers, parent_user, claimed_instance):
    """Test that rejection requires a reason."""
    response = client.post(
        f'/api/instances/{claimed_instance.id}/reject',
        headers=parent_headers,
        json={'approver_id': parent_user.id}
    )

    assert response.status_code == 400
    data = response.get_json()
    assert 'reason' in data['message'].lower()


def test_reject_instance_empty_reason(client, parent_headers, parent_user, claimed_instance):
    """Test that rejection reason cannot be empty."""
    response = client.post(
        f'/api/instances/{claimed_instance.id}/reject',
        headers=parent_headers,
        json={'approver_id': parent_user.id, 'reason': '   '}
    )

    assert response.status_code == 400
    data = response.get_json()
    assert 'reason' in data['message'].lower()


def test_reject_instance_not_claimed(client, parent_headers, parent_user, assigned_instance):
    """Test that rejecting an assigned (not claimed) chore fails."""
    response = client.post(
        f'/api/instances/{assigned_instance.id}/reject',
        headers=parent_headers,
        json={'approver_id': parent_user.id, 'reason': 'Test reason'}
    )

    assert response.status_code == 400
    data = response.get_json()
    assert 'claimed' in data['message'].lower()


def test_reject_instance_kid_cannot_reject(client, kid_headers, kid_user, claimed_instance):
    """Test that kids cannot reject chores."""
    response = client.post(
        f'/api/instances/{claimed_instance.id}/reject',
        headers=kid_headers,
        json={'approver_id': kid_user.id, 'reason': 'Test reason'}
    )

    assert response.status_code == 403
    data = response.get_json()
    assert 'parent' in data['message'].lower()


def test_reject_instance_not_found(client, parent_headers, parent_user):
    """Test rejecting a non-existent instance."""
    response = client.post(
        '/api/instances/99999/reject',
        headers=parent_headers,
        json={'approver_id': parent_user.id, 'reason': 'Test'}
    )

    assert response.status_code == 404


def test_reject_instance_requires_auth(client, claimed_instance):
    """Test that rejecting requires authentication."""
    response = client.post(
        f'/api/instances/{claimed_instance.id}/reject',
        json={'reason': 'Test'}
    )
    assert response.status_code == 401


# ============================================================================
# Integration Tests - Full Workflow
# ============================================================================

def test_full_workflow_claim_approve(client, parent_headers, kid_headers, parent_user, kid_user, assigned_instance):
    """Test complete workflow: assign → claim → approve."""
    initial_points = kid_user.points

    # Step 1: Kid claims the chore
    response = client.post(
        f'/api/instances/{assigned_instance.id}/claim',
        headers=kid_headers,
        json={'user_id': kid_user.id}
    )
    assert response.status_code == 200
    assert response.get_json()['data']['status'] == 'claimed'

    # Step 2: Parent approves
    response = client.post(
        f'/api/instances/{assigned_instance.id}/approve',
        headers=parent_headers,
        json={'approver_id': parent_user.id}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data['data']['status'] == 'approved'

    # Step 3: Verify points awarded
    db.session.refresh(kid_user)
    assert kid_user.points == initial_points + 5

    # Step 4: Verify cannot claim again
    response = client.post(
        f'/api/instances/{assigned_instance.id}/claim',
        headers=kid_headers,
        json={'user_id': kid_user.id}
    )
    assert response.status_code == 400


def test_full_workflow_claim_reject_reclaim_approve(client, parent_headers, kid_headers, parent_user, kid_user, assigned_instance):
    """Test complete workflow: assign → claim → reject → claim → approve."""
    initial_points = kid_user.points

    # Step 1: Kid claims the chore
    response = client.post(
        f'/api/instances/{assigned_instance.id}/claim',
        headers=kid_headers,
        json={'user_id': kid_user.id}
    )
    assert response.status_code == 200

    # Step 2: Parent rejects
    response = client.post(
        f'/api/instances/{assigned_instance.id}/reject',
        headers=parent_headers,
        json={'approver_id': parent_user.id, 'reason': 'Not done properly'}
    )
    assert response.status_code == 200
    assert response.get_json()['data']['status'] == 'assigned'

    # Step 3: Kid re-claims
    response = client.post(
        f'/api/instances/{assigned_instance.id}/claim',
        headers=kid_headers,
        json={'user_id': kid_user.id}
    )
    assert response.status_code == 200
    assert response.get_json()['data']['status'] == 'claimed'

    # Step 4: Parent approves
    response = client.post(
        f'/api/instances/{assigned_instance.id}/approve',
        headers=parent_headers,
        json={'approver_id': parent_user.id}
    )
    assert response.status_code == 200

    # Step 5: Verify points awarded
    db.session.refresh(kid_user)
    assert kid_user.points == initial_points + 5


def test_workflow_prevents_invalid_transitions(client, parent_headers, kid_headers, parent_user, kid_user, assigned_instance):
    """Test that invalid state transitions are prevented."""
    # Cannot approve before claiming
    response = client.post(
        f'/api/instances/{assigned_instance.id}/approve',
        headers=parent_headers,
        json={'approver_id': parent_user.id}
    )
    assert response.status_code == 400

    # Cannot reject before claiming
    response = client.post(
        f'/api/instances/{assigned_instance.id}/reject',
        headers=parent_headers,
        json={'approver_id': parent_user.id, 'reason': 'Test'}
    )
    assert response.status_code == 400


def test_points_history_tracking(client, parent_headers, kid_headers, parent_user, kid_user, assigned_instance):
    """Test that points history is correctly created on approval."""
    # Claim and approve
    client.post(
        f'/api/instances/{assigned_instance.id}/claim',
        headers=kid_headers,
        json={'user_id': kid_user.id}
    )

    client.post(
        f'/api/instances/{assigned_instance.id}/approve',
        headers=parent_headers,
        json={'approver_id': parent_user.id}
    )

    # Check points history
    history_entries = PointsHistory.query.filter_by(
        user_id=kid_user.id,
        chore_instance_id=assigned_instance.id
    ).all()

    assert len(history_entries) == 1
    assert history_entries[0].points_delta == 5
    assert history_entries[0].created_by == parent_user.id
    assert 'Take out trash' in history_entries[0].reason


# Phase 1 Feature Tests: Late Claims and Missed Status


def test_missed_status_allowed(db_session, sample_chore, parent_user, kid_user):
    """Test that 'missed' is a valid status in the database."""
    # Create instance with missed status
    instance = ChoreInstance(
        chore_id=sample_chore.id,
        due_date=date.today() - timedelta(days=2),
        assigned_to=kid_user.id,
        status='missed'
    )
    db_session.add(instance)
    db_session.commit()

    # Verify it was saved correctly
    saved_instance = ChoreInstance.query.get(instance.id)
    assert saved_instance.status == 'missed'


def test_can_claim_checks_assigned_to_field(db_session, parent_user):
    """Test that can_claim() validates assigned_to for individual chores."""
    from models import Chore, User

    # Create two kids
    kid1 = User(ha_user_id='test_kid1', username='Kid 1', role='kid')
    kid2 = User(ha_user_id='test_kid2', username='Kid 2', role='kid')
    db_session.add_all([kid1, kid2])
    db_session.flush()

    chore = Chore(
        name='Individual Chore',
        points=10,
        recurrence_type='none',
        assignment_type='individual',
        created_by=parent_user.id,
        is_active=True
    )
    db_session.add(chore)
    db_session.flush()

    # Create assignment for kid1
    assignment = ChoreAssignment(chore_id=chore.id, user_id=kid1.id)
    db_session.add(assignment)

    # Create instance assigned to kid1
    instance = ChoreInstance(
        chore_id=chore.id,
        due_date=date.today(),
        assigned_to=kid1.id,
        status='assigned'
    )
    db_session.add(instance)
    db_session.commit()

    # Kid1 should be able to claim
    assert instance.can_claim(kid1.id) is True

    # Kid2 should NOT be able to claim
    assert instance.can_claim(kid2.id) is False


def test_can_claim_prevents_late_claim_when_not_allowed(db_session, parent_user, kid_user):
    """Test that can_claim() prevents late claims when allow_late_claims=False."""
    from models import Chore

    chore = Chore(
        name='Strict Deadline Chore',
        points=10,
        recurrence_type='none',
        assignment_type='individual',
        allow_late_claims=False,
        created_by=parent_user.id,
        is_active=True
    )
    db_session.add(chore)
    db_session.flush()

    # Create assignment
    assignment = ChoreAssignment(chore_id=chore.id, user_id=kid_user.id)
    db_session.add(assignment)

    # Create instance due yesterday
    instance = ChoreInstance(
        chore_id=chore.id,
        due_date=date.today() - timedelta(days=1),
        assigned_to=kid_user.id,
        status='assigned'
    )
    db_session.add(instance)
    db_session.commit()

    # Should not be able to claim
    assert instance.can_claim(kid_user.id) is False


def test_can_claim_allows_late_claim_when_allowed(db_session, parent_user, kid_user):
    """Test that can_claim() allows late claims when allow_late_claims=True."""
    from models import Chore

    chore = Chore(
        name='Flexible Chore',
        points=10,
        recurrence_type='none',
        assignment_type='individual',
        allow_late_claims=True,
        late_points=5,
        created_by=parent_user.id,
        is_active=True
    )
    db_session.add(chore)
    db_session.flush()

    # Create assignment
    assignment = ChoreAssignment(chore_id=chore.id, user_id=kid_user.id)
    db_session.add(assignment)

    # Create instance due yesterday
    instance = ChoreInstance(
        chore_id=chore.id,
        due_date=date.today() - timedelta(days=1),
        assigned_to=kid_user.id,
        status='assigned'
    )
    db_session.add(instance)
    db_session.commit()

    # Should be able to claim
    assert instance.can_claim(kid_user.id) is True


def test_award_points_uses_late_points_when_claimed_late(db_session, parent_user, kid_user):
    """Test that award_points() uses late_points when claimed_late=True."""
    from models import Chore

    chore = Chore(
        name='Chore with Late Points',
        points=10,
        recurrence_type='none',
        assignment_type='individual',
        allow_late_claims=True,
        late_points=5,
        created_by=parent_user.id,
        is_active=True
    )
    db_session.add(chore)
    db_session.flush()

    # Create instance that was claimed late
    instance = ChoreInstance(
        chore_id=chore.id,
        due_date=date.today() - timedelta(days=1),
        assigned_to=kid_user.id,
        status='claimed',
        claimed_by=kid_user.id,
        claimed_at=datetime.utcnow(),
        claimed_late=True
    )
    db_session.add(instance)
    db_session.commit()

    # Award points
    instance.award_points(parent_user.id)

    # Should award late_points, not regular points
    assert instance.points_awarded == 5


def test_award_points_uses_regular_points_when_not_late(db_session, parent_user, kid_user):
    """Test that award_points() uses regular points when claimed_late=False."""
    from models import Chore

    chore = Chore(
        name='Chore with Late Points',
        points=10,
        recurrence_type='none',
        assignment_type='individual',
        allow_late_claims=True,
        late_points=5,
        created_by=parent_user.id,
        is_active=True
    )
    db_session.add(chore)
    db_session.flush()

    # Create instance that was claimed on time
    instance = ChoreInstance(
        chore_id=chore.id,
        due_date=date.today(),
        assigned_to=kid_user.id,
        status='claimed',
        claimed_by=kid_user.id,
        claimed_at=datetime.utcnow(),
        claimed_late=False
    )
    db_session.add(instance)
    db_session.commit()

    # Award points
    instance.award_points(parent_user.id)

    # Should award regular points
    assert instance.points_awarded == 10


def test_award_points_respects_parent_override(db_session, parent_user, kid_user):
    """Test that award_points() respects parent override even for late claims."""
    from models import Chore

    chore = Chore(
        name='Chore with Late Points',
        points=10,
        recurrence_type='none',
        assignment_type='individual',
        allow_late_claims=True,
        late_points=5,
        created_by=parent_user.id,
        is_active=True
    )
    db_session.add(chore)
    db_session.flush()

    # Create instance that was claimed late
    instance = ChoreInstance(
        chore_id=chore.id,
        due_date=date.today() - timedelta(days=1),
        assigned_to=kid_user.id,
        status='claimed',
        claimed_by=kid_user.id,
        claimed_at=datetime.utcnow(),
        claimed_late=True
    )
    db_session.add(instance)
    db_session.commit()

    # Award points with parent override
    instance.award_points(parent_user.id, points=8)

    # Should award override points, not late_points
    assert instance.points_awarded == 8


# Phase 2 Tests: Unclaim and Reassign Endpoints

def test_unclaim_instance_success(client, db_session, kid_user, parent_user):
    """Test successfully unclaiming a chore."""
    from models import Chore, ChoreInstance, ChoreAssignment

    # Create chore and instance
    chore = Chore(
        name='Test Chore',
        points=10,
        recurrence_type='none',
        assignment_type='individual',
        created_by=parent_user.id,
        is_active=True
    )
    db_session.add(chore)
    db_session.flush()

    assignment = ChoreAssignment(chore_id=chore.id, user_id=kid_user.id)
    db_session.add(assignment)

    instance = ChoreInstance(
        chore_id=chore.id,
        due_date=date.today(),
        assigned_to=kid_user.id,
        status='claimed',
        claimed_by=kid_user.id,
        claimed_at=datetime.utcnow()
    )
    db_session.add(instance)
    db_session.commit()

    # Unclaim
    response = client.post(
        f'/api/instances/{instance.id}/unclaim',
        json={'user_id': kid_user.id},
        headers={'X-Ingress-User': kid_user.ha_user_id}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['data']['status'] == 'assigned'
    assert data['data']['claimed_by'] is None
    assert data['data']['claimed_late'] is False


def test_unclaim_instance_not_your_claim(client, db_session, parent_user):
    """Test that users can't unclaim others' chores."""
    from models import Chore, ChoreInstance, User

    kid1 = User(ha_user_id='unclaim_kid1', username='Kid 1', role='kid')
    kid2 = User(ha_user_id='unclaim_kid2', username='Kid 2', role='kid')
    db_session.add_all([kid1, kid2])
    db_session.flush()

    chore = Chore(
        name='Test Chore',
        points=10,
        recurrence_type='none',
        assignment_type='individual',
        created_by=parent_user.id,
        is_active=True
    )
    db_session.add(chore)
    db_session.flush()

    instance = ChoreInstance(
        chore_id=chore.id,
        due_date=date.today(),
        assigned_to=kid1.id,
        status='claimed',
        claimed_by=kid1.id,
        claimed_at=datetime.utcnow()
    )
    db_session.add(instance)
    db_session.commit()

    # Kid2 tries to unclaim kid1's chore
    response = client.post(
        f'/api/instances/{instance.id}/unclaim',
        json={'user_id': kid2.id},
        headers={'X-Ingress-User': 'unclaim_kid2'}
    )

    assert response.status_code == 403
    assert 'Not your claim' in response.get_json()['message']


def test_reassign_instance_success(client, db_session, parent_user):
    """Test successfully reassigning a chore."""
    from models import Chore, ChoreInstance, ChoreAssignment, User

    kid1 = User(ha_user_id='reassign_kid1', username='Kid 1', role='kid')
    kid2 = User(ha_user_id='reassign_kid2', username='Kid 2', role='kid')
    db_session.add_all([kid1, kid2])
    db_session.flush()

    chore = Chore(
        name='Test Chore',
        points=10,
        recurrence_type='none',
        assignment_type='individual',
        created_by=parent_user.id,
        is_active=True
    )
    db_session.add(chore)
    db_session.flush()

    # Assign to kid1
    assignment1 = ChoreAssignment(chore_id=chore.id, user_id=kid1.id)
    db_session.add(assignment1)

    instance = ChoreInstance(
        chore_id=chore.id,
        due_date=date.today(),
        assigned_to=kid1.id,
        status='assigned'
    )
    db_session.add(instance)
    db_session.commit()

    # Reassign to kid2
    response = client.post(
        f'/api/instances/{instance.id}/reassign',
        json={'new_user_id': kid2.id, 'reassigned_by': parent_user.id},
        headers={'X-Ingress-User': parent_user.ha_user_id}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['data']['assigned_to'] == kid2.id

    # Verify ChoreAssignment created
    assignment2 = ChoreAssignment.query.filter_by(
        chore_id=chore.id,
        user_id=kid2.id
    ).first()
    assert assignment2 is not None


def test_reassign_instance_only_parents(client, db_session, parent_user):
    """Test that only parents can reassign chores."""
    from models import Chore, ChoreInstance, User

    kid1 = User(ha_user_id='reassign_only_kid1', username='Kid 1', role='kid')
    kid2 = User(ha_user_id='reassign_only_kid2', username='Kid 2', role='kid')
    db_session.add_all([kid1, kid2])
    db_session.flush()

    chore = Chore(
        name='Test Chore',
        points=10,
        recurrence_type='none',
        assignment_type='individual',
        created_by=parent_user.id,
        is_active=True
    )
    db_session.add(chore)
    db_session.flush()

    instance = ChoreInstance(
        chore_id=chore.id,
        due_date=date.today(),
        assigned_to=kid1.id,
        status='assigned'
    )
    db_session.add(instance)
    db_session.commit()

    # Kid tries to reassign
    response = client.post(
        f'/api/instances/{instance.id}/reassign',
        json={'new_user_id': kid2.id, 'reassigned_by': kid1.id},
        headers={'X-Ingress-User': 'reassign_only_kid1'}
    )

    assert response.status_code == 403
    assert 'Only parents' in response.get_json()['message']


def test_reassign_instance_only_individual_chores(client, db_session, parent_user):
    """Test that only individual chores can be reassigned."""
    from models import Chore, ChoreInstance, User

    kid1 = User(ha_user_id='reassign_ind_kid1', username='Kid 1', role='kid')
    db_session.add(kid1)
    db_session.flush()

    # Create shared chore
    chore = Chore(
        name='Shared Chore',
        points=10,
        recurrence_type='none',
        assignment_type='shared',
        created_by=parent_user.id,
        is_active=True
    )
    db_session.add(chore)
    db_session.flush()

    instance = ChoreInstance(
        chore_id=chore.id,
        due_date=date.today(),
        assigned_to=None,  # Shared chore
        status='assigned'
    )
    db_session.add(instance)
    db_session.commit()

    # Try to reassign
    response = client.post(
        f'/api/instances/{instance.id}/reassign',
        json={'new_user_id': kid1.id, 'reassigned_by': parent_user.id},
        headers={'X-Ingress-User': parent_user.ha_user_id}
    )

    assert response.status_code == 400
    assert 'individual chores' in response.get_json()['message']


# ============================================================================
# GET /api/instances/due-today - Get instances due today
# ============================================================================

def test_get_instances_due_today_success(client, db_session, kid_headers, parent_user, kid_user):
    """Test getting instances due today."""
    from models import Chore, ChoreInstance, ChoreAssignment

    chore = Chore(
        name='Test Chore',
        points=10,
        recurrence_type='none',
        assignment_type='individual',
        created_by=parent_user.id,
        is_active=True
    )
    db_session.add(chore)
    db_session.flush()

    assignment = ChoreAssignment(chore_id=chore.id, user_id=kid_user.id)
    db_session.add(assignment)

    # Create instance due today
    today_instance = ChoreInstance(
        chore_id=chore.id,
        due_date=date.today(),
        assigned_to=kid_user.id,
        status='assigned'
    )
    # Create instance due tomorrow
    tomorrow_instance = ChoreInstance(
        chore_id=chore.id,
        due_date=date.today() + timedelta(days=1),
        assigned_to=kid_user.id,
        status='assigned'
    )
    db_session.add_all([today_instance, tomorrow_instance])
    db_session.commit()

    response = client.get('/api/instances/due-today', headers=kid_headers)

    assert response.status_code == 200
    data = response.get_json()
    assert data['date'] == date.today().isoformat()
    assert data['count'] == 1
    assert len(data['instances']) == 1
    assert data['instances'][0]['id'] == today_instance.id


def test_get_instances_due_today_includes_null_due_date(client, db_session, kid_headers, parent_user, kid_user):
    """Test that instances with null due date are included."""
    from models import Chore, ChoreInstance, ChoreAssignment

    chore = Chore(
        name='Anytime Chore',
        points=5,
        recurrence_type='none',
        assignment_type='individual',
        created_by=parent_user.id,
        is_active=True
    )
    db_session.add(chore)
    db_session.flush()

    assignment = ChoreAssignment(chore_id=chore.id, user_id=kid_user.id)
    db_session.add(assignment)

    # Create instance with null due date
    instance = ChoreInstance(
        chore_id=chore.id,
        due_date=None,  # Anytime chore
        assigned_to=kid_user.id,
        status='assigned'
    )
    db_session.add(instance)
    db_session.commit()

    response = client.get('/api/instances/due-today', headers=kid_headers)

    assert response.status_code == 200
    data = response.get_json()
    assert data['count'] == 1
    assert data['instances'][0]['due_date'] is None


def test_get_instances_due_today_filter_by_user(client, db_session, kid_headers, parent_user, kid_user):
    """Test filtering instances by user_id."""
    from models import Chore, ChoreInstance, ChoreAssignment, User

    kid2 = User(ha_user_id='due_today_kid2', username='Kid 2', role='kid')
    db_session.add(kid2)
    db_session.flush()

    chore = Chore(
        name='Test Chore',
        points=10,
        recurrence_type='none',
        assignment_type='individual',
        created_by=parent_user.id,
        is_active=True
    )
    db_session.add(chore)
    db_session.flush()

    # Create assignments for both kids
    assignment1 = ChoreAssignment(chore_id=chore.id, user_id=kid_user.id)
    assignment2 = ChoreAssignment(chore_id=chore.id, user_id=kid2.id)
    db_session.add_all([assignment1, assignment2])

    # Create instances for both kids
    instance1 = ChoreInstance(
        chore_id=chore.id,
        due_date=date.today(),
        assigned_to=kid_user.id,
        status='assigned'
    )
    instance2 = ChoreInstance(
        chore_id=chore.id,
        due_date=date.today(),
        assigned_to=kid2.id,
        status='assigned'
    )
    db_session.add_all([instance1, instance2])
    db_session.commit()

    response = client.get(f'/api/instances/due-today?user_id={kid_user.id}', headers=kid_headers)

    assert response.status_code == 200
    data = response.get_json()
    assert data['count'] == 1
    assert data['instances'][0]['assigned_to'] == kid_user.id


def test_get_instances_due_today_filter_by_status(client, db_session, kid_headers, parent_user, kid_user):
    """Test filtering instances by status."""
    from models import Chore, ChoreInstance, ChoreAssignment

    chore = Chore(
        name='Test Chore',
        points=10,
        recurrence_type='none',
        assignment_type='individual',
        created_by=parent_user.id,
        is_active=True
    )
    db_session.add(chore)
    db_session.flush()

    assignment = ChoreAssignment(chore_id=chore.id, user_id=kid_user.id)
    db_session.add(assignment)

    # Create assigned and claimed instances
    assigned = ChoreInstance(
        chore_id=chore.id,
        due_date=date.today(),
        assigned_to=kid_user.id,
        status='assigned'
    )
    claimed = ChoreInstance(
        chore_id=chore.id,
        due_date=date.today(),
        assigned_to=kid_user.id,
        status='claimed',
        claimed_by=kid_user.id,
        claimed_at=datetime.utcnow()
    )
    db_session.add_all([assigned, claimed])
    db_session.commit()

    response = client.get('/api/instances/due-today?status=assigned', headers=kid_headers)

    assert response.status_code == 200
    data = response.get_json()
    assert data['count'] == 1
    assert data['instances'][0]['status'] == 'assigned'


def test_get_instances_due_today_requires_auth(client):
    """Test that getting due today instances requires authentication."""
    response = client.get('/api/instances/due-today')
    assert response.status_code == 401


def test_get_instances_due_today_includes_shared_chores(client, db_session, kid_headers, parent_user, kid_user):
    """Test that shared chores (assigned_to=None) are included in filtered results."""
    from models import Chore, ChoreInstance, ChoreAssignment

    chore = Chore(
        name='Shared Chore',
        points=10,
        recurrence_type='none',
        assignment_type='shared',
        created_by=parent_user.id,
        is_active=True
    )
    db_session.add(chore)
    db_session.flush()

    # Create shared chore assignment
    assignment = ChoreAssignment(chore_id=chore.id, user_id=kid_user.id)
    db_session.add(assignment)

    # Shared instance has assigned_to=None
    instance = ChoreInstance(
        chore_id=chore.id,
        due_date=date.today(),
        assigned_to=None,
        status='assigned'
    )
    db_session.add(instance)
    db_session.commit()

    # Filter by user_id should still include shared chores
    response = client.get(f'/api/instances/due-today?user_id={kid_user.id}', headers=kid_headers)

    assert response.status_code == 200
    data = response.get_json()
    assert data['count'] == 1
    assert data['instances'][0]['assigned_to'] is None
