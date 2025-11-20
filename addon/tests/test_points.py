"""Tests for points API endpoints."""

import pytest
from models import db, User, PointsHistory


class TestAdjustPoints:
    """Tests for POST /api/points/adjust endpoint."""

    def test_adjust_points_add_success(self, client, parent_headers, kid_user, parent_user, db_session):
        """Test successfully adding points."""
        adjustment_data = {
            'user_id': kid_user.id,
            'points_delta': 10,
            'reason': 'Bonus for good behavior'
        }

        response = client.post('/api/points/adjust', json=adjustment_data, headers=parent_headers)
        assert response.status_code == 200

        data = response.get_json()
        assert data['data']['user_id'] == kid_user.id
        assert data['data']['old_balance'] == 50
        assert data['data']['new_balance'] == 60
        assert data['data']['points_delta'] == 10
        assert data['data']['reason'] == 'Bonus for good behavior'
        assert data['data']['adjusted_by'] == parent_user.username

        # Verify points were updated in database
        db_session.refresh(kid_user)
        assert kid_user.points == 60

    def test_adjust_points_subtract_success(self, client, parent_headers, kid_user, db_session):
        """Test successfully subtracting points."""
        adjustment_data = {
            'user_id': kid_user.id,
            'points_delta': -10,
            'reason': 'Broke a rule'
        }

        response = client.post('/api/points/adjust', json=adjustment_data, headers=parent_headers)
        assert response.status_code == 200

        data = response.get_json()
        assert data['data']['old_balance'] == 50
        assert data['data']['new_balance'] == 40
        assert data['data']['points_delta'] == -10

        # Verify points were updated
        db_session.refresh(kid_user)
        assert kid_user.points == 40

    def test_adjust_points_can_go_negative(self, client, parent_headers, kid_user, db_session):
        """Test that points can go negative."""
        adjustment_data = {
            'user_id': kid_user.id,
            'points_delta': -100,
            'reason': 'Major penalty'
        }

        response = client.post('/api/points/adjust', json=adjustment_data, headers=parent_headers)
        assert response.status_code == 200

        data = response.get_json()
        assert data['data']['new_balance'] == -50

        db_session.refresh(kid_user)
        assert kid_user.points == -50

    def test_adjust_points_creates_history_entry(self, client, parent_headers, kid_user, parent_user, db_session):
        """Test that adjustment creates points history entry."""
        adjustment_data = {
            'user_id': kid_user.id,
            'points_delta': 15,
            'reason': 'Manual adjustment'
        }

        response = client.post('/api/points/adjust', json=adjustment_data, headers=parent_headers)
        assert response.status_code == 200

        # Check history was created
        history = PointsHistory.query.filter_by(
            user_id=kid_user.id,
            points_delta=15
        ).first()
        assert history is not None
        assert history.reason == 'Manual adjustment'
        assert history.created_by == parent_user.id
        assert history.chore_instance_id is None
        assert history.reward_claim_id is None

    def test_adjust_points_requires_parent(self, client, kid_headers, kid_user):
        """Test that only parents can adjust points."""
        adjustment_data = {
            'user_id': kid_user.id,
            'points_delta': 100,
            'reason': 'Trying to cheat'
        }

        response = client.post('/api/points/adjust', json=adjustment_data, headers=kid_headers)
        assert response.status_code == 403
        assert 'Only parents' in response.get_json()['message']

    def test_adjust_points_missing_fields(self, client, parent_headers):
        """Test that missing required fields returns error."""
        response = client.post('/api/points/adjust', json={}, headers=parent_headers)
        assert response.status_code == 400
        assert 'Missing required fields' in response.get_json()['message']

    def test_adjust_points_zero_delta(self, client, parent_headers, kid_user):
        """Test that zero points_delta is rejected."""
        adjustment_data = {
            'user_id': kid_user.id,
            'points_delta': 0,
            'reason': 'Nothing'
        }

        response = client.post('/api/points/adjust', json=adjustment_data, headers=parent_headers)
        assert response.status_code == 400
        assert 'cannot be zero' in response.get_json()['message']

    def test_adjust_points_invalid_delta(self, client, parent_headers, kid_user):
        """Test that invalid points_delta type is rejected."""
        adjustment_data = {
            'user_id': kid_user.id,
            'points_delta': 'not a number',
            'reason': 'Test'
        }

        response = client.post('/api/points/adjust', json=adjustment_data, headers=parent_headers)
        assert response.status_code == 400
        assert 'must be a valid integer' in response.get_json()['message']

    def test_adjust_points_user_not_found(self, client, parent_headers):
        """Test adjusting points for non-existent user."""
        adjustment_data = {
            'user_id': 999,
            'points_delta': 10,
            'reason': 'Test'
        }

        response = client.post('/api/points/adjust', json=adjustment_data, headers=parent_headers)
        assert response.status_code == 404
        assert 'not found' in response.get_json()['message']

    def test_adjust_points_only_for_kids(self, client, parent_headers, parent_user):
        """Test that points can only be adjusted for kids, not parents."""
        adjustment_data = {
            'user_id': parent_user.id,
            'points_delta': 10,
            'reason': 'Test'
        }

        response = client.post('/api/points/adjust', json=adjustment_data, headers=parent_headers)
        assert response.status_code == 400
        assert 'only adjust points for kids' in response.get_json()['message']


