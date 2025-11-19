"""Tests for rewards API endpoints."""

import pytest
from datetime import datetime, timedelta
from models import db, Reward, RewardClaim, User


class TestListRewards:
    """Tests for GET /api/rewards endpoint."""

    def test_list_all_rewards(self, client, parent_headers, sample_reward, db_session):
        """Test listing all rewards."""
        # Create another reward
        reward2 = Reward(
            name='Movie night',
            description='Watch a movie',
            points_cost=15,
            is_active=True
        )
        db_session.add(reward2)
        db_session.commit()

        response = client.get('/api/rewards', headers=parent_headers)
        assert response.status_code == 200

        data = response.get_json()
        assert 'data' in data
        assert len(data['data']) == 2
        assert data['data'][0]['points_cost'] == 15  # Sorted by points_cost
        assert data['data'][1]['points_cost'] == 20

    def test_list_active_rewards_only(self, client, parent_headers, sample_reward, db_session):
        """Test filtering by active status."""
        # Create inactive reward
        inactive_reward = Reward(
            name='Inactive reward',
            points_cost=10,
            is_active=False
        )
        db_session.add(inactive_reward)
        db_session.commit()

        response = client.get('/api/rewards?active=true', headers=parent_headers)
        assert response.status_code == 200

        data = response.get_json()
        assert len(data['data']) == 1
        assert data['data'][0]['name'] == 'Ice cream trip'
        assert data['data'][0]['is_active'] is True

    def test_list_rewards_includes_claim_count(self, client, parent_headers, sample_reward, kid_user, db_session):
        """Test that reward list includes total claims count."""
        # Create some claims
        claim1 = RewardClaim(
            reward_id=sample_reward.id,
            user_id=kid_user.id,
            points_spent=20,
            status='approved'
        )
        claim2 = RewardClaim(
            reward_id=sample_reward.id,
            user_id=kid_user.id,
            points_spent=20,
            status='approved'
        )
        db_session.add(claim1)
        db_session.add(claim2)
        db_session.commit()

        response = client.get('/api/rewards', headers=parent_headers)
        assert response.status_code == 200

        data = response.get_json()
        assert data['data'][0]['total_claims'] == 2

    def test_list_rewards_requires_auth(self, client):
        """Test that authentication is required."""
        response = client.get('/api/rewards')
        assert response.status_code == 401


class TestCreateReward:
    """Tests for POST /api/rewards endpoint."""

    def test_create_reward_success(self, client, parent_headers):
        """Test creating a reward successfully."""
        reward_data = {
            'name': 'New reward',
            'description': 'A test reward',
            'points_cost': 30,
            'cooldown_days': 14,
            'max_claims_total': 10,
            'max_claims_per_kid': 2
        }

        response = client.post('/api/rewards', json=reward_data, headers=parent_headers)
        assert response.status_code == 201

        data = response.get_json()
        assert data['data']['name'] == 'New reward'
        assert data['data']['points_cost'] == 30
        assert data['data']['cooldown_days'] == 14
        assert data['data']['max_claims_total'] == 10
        assert data['data']['max_claims_per_kid'] == 2
        assert data['data']['is_active'] is True

    def test_create_reward_minimal(self, client, parent_headers):
        """Test creating reward with only required fields."""
        reward_data = {
            'name': 'Simple reward',
            'points_cost': 10
        }

        response = client.post('/api/rewards', json=reward_data, headers=parent_headers)
        assert response.status_code == 201

        data = response.get_json()
        assert data['data']['name'] == 'Simple reward'
        assert data['data']['description'] is None
        assert data['data']['cooldown_days'] is None

    def test_create_reward_missing_required_fields(self, client, parent_headers):
        """Test that missing required fields returns error."""
        response = client.post('/api/rewards', json={}, headers=parent_headers)
        assert response.status_code == 400
        assert 'Missing required fields' in response.get_json()['message']

    def test_create_reward_invalid_points_cost(self, client, parent_headers):
        """Test that zero or negative points_cost is rejected."""
        reward_data = {
            'name': 'Bad reward',
            'points_cost': 0
        }

        response = client.post('/api/rewards', json=reward_data, headers=parent_headers)
        assert response.status_code == 400
        assert 'must be greater than 0' in response.get_json()['message']

    def test_create_reward_requires_parent(self, client, kid_headers):
        """Test that only parents can create rewards."""
        reward_data = {
            'name': 'Kid reward',
            'points_cost': 10
        }

        response = client.post('/api/rewards', json=reward_data, headers=kid_headers)
        assert response.status_code == 403
        assert 'Only parents' in response.get_json()['message']


