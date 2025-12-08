"""
Unit tests for UI routes.

Tests the web interface routes that render HTML templates.
"""

import pytest
from datetime import datetime, date, timedelta
from models import User, Chore, ChoreInstance, Reward, RewardClaim, PointsHistory, ChoreAssignment


class TestDashboard:
    """Tests for dashboard page."""

    def test_dashboard_renders(self, client, parent_headers, parent_user):
        """Test that dashboard page loads successfully."""
        response = client.get('/', headers=parent_headers)
        assert response.status_code == 200
        assert b'Dashboard' in response.data
        assert b'ChoreControl' in response.data

    def test_dashboard_shows_stats(self, client, parent_headers, parent_user, kid_user, sample_chore):
        """Test that dashboard displays statistics."""
        from models import db
        # Create a pending instance
        instance = ChoreInstance(
            chore_id=sample_chore.id,
            due_date=date.today(),
            status='claimed',
            claimed_by=kid_user.id,
            claimed_at=datetime.utcnow()
        )
        db.session.add(instance)
        db.session.commit()

        response = client.get('/', headers=parent_headers)
        assert response.status_code == 200
        assert b'Pending Approvals' in response.data

    def test_dashboard_requires_auth(self, client):
        """Test that dashboard requires authentication (redirects to login)."""
        response = client.get('/')
        assert response.status_code == 302
        assert '/login' in response.location


class TestChoresList:
    """Tests for chores list page."""

    def test_chores_list_renders(self, client, parent_headers, parent_user):
        """Test that chores list page loads."""
        response = client.get('/chores', headers=parent_headers)
        assert response.status_code == 200
        assert b'Chores' in response.data

    def test_chores_list_shows_chores(self, client, parent_headers, parent_user, sample_chore):
        """Test that chores are displayed."""
        response = client.get('/chores', headers=parent_headers)
        assert response.status_code == 200
        assert sample_chore.name.encode() in response.data

    def test_chores_list_filter_active(self, client, parent_headers, parent_user, sample_chore):
        """Test filtering by active status."""
        from models import db
        # Create inactive chore
        inactive_chore = Chore(
            name="Inactive Chore",
            points=5,
            is_active=False,
            created_by=parent_user.id
        )
        db.session.add(inactive_chore)
        db.session.commit()

        # Filter for active only
        response = client.get('/chores?active=true', headers=parent_headers)
        assert response.status_code == 200
        assert sample_chore.name.encode() in response.data
        assert b'Inactive Chore' not in response.data

    def test_chores_list_filter_by_assignment(self, client, parent_headers, parent_user, kid_user, sample_chore):
        """Test filtering by assigned user."""
        from models import db
        # Assign chore to kid
        assignment = ChoreAssignment(chore_id=sample_chore.id, user_id=kid_user.id)
        db.session.add(assignment)
        db.session.commit()

        response = client.get(f'/chores?assigned_to={kid_user.id}', headers=parent_headers)
        assert response.status_code == 200
        assert sample_chore.name.encode() in response.data


class TestChoreDetail:
    """Tests for chore detail page."""

    def test_chore_detail_renders(self, client, parent_headers, parent_user, sample_chore):
        """Test that chore detail page loads."""
        response = client.get(f'/chores/{sample_chore.id}', headers=parent_headers)
        assert response.status_code == 200
        assert sample_chore.name.encode() in response.data

    def test_chore_detail_shows_instances(self, client, parent_headers, parent_user, sample_chore):
        """Test that instances are displayed."""
        from models import db
        # Create instance (valid statuses: assigned, claimed, approved, rejected, missed)
        instance = ChoreInstance(
            chore_id=sample_chore.id,
            due_date=date.today(),
            status='assigned'
        )
        db.session.add(instance)
        db.session.commit()

        response = client.get(f'/chores/{sample_chore.id}', headers=parent_headers)
        assert response.status_code == 200
        assert b'Chore Instances' in response.data

    def test_chore_detail_404_for_missing_chore(self, client, parent_headers, parent_user):
        """Test that 404 is returned for non-existent chore."""
        response = client.get('/chores/99999', headers=parent_headers)
        assert response.status_code == 404


class TestChoreForm:
    """Tests for chore create/edit form."""

    def test_chore_form_new_renders(self, client, parent_headers, parent_user):
        """Test that new chore form loads."""
        response = client.get('/chores/new', headers=parent_headers)
        assert response.status_code == 200
        assert b'Create New Chore' in response.data

    def test_chore_form_edit_renders(self, client, parent_headers, parent_user, sample_chore):
        """Test that edit chore form loads."""
        response = client.get(f'/chores/{sample_chore.id}/edit', headers=parent_headers)
        assert response.status_code == 200
        assert b'Edit Chore' in response.data
        assert sample_chore.name.encode() in response.data

    def test_chore_form_shows_kids_for_assignment(self, client, parent_headers, parent_user, kid_user):
        """Test that kids are shown for assignment."""
        response = client.get('/chores/new', headers=parent_headers)
        assert response.status_code == 200
        assert kid_user.username.encode() in response.data