class TestGetPointsHistory:
    """Tests for GET /api/points/history/{user_id} endpoint."""

    def test_get_points_history_success(self, client, parent_headers, user_with_points_history, db_session):
        """Test getting points history for a user."""
        response = client.get(f'/api/points/history/{user_with_points_history.id}', headers=parent_headers)
        assert response.status_code == 200

        data = response.get_json()
        assert 'data' in data
        assert len(data['data']) == 5
        assert data['total'] == 5
        assert data['current_balance'] == user_with_points_history.points

        # Verify entries are sorted by created_at descending (newest first)
        # The last entry should be first in the response
        assert 'Mow lawn' in data['data'][0]['reason']

    def test_get_points_history_includes_creator(self, client, parent_headers, user_with_points_history, parent_user):
        """Test that history includes creator information."""
        response = client.get(f'/api/points/history/{user_with_points_history.id}', headers=parent_headers)
        assert response.status_code == 200

        data = response.get_json()
        # Find an entry with creator
        entry_with_creator = [e for e in data['data'] if 'created_by' in e][0]
        assert entry_with_creator['created_by']['id'] == parent_user.id
        assert entry_with_creator['created_by']['username'] == parent_user.username
        assert entry_with_creator['created_by']['role'] == 'parent'

    def test_get_points_history_pagination(self, client, parent_headers, user_with_points_history):
        """Test pagination of points history."""
        # Get first 2 entries
        response = client.get(
            f'/api/points/history/{user_with_points_history.id}?limit=2&offset=0',
            headers=parent_headers
        )
        assert response.status_code == 200

        data = response.get_json()
        assert len(data['data']) == 2
        assert data['limit'] == 2
        assert data['offset'] == 0
        assert data['total'] == 5

        # Get next 2 entries
        response2 = client.get(
            f'/api/points/history/{user_with_points_history.id}?limit=2&offset=2',
            headers=parent_headers
        )
        assert response2.status_code == 200

        data2 = response2.get_json()
        assert len(data2['data']) == 2
        assert data2['offset'] == 2

        # Entries should be different
        assert data['data'][0]['id'] != data2['data'][0]['id']

    def test_get_points_history_default_pagination(self, client, parent_headers, user_with_points_history):
        """Test default pagination values."""
        response = client.get(f'/api/points/history/{user_with_points_history.id}', headers=parent_headers)
        assert response.status_code == 200

        data = response.get_json()
        assert data['limit'] == 50  # Default limit
        assert data['offset'] == 0  # Default offset

    def test_get_points_history_invalid_pagination(self, client, parent_headers, kid_user):
        """Test that invalid pagination parameters are rejected."""
        # Invalid limit (too high)
        response = client.get(f'/api/points/history/{kid_user.id}?limit=2000', headers=parent_headers)
        assert response.status_code == 400

        # Negative offset
        response = client.get(f'/api/points/history/{kid_user.id}?offset=-1', headers=parent_headers)
        assert response.status_code == 400

        # Invalid limit (too low)
        response = client.get(f'/api/points/history/{kid_user.id}?limit=0', headers=parent_headers)
        assert response.status_code == 400

    def test_get_points_history_user_not_found(self, client, parent_headers):
        """Test getting history for non-existent user."""
        response = client.get('/api/points/history/999', headers=parent_headers)
        assert response.status_code == 404

    def test_get_points_history_kid_can_view_own(self, client, kid_headers, kid_user, db_session):
        """Test that kids can view their own points history."""
        # Add some history
        history = PointsHistory(
            user_id=kid_user.id,
            points_delta=10,
            reason='Test entry'
        )
        db_session.add(history)
        db_session.commit()

        response = client.get(f'/api/points/history/{kid_user.id}', headers=kid_headers)
        assert response.status_code == 200

        data = response.get_json()
        assert len(data['data']) > 0

    def test_get_points_history_kid_cannot_view_others(self, client, kid_headers, kid_user_2):
        """Test that kids cannot view other kids' history."""
        # kid_user (authenticated) trying to view kid_user_2's history
        response = client.get(f'/api/points/history/{kid_user_2.id}', headers=kid_headers)
        assert response.status_code == 403
        assert 'only view your own' in response.get_json()['message']

    def test_get_points_history_parent_can_view_any(self, client, parent_headers, kid_user, kid_user_2):
        """Test that parents can view any user's history."""
        response1 = client.get(f'/api/points/history/{kid_user.id}', headers=parent_headers)
        assert response1.status_code == 200

        response2 = client.get(f'/api/points/history/{kid_user_2.id}', headers=parent_headers)
        assert response2.status_code == 200

    def test_get_points_history_empty(self, client, parent_headers, db_session):
        """Test getting history for user with no history."""
        # Create new kid with no history
        new_kid = User(
            ha_user_id='kid-ha-003',
            username='New Kid',
            role='kid',
            points=0
        )
        db_session.add(new_kid)
        db_session.commit()

        response = client.get(f'/api/points/history/{new_kid.id}', headers=parent_headers)
        assert response.status_code == 200

        data = response.get_json()
        assert len(data['data']) == 0
        assert data['total'] == 0
        assert data['current_balance'] == 0

    def test_get_points_history_includes_references(self, client, parent_headers, kid_user, db_session):
        """Test that history includes chore_instance_id and reward_claim_id references."""
        # Add history with references
        history1 = PointsHistory(
            user_id=kid_user.id,
            points_delta=10,
            reason='Chore completion',
            chore_instance_id=1
        )
        history2 = PointsHistory(
            user_id=kid_user.id,
            points_delta=-20,
            reason='Reward claim',
            reward_claim_id=1
        )
        db_session.add(history1)
        db_session.add(history2)
        db_session.commit()

        response = client.get(f'/api/points/history/{kid_user.id}', headers=parent_headers)
        assert response.status_code == 200

        data = response.get_json()
        # Find the entries
        chore_entry = [e for e in data['data'] if e['reason'] == 'Chore completion'][0]
        reward_entry = [e for e in data['data'] if e['reason'] == 'Reward claim'][0]

        assert chore_entry['chore_instance_id'] == 1
        assert reward_entry['reward_claim_id'] == 1