class TestGetReward:
    """Tests for GET /api/rewards/{id} endpoint."""

    def test_get_reward_success(self, client, parent_headers, sample_reward):
        """Test getting reward details."""
        response = client.get(f'/api/rewards/{sample_reward.id}', headers=parent_headers)
        assert response.status_code == 200

        data = response.get_json()
        assert data['data']['id'] == sample_reward.id
        assert data['data']['name'] == 'Ice cream trip'
        assert data['data']['total_claims'] == 0

    def test_get_reward_with_cooldown_status(self, client, kid_headers, sample_reward, kid_user, db_session):
        """Test getting reward shows cooldown status for current user."""
        # Create a recent claim
        claim = RewardClaim(
            reward_id=sample_reward.id,
            user_id=kid_user.id,
            points_spent=20,
            status='approved',
            claimed_at=datetime.utcnow() - timedelta(days=2)
        )
        db_session.add(claim)
        db_session.commit()

        response = client.get(f'/api/rewards/{sample_reward.id}', headers=kid_headers)
        assert response.status_code == 200

        data = response.get_json()
        assert data['data']['is_on_cooldown_for_user'] is True
        assert data['data']['cooldown_days_remaining'] == 5

    def test_get_reward_not_found(self, client, parent_headers):
        """Test getting non-existent reward."""
        response = client.get('/api/rewards/999', headers=parent_headers)
        assert response.status_code == 404


class TestUpdateReward:
    """Tests for PUT /api/rewards/{id} endpoint."""

    def test_update_reward_success(self, client, parent_headers, sample_reward):
        """Test updating a reward."""
        update_data = {
            'name': 'Updated ice cream',
            'points_cost': 25,
            'cooldown_days': 10
        }

        response = client.put(f'/api/rewards/{sample_reward.id}', json=update_data, headers=parent_headers)
        assert response.status_code == 200

        data = response.get_json()
        assert data['data']['name'] == 'Updated ice cream'
        assert data['data']['points_cost'] == 25
        assert data['data']['cooldown_days'] == 10

    def test_update_reward_partial(self, client, parent_headers, sample_reward):
        """Test updating only some fields."""
        update_data = {'name': 'New name only'}

        response = client.put(f'/api/rewards/{sample_reward.id}', json=update_data, headers=parent_headers)
        assert response.status_code == 200

        data = response.get_json()
        assert data['data']['name'] == 'New name only'
        assert data['data']['points_cost'] == 20  # Unchanged

    def test_update_reward_requires_parent(self, client, kid_headers, sample_reward):
        """Test that only parents can update rewards."""
        response = client.put(f'/api/rewards/{sample_reward.id}', json={'name': 'Hacked'}, headers=kid_headers)
        assert response.status_code == 403


class TestDeleteReward:
    """Tests for DELETE /api/rewards/{id} endpoint."""

    def test_delete_reward_success(self, client, parent_headers, sample_reward, db_session):
        """Test soft deleting a reward."""
        response = client.delete(f'/api/rewards/{sample_reward.id}', headers=parent_headers)
        assert response.status_code == 204

        # Verify soft delete
        db_session.refresh(sample_reward)
        assert sample_reward.is_active is False

    def test_delete_reward_requires_parent(self, client, kid_headers, sample_reward):
        """Test that only parents can delete rewards."""
        response = client.delete(f'/api/rewards/{sample_reward.id}', headers=kid_headers)
        assert response.status_code == 403