class TestRewardsList:
    """Tests for rewards list page."""

    def test_rewards_list_renders(self, client, parent_headers, parent_user):
        """Test that rewards list page loads."""
        response = client.get('/rewards', headers=parent_headers)
        assert response.status_code == 200
        assert b'Rewards' in response.data

    def test_rewards_list_shows_rewards(self, client, parent_headers, parent_user, sample_reward):
        """Test that rewards are displayed."""
        response = client.get('/rewards', headers=parent_headers)
        assert response.status_code == 200
        assert sample_reward.name.encode() in response.data

    def test_rewards_list_shows_pending_claims(self, client, parent_headers, parent_user, kid_user, sample_reward):
        """Test that pending reward claims are displayed."""
        from models import db
        # Create pending claim
        claim = RewardClaim(
            reward_id=sample_reward.id,
            user_id=kid_user.id,
            points_spent=sample_reward.points_cost,
            claimed_at=datetime.utcnow(),
            status='pending'
        )
        db.session.add(claim)
        db.session.commit()

        response = client.get('/rewards', headers=parent_headers)
        assert response.status_code == 200
        assert b'Pending Reward Claims' in response.data


class TestRewardForm:
    """Tests for reward create/edit form."""

    def test_reward_form_new_renders(self, client, parent_headers, parent_user):
        """Test that new reward form loads."""
        response = client.get('/rewards/new', headers=parent_headers)
        assert response.status_code == 200
        assert b'Create New Reward' in response.data

    def test_reward_form_edit_renders(self, client, parent_headers, parent_user, sample_reward):
        """Test that edit reward form loads."""
        response = client.get(f'/rewards/{sample_reward.id}/edit', headers=parent_headers)
        assert response.status_code == 200
        assert b'Edit Reward' in response.data
        assert sample_reward.name.encode() in response.data


class TestApprovalQueue:
    """Tests for approval queue page."""

    def test_approval_queue_renders(self, client, parent_headers, parent_user):
        """Test that approval queue page loads."""
        response = client.get('/approvals', headers=parent_headers)
        assert response.status_code == 200
        assert b'Approval Queue' in response.data

    def test_approval_queue_shows_pending_chores(self, client, parent_headers, parent_user, kid_user, sample_chore):
        """Test that pending chore instances are shown."""
        from models import db
        instance = ChoreInstance(
            chore_id=sample_chore.id,
            due_date=date.today(),
            status='claimed',
            claimed_by=kid_user.id,
            claimed_at=datetime.utcnow()
        )
        db.session.add(instance)
        db.session.commit()

        response = client.get('/approvals', headers=parent_headers)
        assert response.status_code == 200
        assert sample_chore.name.encode() in response.data
        assert b'Pending Chore Approvals' in response.data

    def test_approval_queue_shows_pending_rewards(self, client, parent_headers, parent_user, kid_user, sample_reward):
        """Test that pending reward claims are shown."""
        from models import db
        claim = RewardClaim(
            reward_id=sample_reward.id,
            user_id=kid_user.id,
            points_spent=sample_reward.points_cost,
            claimed_at=datetime.utcnow(),
            status='pending'
        )
        db.session.add(claim)
        db.session.commit()

        response = client.get('/approvals', headers=parent_headers)
        assert response.status_code == 200
        assert sample_reward.name.encode() in response.data
        assert b'Pending Reward Claims' in response.data


class TestUsersList:
    """Tests for users list page."""

    def test_users_list_renders(self, client, parent_headers, parent_user):
        """Test that users list page loads."""
        response = client.get('/users', headers=parent_headers)
        assert response.status_code == 200
        assert b'Users' in response.data

    def test_users_list_shows_users(self, client, parent_headers, parent_user, kid_user):
        """Test that users are displayed."""
        response = client.get('/users', headers=parent_headers)
        assert response.status_code == 200
        assert parent_user.username.encode() in response.data
        assert kid_user.username.encode() in response.data

    def test_users_list_filter_by_role(self, client, parent_headers, parent_user, kid_user):
        """Test filtering users by role."""
        response = client.get('/users?role=kid', headers=parent_headers)
        assert response.status_code == 200
        assert kid_user.username.encode() in response.data
        # Parent might still appear in nav, but should not be in the main list


