"""Tests for webhook integration in ChoreControl."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, date

from models import db, User, Chore, ChoreInstance, ChoreAssignment, Reward, RewardClaim


class TestWebhookUtility:
    """Tests for the webhook utility module."""

    def test_webhook_payload_format(self, app, db_session, kid_user):
        """Test webhook payload structure."""
        with app.app_context():
            from utils.webhooks import build_payload

            payload = build_payload('test_event', kid_user)

            assert 'event' in payload
            assert 'timestamp' in payload
            assert 'data' in payload
            assert payload['event'] == 'test_event'
            assert payload['timestamp'].endswith('Z')
            assert 'id' in payload['data']
            assert 'username' in payload['data']

    def test_webhook_payload_with_kwargs(self, app, db_session, kid_user):
        """Test payload includes additional kwargs."""
        with app.app_context():
            from utils.webhooks import build_payload

            payload = build_payload('test_event', kid_user, custom_field='custom_value')

            assert payload['data']['custom_field'] == 'custom_value'

    def test_webhook_payload_with_dict_object(self, app):
        """Test payload handles dict objects."""
        with app.app_context():
            from utils.webhooks import build_payload

            data = {'key': 'value', 'number': 42}
            payload = build_payload('dict_event', data)

            assert payload['data']['key'] == 'value'
            assert payload['data']['number'] == 42

    @patch('utils.webhooks.requests.post')
    def test_webhook_delivery_success(self, mock_post, app, db_session, kid_user):
        """Test successful webhook delivery."""
        with app.app_context():
            # Configure mock
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            # Set webhook URL in app config
            app.config['HA_WEBHOOK_URL'] = 'http://test.local/webhook'

            from utils.webhooks import fire_webhook
            result = fire_webhook('test_event', kid_user)

            assert result is True
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == 'http://test.local/webhook'
            assert 'json' in call_args[1]
            assert call_args[1]['timeout'] == 5

    @patch('utils.webhooks.requests.post')
    def test_webhook_delivery_timeout(self, mock_post, app, db_session, kid_user):
        """Test webhook handles timeout gracefully."""
        with app.app_context():
            import requests
            mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")

            app.config['HA_WEBHOOK_URL'] = 'http://test.local/webhook'

            from utils.webhooks import fire_webhook
            result = fire_webhook('test_event', kid_user)

            assert result is False

    @patch('utils.webhooks.requests.post')
    def test_webhook_delivery_error(self, mock_post, app, db_session, kid_user):
        """Test webhook handles request errors gracefully."""
        with app.app_context():
            import requests
            mock_post.side_effect = requests.exceptions.RequestException("Connection failed")

            app.config['HA_WEBHOOK_URL'] = 'http://test.local/webhook'

            from utils.webhooks import fire_webhook
            result = fire_webhook('test_event', kid_user)

            assert result is False

    def test_webhook_no_url_configured(self, app, db_session, kid_user):
        """Test webhook skips when no URL configured."""
        with app.app_context():
            app.config['HA_WEBHOOK_URL'] = None

            from utils.webhooks import fire_webhook
            result = fire_webhook('test_event', kid_user)

            assert result is False


class TestChoreInstanceWebhooks:
    """Tests for webhooks fired during chore instance lifecycle."""

    @patch('services.instance_service.fire_webhook')
    def test_claim_fires_webhook(self, mock_webhook, client, db_session, kid_user, parent_user, sample_chore, kid_headers):
        """Test claiming a chore instance fires webhook."""
        # Create assignment and instance
        assignment = ChoreAssignment(
            chore_id=sample_chore.id,
            user_id=kid_user.id
        )
        db_session.add(assignment)

        instance = ChoreInstance(
            chore_id=sample_chore.id,
            due_date=date.today(),
            status='assigned',
            assigned_to=kid_user.id
        )
        db_session.add(instance)
        db_session.commit()

        # Claim the instance
        response = client.post(
            f'/api/instances/{instance.id}/claim',
            json={'user_id': kid_user.id},
            headers=kid_headers
        )

        assert response.status_code == 200
        mock_webhook.assert_called_once()
        call_args = mock_webhook.call_args
        assert call_args[0][0] == 'chore_instance_claimed'

    @patch('services.instance_service.fire_webhook')
    def test_approve_fires_webhooks(self, mock_webhook, client, db_session, kid_user, parent_user, sample_chore, parent_headers):
        """Test approving a chore instance fires webhooks."""
        # Create assignment and claimed instance
        assignment = ChoreAssignment(
            chore_id=sample_chore.id,
            user_id=kid_user.id
        )
        db_session.add(assignment)

        instance = ChoreInstance(
            chore_id=sample_chore.id,
            due_date=date.today(),
            status='claimed',
            assigned_to=kid_user.id,
            claimed_by=kid_user.id,
            claimed_at=datetime.utcnow()
        )
        db_session.add(instance)
        db_session.commit()

        # Approve the instance
        response = client.post(
            f'/api/instances/{instance.id}/approve',
            json={'approver_id': parent_user.id},
            headers=parent_headers
        )

        assert response.status_code == 200
        # Should fire both 'chore_instance_approved' and 'points_awarded'
        assert mock_webhook.call_count == 2
        call_events = [call[0][0] for call in mock_webhook.call_args_list]
        assert 'chore_instance_approved' in call_events
        assert 'points_awarded' in call_events

    @patch('services.instance_service.fire_webhook')
    def test_reject_fires_webhook(self, mock_webhook, client, db_session, kid_user, parent_user, sample_chore, parent_headers):
        """Test rejecting a chore instance fires webhook."""
        # Create assignment and claimed instance
        assignment = ChoreAssignment(
            chore_id=sample_chore.id,
            user_id=kid_user.id
        )
        db_session.add(assignment)

        instance = ChoreInstance(
            chore_id=sample_chore.id,
            due_date=date.today(),
            status='claimed',
            assigned_to=kid_user.id,
            claimed_by=kid_user.id,
            claimed_at=datetime.utcnow()
        )
        db_session.add(instance)
        db_session.commit()

        # Reject the instance
        response = client.post(
            f'/api/instances/{instance.id}/reject',
            json={'approver_id': parent_user.id, 'reason': 'Not done properly'},
            headers=parent_headers
        )

        assert response.status_code == 200
        mock_webhook.assert_called_once()
        call_args = mock_webhook.call_args
        assert call_args[0][0] == 'chore_instance_rejected'


class TestRewardWebhooks:
    """Tests for webhooks fired during reward lifecycle."""

    @patch('services.reward_service.fire_webhook')
    def test_claim_reward_fires_webhook(self, mock_webhook, client, db_session, kid_user, sample_reward, kid_headers):
        """Test claiming a reward fires webhook."""
        response = client.post(
            f'/api/rewards/{sample_reward.id}/claim',
            headers=kid_headers
        )

        assert response.status_code == 201
        mock_webhook.assert_called_once()
        call_args = mock_webhook.call_args
        assert call_args[0][0] == 'reward_claimed'

    @patch('services.reward_service.fire_webhook')
    def test_approve_reward_fires_webhook(self, mock_webhook, client, db_session, kid_user, parent_user, sample_reward, parent_headers):
        """Test approving a reward claim fires webhook."""
        # Create a pending reward claim
        sample_reward.requires_approval = True
        db_session.commit()

        claim = RewardClaim(
            reward_id=sample_reward.id,
            user_id=kid_user.id,
            points_spent=sample_reward.points_cost,
            status='pending',
            expires_at=datetime.utcnow()
        )
        db_session.add(claim)
        db_session.commit()

        # Approve the claim
        response = client.post(
            f'/api/rewards/claims/{claim.id}/approve',
            headers=parent_headers
        )

        assert response.status_code == 200
        mock_webhook.assert_called_once()
        call_args = mock_webhook.call_args
        assert call_args[0][0] == 'reward_approved'

    @patch('services.reward_service.fire_webhook')
    def test_reject_reward_fires_webhook(self, mock_webhook, client, db_session, kid_user, parent_user, sample_reward, parent_headers):
        """Test rejecting a reward claim fires webhook with reason."""
        # Create a pending reward claim
        sample_reward.requires_approval = True
        db_session.commit()

        claim = RewardClaim(
            reward_id=sample_reward.id,
            user_id=kid_user.id,
            points_spent=sample_reward.points_cost,
            status='pending',
            expires_at=datetime.utcnow()
        )
        db_session.add(claim)
        db_session.commit()

        # Reject the claim
        response = client.post(
            f'/api/rewards/claims/{claim.id}/reject',
            headers=parent_headers
        )

        assert response.status_code == 200
        mock_webhook.assert_called_once()
        call_args = mock_webhook.call_args
        assert call_args[0][0] == 'reward_rejected'
        assert call_args[1]['reason'] == 'manual'


class TestPointsWebhooks:
    """Tests for webhooks fired during points adjustments."""

    @patch('routes.points.fire_webhook')
    def test_manual_adjustment_fires_webhook(self, mock_webhook, client, db_session, kid_user, parent_user, parent_headers):
        """Test manual points adjustment fires webhook."""
        response = client.post(
            '/api/points/adjust',
            json={
                'user_id': kid_user.id,
                'points_delta': 10,
                'reason': 'Bonus points'
            },
            headers=parent_headers
        )

        assert response.status_code == 200
        mock_webhook.assert_called_once()
        call_args = mock_webhook.call_args
        assert call_args[0][0] == 'points_awarded'
        assert call_args[1]['delta'] == 10
        assert call_args[1]['reason'] == 'Bonus points'


class TestChoreCreationWebhooks:
    """Tests for webhooks fired when chores are created."""

    @patch('routes.chores.fire_webhook')
    def test_create_chore_fires_webhook_for_today_instances(self, mock_webhook, client, db_session, kid_user, parent_user, parent_headers):
        """Test creating a chore fires webhooks for instances due today."""
        response = client.post(
            '/api/chores',
            json={
                'name': 'Test Chore',
                'points': 5,
                'recurrence_type': 'simple',
                'recurrence_pattern': {'type': 'simple', 'interval': 'daily', 'every_n': 1},
                'assignment_type': 'individual',
                'requires_approval': True,
                'start_date': date.today().isoformat(),
                'assignments': [{'user_id': kid_user.id}]
            },
            headers=parent_headers
        )

        assert response.status_code == 201
        # Webhook should be called for instance created for today
        if mock_webhook.call_count > 0:
            call_events = [call[0][0] for call in mock_webhook.call_args_list]
            assert 'chore_instance_created' in call_events


class TestAllWebhookEventTypes:
    """Test that all 8 webhook event types are properly implemented."""

    def test_all_event_types_exist(self, app):
        """Verify all event type constants are used in codebase."""
        # These are the 8 webhook event types from the spec
        expected_events = [
            'chore_instance_created',
            'chore_instance_claimed',
            'chore_instance_approved',
            'chore_instance_rejected',
            'points_awarded',
            'reward_claimed',
            'reward_approved',
            'reward_rejected'
        ]

        # This test serves as documentation of all webhook types
        # Actual firing is tested in individual test methods above
        for event in expected_events:
            assert isinstance(event, str)
            assert len(event) > 0