class TestClaimReward:
    """Tests for POST /api/rewards/{id}/claim endpoint."""

    def test_claim_reward_success(self, client, kid_headers, sample_reward, kid_user, db_session):
        """Test successfully claiming a reward."""
        response = client.post(f'/api/rewards/{sample_reward.id}/claim', headers=kid_headers)
        assert response.status_code == 200

        data = response.get_json()
        assert data['data']['reward_id'] == sample_reward.id
        assert data['data']['user_id'] == kid_user.id
        assert data['data']['points_spent'] == 20
        assert data['data']['old_balance'] == 50
        assert data['data']['new_balance'] == 30

        # Verify points were deducted
        db_session.refresh(kid_user)
        assert kid_user.points == 30

        # Verify claim was created
        claim = RewardClaim.query.filter_by(reward_id=sample_reward.id, user_id=kid_user.id).first()
        assert claim is not None
        assert claim.status == 'approved'

    def test_claim_reward_insufficient_points(self, client, kid_headers, sample_reward, kid_user, db_session):
        """Test claiming reward with insufficient points."""
        # Reduce kid's points
        kid_user.points = 15
        db_session.commit()

        response = client.post(f'/api/rewards/{sample_reward.id}/claim', headers=kid_headers)
        assert response.status_code == 400

        data = response.get_json()
        assert 'Insufficient points' in data['message']
        assert data['details']['required'] == 20
        assert data['details']['current'] == 15

    def test_claim_reward_on_cooldown(self, client, kid_headers, sample_reward, kid_user, db_session):
        """Test claiming reward that is on cooldown."""
        # Create recent claim
        recent_claim = RewardClaim(
            reward_id=sample_reward.id,
            user_id=kid_user.id,
            points_spent=20,
            status='approved',
            claimed_at=datetime.utcnow() - timedelta(days=3)
        )
        db_session.add(recent_claim)
        db_session.commit()

        response = client.post(f'/api/rewards/{sample_reward.id}/claim', headers=kid_headers)
        assert response.status_code == 400

        data = response.get_json()
        assert 'cooldown' in data['message'].lower()
        assert data['details']['cooldown_days_remaining'] == 4

    def test_claim_reward_max_claims_per_kid(self, client, kid_headers, sample_reward, kid_user, db_session):
        """Test max claims per kid enforcement."""
        # Set max claims per kid
        sample_reward.max_claims_per_kid = 2
        db_session.commit()

        # Create 2 existing claims
        for _ in range(2):
            claim = RewardClaim(
                reward_id=sample_reward.id,
                user_id=kid_user.id,
                points_spent=20,
                status='approved',
                claimed_at=datetime.utcnow() - timedelta(days=30)  # Past cooldown
            )
            db_session.add(claim)
        db_session.commit()

        response = client.post(f'/api/rewards/{sample_reward.id}/claim', headers=kid_headers)
        assert response.status_code == 400
        assert 'maximum claims for this reward' in response.get_json()['message']

    def test_claim_reward_max_claims_total(self, client, kid_headers, sample_reward, kid_user, kid_user_2, db_session):
        """Test max claims total enforcement."""
        # Set max claims total
        sample_reward.max_claims_total = 1
        db_session.commit()

        # Kid 2 claims first
        claim = RewardClaim(
            reward_id=sample_reward.id,
            user_id=kid_user_2.id,
            points_spent=20,
            status='approved'
        )
        db_session.add(claim)
        db_session.commit()

        # Kid 1 tries to claim
        response = client.post(f'/api/rewards/{sample_reward.id}/claim', headers=kid_headers)
        assert response.status_code == 400
        assert 'reached maximum claims' in response.get_json()['message']

    def test_claim_reward_inactive(self, client, kid_headers, sample_reward, db_session):
        """Test claiming inactive reward."""
        sample_reward.is_active = False
        db_session.commit()

        response = client.post(f'/api/rewards/{sample_reward.id}/claim', headers=kid_headers)
        assert response.status_code == 400
        assert 'not active' in response.get_json()['message']

    def test_claim_reward_parent_cannot_claim(self, client, parent_headers, sample_reward, parent_user):
        """Test that parents cannot claim rewards."""
        response = client.post(f'/api/rewards/{sample_reward.id}/claim', headers=parent_headers)
        assert response.status_code == 400
        assert 'Only kids' in response.get_json()['message']

    def test_claim_reward_creates_points_history(self, client, kid_headers, sample_reward, kid_user, db_session):
        """Test that claiming reward creates points history entry."""
        response = client.post(f'/api/rewards/{sample_reward.id}/claim', headers=kid_headers)
        assert response.status_code == 200

        # Check points history
        from models import PointsHistory
        history = PointsHistory.query.filter_by(user_id=kid_user.id).first()
        assert history is not None
        assert history.points_delta == -20
        assert 'Ice cream trip' in history.reason
        assert history.reward_claim_id is not None