class TestUserDetail:
    """Tests for user detail page."""

    def test_user_detail_renders(self, client, parent_headers, parent_user, kid_user):
        """Test that user detail page loads."""
        response = client.get(f'/users/{kid_user.id}', headers=parent_headers)
        assert response.status_code == 200
        assert kid_user.username.encode() in response.data

    def test_user_detail_shows_points_for_kid(self, client, parent_headers, parent_user, kid_user):
        """Test that points info is shown for kids."""
        # Add some points
        kid_user.adjust_points(50, "Test points", created_by_id=parent_user.id)

        response = client.get(f'/users/{kid_user.id}', headers=parent_headers)
        assert response.status_code == 200
        assert b'Current Points' in response.data
        assert b'50' in response.data

    def test_user_detail_shows_points_history(self, client, parent_headers, parent_user, kid_user):
        """Test that points history is displayed."""
        kid_user.adjust_points(25, "Test adjustment", created_by_id=parent_user.id)

        response = client.get(f'/users/{kid_user.id}', headers=parent_headers)
        assert response.status_code == 200
        assert b'Points History' in response.data
        assert b'Test adjustment' in response.data

    def test_user_detail_shows_assigned_chores(self, client, parent_headers, parent_user, kid_user, sample_chore):
        """Test that assigned chores are shown."""
        from models import db
        assignment = ChoreAssignment(chore_id=sample_chore.id, user_id=kid_user.id)
        db.session.add(assignment)
        db.session.commit()

        response = client.get(f'/users/{kid_user.id}', headers=parent_headers)
        assert response.status_code == 200
        assert b'Assigned Chores' in response.data
        assert sample_chore.name.encode() in response.data

    def test_user_detail_404_for_missing_user(self, client, parent_headers, parent_user):
        """Test that 404 is returned for non-existent user."""
        response = client.get('/users/99999', headers=parent_headers)
        assert response.status_code == 404


class TestUIAuthentication:
    """Tests for UI authentication."""

    def test_all_ui_routes_require_auth(self, client):
        """Test that all UI routes require authentication (redirect to login)."""
        routes = [
            '/',
            '/chores',
            '/chores/new',
            '/calendar',
            '/rewards',
            '/rewards/new',
            '/approvals',
            '/users'
        ]

        for route in routes:
            response = client.get(route)
            assert response.status_code == 302, f"Route {route} should redirect to login"
            assert '/login' in response.location, f"Route {route} should redirect to login"

    def test_ui_routes_work_with_auth(self, client, parent_headers, parent_user):
        """Test that UI routes work with valid authentication."""
        routes = [
            '/',
            '/chores',
            '/chores/new',
            '/calendar',
            '/rewards',
            '/rewards/new',
            '/approvals',
            '/users'
        ]

        for route in routes:
            response = client.get(route, headers=parent_headers)
            assert response.status_code == 200, f"Route {route} should work with auth"


class TestUIPagination:
    """Tests for UI pagination."""

    def test_chores_pagination(self, client, parent_headers, parent_user):
        """Test that chores list paginates correctly."""
        from models import db
        # Create 25 chores (more than default per_page of 20)
        for i in range(25):
            chore = Chore(
                name=f"Test Chore {i}",
                points=10,
                created_by=parent_user.id
            )
            db.session.add(chore)
        db.session.commit()

        # First page
        response = client.get('/chores', headers=parent_headers)
        assert response.status_code == 200
        assert b'Page 1' in response.data or b'Showing' in response.data

        # Second page
        response = client.get('/chores?page=2', headers=parent_headers)
        assert response.status_code == 200

    def test_user_points_history_pagination(self, client, parent_headers, parent_user, kid_user):
        """Test that points history paginates."""
        # Add 25 point adjustments
        for i in range(25):
            kid_user.adjust_points(1, f"Adjustment {i}", created_by_id=parent_user.id)

        response = client.get(f'/users/{kid_user.id}', headers=parent_headers)
        assert response.status_code == 200

        response = client.get(f'/users/{kid_user.id}?page=2', headers=parent_headers)
        assert response.status_code == 200


class TestUIEmptyStates:
    """Tests for empty state handling in UI."""

    def test_empty_chores_list(self, client, parent_headers, parent_user):
        """Test empty state when no chores exist."""
        response = client.get('/chores', headers=parent_headers)
        assert response.status_code == 200
        assert b'No chores found' in response.data or b'Create Chore' in response.data

    def test_empty_rewards_list(self, client, parent_headers, parent_user):
        """Test empty state when no rewards exist."""
        response = client.get('/rewards', headers=parent_headers)
        assert response.status_code == 200
        assert b'No rewards' in response.data or b'Create Reward' in response.data

    def test_empty_approval_queue(self, client, parent_headers, parent_user):
        """Test empty state when no pending approvals."""
        response = client.get('/approvals', headers=parent_headers)
        assert response.status_code == 200
        assert b'All caught up' in response.data or b'No pending' in response.data