class TestModelToDict:
    """Tests for model to_dict() serialization methods."""

    def test_user_to_dict(self, kid_user):
        """Test User.to_dict() method."""
        result = kid_user.to_dict()

        assert result['id'] == kid_user.id
        assert result['ha_user_id'] == kid_user.ha_user_id
        assert result['username'] == kid_user.username
        assert result['role'] == kid_user.role
        assert result['points'] == kid_user.points
        assert 'created_at' in result
        assert 'updated_at' in result

    def test_points_history_to_dict(self, db_session, kid_user, parent_user):
        """Test PointsHistory.to_dict() method."""
        history = PointsHistory(
            user_id=kid_user.id,
            points_delta=10,
            reason='Test entry',
            created_by=parent_user.id
        )
        db_session.add(history)
        db_session.commit()

        result = history.to_dict()

        assert result['id'] == history.id
        assert result['user_id'] == kid_user.id
        assert result['points_delta'] == 10
        assert result['reason'] == 'Test entry'
        assert result['created_by'] == parent_user.id
        assert 'created_at' in result

    def test_chore_to_dict(self, sample_chore):
        """Test Chore.to_dict() method."""
        result = sample_chore.to_dict()

        assert result['id'] == sample_chore.id
        assert result['name'] == sample_chore.name
        assert result['points'] == sample_chore.points
        assert result['recurrence_type'] == sample_chore.recurrence_type
        assert result['is_active'] == sample_chore.is_active
        assert 'created_at' in result
        assert 'updated_at' in result

    def test_chore_instance_to_dict(self, db_session, sample_chore, kid_user):
        """Test ChoreInstance.to_dict() method."""
        from datetime import date
        from models import ChoreInstance

        instance = ChoreInstance(
            chore_id=sample_chore.id,
            due_date=date.today(),
            assigned_to=kid_user.id,
            status='assigned'
        )
        db_session.add(instance)
        db_session.commit()

        result = instance.to_dict()

        assert result['id'] == instance.id
        assert result['chore_id'] == sample_chore.id
        assert result['chore_name'] == sample_chore.name
        assert result['status'] == 'assigned'
        assert result['assigned_to'] == kid_user.id
        assert result['assigned_to_name'] == kid_user.username
        assert 'due_date' in result

    def test_reward_to_dict(self, sample_reward):
        """Test Reward.to_dict() method."""
        result = sample_reward.to_dict()

        assert result['id'] == sample_reward.id
        assert result['name'] == sample_reward.name
        assert result['points_cost'] == sample_reward.points_cost
        assert result['cooldown_days'] == sample_reward.cooldown_days
        assert result['is_active'] == sample_reward.is_active
        assert 'created_at' in result

    def test_reward_claim_to_dict(self, db_session, sample_reward, kid_user):
        """Test RewardClaim.to_dict() method."""
        from models import RewardClaim

        claim = RewardClaim(
            reward_id=sample_reward.id,
            user_id=kid_user.id,
            points_spent=sample_reward.points_cost,
            status='approved'
        )
        db_session.add(claim)
        db_session.commit()

        result = claim.to_dict()

        assert result['id'] == claim.id
        assert result['reward_id'] == sample_reward.id
        assert result['reward_name'] == sample_reward.name
        assert result['user_id'] == kid_user.id
        assert result['user_name'] == kid_user.username
        assert result['points_spent'] == sample_reward.points_cost
        assert result['status'] == 'approved'


class TestPointsVerification:
    """Tests for points balance verification."""

    def test_verify_points_balance_correct(self, db_session, parent_user):
        """Test verification passes when points balance is correct."""
        # Create a fresh kid with 0 points to start clean
        from models import User
        kid = User(ha_user_id='verify-test-kid', username='Verify Test Kid', role='kid', points=0)
        db_session.add(kid)
        db_session.commit()

        # Add some history
        kid.adjust_points(10, 'Test 1', parent_user.id)
        kid.adjust_points(5, 'Test 2', parent_user.id)
        db_session.commit()

        # Verify balance
        assert kid.verify_points_balance() is True
        assert kid.points == 15

    def test_calculate_current_points(self, db_session, parent_user):
        """Test calculate_current_points method."""
        # Create a fresh kid with 0 points to start clean
        from models import User
        kid = User(ha_user_id='calc-test-kid', username='Calc Test Kid', role='kid', points=0)
        db_session.add(kid)
        db_session.commit()

        # Add history
        kid.adjust_points(10, 'Test 1', parent_user.id)
        kid.adjust_points(-5, 'Test 2', parent_user.id)
        db_session.commit()

        calculated = kid.calculate_current_points()
        expected = 10 - 5

        assert calculated == expected
        assert kid.points == expected