class TestCalendar:
    """Tests for calendar page."""

    def test_calendar_renders(self, client, parent_headers, parent_user):
        """Test that calendar page loads successfully."""
        response = client.get('/calendar', headers=parent_headers)
        assert response.status_code == 200
        assert b'Calendar' in response.data

    def test_calendar_requires_auth(self, client):
        """Test that calendar requires authentication (redirects to login)."""
        response = client.get('/calendar')
        assert response.status_code == 302
        assert '/login' in response.location

    def test_calendar_shows_instances_with_due_dates(self, client, parent_headers, parent_user, kid_user, sample_chore):
        """Test that instances with due dates appear in calendar events."""
        from models import db
        instance = ChoreInstance(
            chore_id=sample_chore.id,
            due_date=date.today(),
            assigned_to=kid_user.id,
            status='assigned'
        )
        db.session.add(instance)
        db.session.commit()

        response = client.get('/calendar', headers=parent_headers)
        assert response.status_code == 200
        # Check that the chore name appears in the calendar events JSON
        assert sample_chore.name.encode() in response.data

    def test_calendar_shows_instances_without_due_dates_in_table(self, client, parent_headers, parent_user, kid_user, sample_chore):
        """Test that instances without due dates appear in data table."""
        from models import db
        instance = ChoreInstance(
            chore_id=sample_chore.id,
            due_date=None,
            assigned_to=kid_user.id,
            status='assigned'
        )
        db.session.add(instance)
        db.session.commit()

        response = client.get('/calendar', headers=parent_headers)
        assert response.status_code == 200
        assert b'Instances Without Due Date' in response.data
        assert sample_chore.name.encode() in response.data

    def test_calendar_empty_state_for_no_due_date_instances(self, client, parent_headers, parent_user, kid_user, sample_chore):
        """Test empty state when all instances have due dates."""
        from models import db
        # Create only instances with due dates
        instance = ChoreInstance(
            chore_id=sample_chore.id,
            due_date=date.today(),
            assigned_to=kid_user.id,
            status='assigned'
        )
        db.session.add(instance)
        db.session.commit()

        response = client.get('/calendar', headers=parent_headers)
        assert response.status_code == 200
        assert b'No instances without due dates' in response.data or b'All chore instances have due dates' in response.data

    def test_calendar_shows_status_legend(self, client, parent_headers, parent_user):
        """Test that status legend is displayed."""
        response = client.get('/calendar', headers=parent_headers)
        assert response.status_code == 200
        assert b'Assigned' in response.data
        assert b'Claimed' in response.data
        assert b'Approved' in response.data
        assert b'Rejected' in response.data
        assert b'Missed' in response.data

    def test_calendar_includes_fullcalendar(self, client, parent_headers, parent_user):
        """Test that FullCalendar library is included."""
        response = client.get('/calendar', headers=parent_headers)
        assert response.status_code == 200
        assert b'fullcalendar' in response.data

    def test_calendar_shows_different_statuses(self, client, parent_headers, parent_user, kid_user, sample_chore):
        """Test that instances with different statuses are shown."""
        from models import db
        # Create instances with different statuses
        statuses = ['assigned', 'claimed', 'approved', 'rejected', 'missed']
        for i, status in enumerate(statuses):
            instance = ChoreInstance(
                chore_id=sample_chore.id,
                due_date=date.today() + timedelta(days=i),
                assigned_to=kid_user.id,
                status=status
            )
            if status == 'claimed':
                instance.claimed_by = kid_user.id
                instance.claimed_at = datetime.utcnow()
            elif status == 'approved':
                instance.claimed_by = kid_user.id
                instance.claimed_at = datetime.utcnow()
                instance.approved_by = parent_user.id
                instance.approved_at = datetime.utcnow()
            elif status == 'rejected':
                instance.claimed_by = kid_user.id
                instance.claimed_at = datetime.utcnow()
                instance.rejected_by = parent_user.id
                instance.rejected_at = datetime.utcnow()
            db.session.add(instance)
        db.session.commit()

        response = client.get('/calendar', headers=parent_headers)
        assert response.status_code == 200
        # All instances should be in the calendar events
        assert response.data.count(sample_chore.name.encode()) >= 5

    def test_calendar_shows_unassigned_instances(self, client, parent_headers, parent_user, sample_chore):
        """Test that unassigned instances are shown correctly."""
        from models import db
        instance = ChoreInstance(
            chore_id=sample_chore.id,
            due_date=date.today(),
            assigned_to=None,
            status='assigned'
        )
        db.session.add(instance)
        db.session.commit()

        response = client.get('/calendar', headers=parent_headers)
        assert response.status_code == 200
        assert b'Unassigned' in response.data
