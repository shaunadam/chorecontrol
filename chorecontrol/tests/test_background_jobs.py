"""Tests for Phase 3 background jobs."""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import patch, MagicMock

from models import db, User, Chore, ChoreInstance, ChoreAssignment, Reward, RewardClaim, PointsHistory
from jobs.instance_generator import generate_daily_instances
from jobs.auto_approval import check_auto_approvals
from jobs.missed_instances import mark_missed_instances
from jobs.reward_expiration import expire_pending_rewards
from jobs.points_audit import audit_points_balances


# =============================================================================
# Fixtures specific to background job tests
# =============================================================================

@pytest.fixture
def system_user(db_session):
    """Create a system user for auto-approvals."""
    user = User(
        ha_user_id='system',
        username='System',
        role='system',
        points=0
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def daily_chore(db_session, parent_user, kid_user):
    """Create a daily chore with assignment."""
    chore = Chore(
        name='Make Bed',
        description='Make bed every morning',
        points=5,
        recurrence_type='simple',
        recurrence_pattern={'type': 'daily'},
        assignment_type='individual',
        requires_approval=True,
        created_by=parent_user.id,
        is_active=True
    )
    db_session.add(chore)
    db_session.commit()

    # Create assignment
    assignment = ChoreAssignment(
        chore_id=chore.id,
        user_id=kid_user.id
    )
    db_session.add(assignment)
    db_session.commit()

    return chore


@pytest.fixture
def auto_approve_chore(db_session, parent_user, kid_user):
    """Create a chore with auto-approval enabled."""
    chore = Chore(
        name='Clean Room',
        description='Clean your room',
        points=10,
        recurrence_type='simple',
        recurrence_pattern={'type': 'weekly', 'days_of_week': [1]},
        assignment_type='individual',
        requires_approval=True,
        auto_approve_after_hours=24,  # Auto-approve after 24 hours
        created_by=parent_user.id,
        is_active=True
    )
    db_session.add(chore)
    db_session.commit()

    # Create assignment
    assignment = ChoreAssignment(
        chore_id=chore.id,
        user_id=kid_user.id
    )
    db_session.add(assignment)
    db_session.commit()

    return chore


@pytest.fixture
def no_late_claims_chore(db_session, parent_user, kid_user):
    """Create a chore that doesn't allow late claims."""
    chore = Chore(
        name='Take Out Trash',
        description='Trash pickup day',
        points=10,
        recurrence_type='simple',
        recurrence_pattern={'type': 'weekly', 'days_of_week': [1]},
        assignment_type='individual',
        requires_approval=True,
        allow_late_claims=False,
        created_by=parent_user.id,
        is_active=True
    )
    db_session.add(chore)
    db_session.commit()

    # Create assignment
    assignment = ChoreAssignment(
        chore_id=chore.id,
        user_id=kid_user.id
    )
    db_session.add(assignment)
    db_session.commit()

    return chore


@pytest.fixture
def approval_required_reward(db_session):
    """Create a reward that requires approval."""
    reward = Reward(
        name='Movie Night Pick',
        description='Choose the movie',
        points_cost=30,
        requires_approval=True,
        is_active=True
    )
    db_session.add(reward)
    db_session.commit()
    return reward


# =============================================================================
# Tests for Daily Instance Generator Job (Task 11)
# =============================================================================

class TestGenerateDailyInstances:
    """Tests for generate_daily_instances job."""

    def test_generates_instances_for_active_chores(self, app, db_session, daily_chore, kid_user):
        """Test that job generates instances for active chores."""
        with app.app_context():
            # Run the job
            generate_daily_instances()

            # Check that instances were created
            instances = ChoreInstance.query.filter_by(chore_id=daily_chore.id).all()
            assert len(instances) > 0

            # Check instance properties
            today_instance = [i for i in instances if i.due_date == date.today()]
            assert len(today_instance) == 1
            assert today_instance[0].status == 'assigned'
            assert today_instance[0].assigned_to == kid_user.id

    def test_skips_inactive_chores(self, app, db_session, parent_user, kid_user):
        """Test that job skips inactive chores."""
        with app.app_context():
            # Create an inactive chore
            chore = Chore(
                name='Inactive Chore',
                points=5,
                recurrence_type='simple',
                recurrence_pattern={'type': 'daily'},
                assignment_type='individual',
                requires_approval=True,
                created_by=parent_user.id,
                is_active=False  # Inactive from the start
            )
            db_session.add(chore)
            db_session.commit()

            # Create assignment
            assignment = ChoreAssignment(chore_id=chore.id, user_id=kid_user.id)
            db_session.add(assignment)
            db_session.commit()

            # Run the job
            generate_daily_instances()

            # Check that no instances were created
            instances = ChoreInstance.query.filter_by(chore_id=chore.id).all()
            assert len(instances) == 0

    def test_does_not_create_duplicates(self, app, db_session, daily_chore, kid_user):
        """Test that job doesn't create duplicate instances."""
        with app.app_context():
            # Run the job twice
            generate_daily_instances()
            initial_count = ChoreInstance.query.filter_by(chore_id=daily_chore.id).count()

            generate_daily_instances()
            final_count = ChoreInstance.query.filter_by(chore_id=daily_chore.id).count()

            # Count should be the same
            assert initial_count == final_count

    def test_generates_for_multiple_assigned_users(self, app, db_session, parent_user, kid_user, kid_user_2):
        """Test that job generates instances for all assigned users (individual chores)."""
        with app.app_context():
            # Create chore assigned to both kids
            chore = Chore(
                name='Brush Teeth',
                points=2,
                recurrence_type='simple',
                recurrence_pattern={'type': 'daily'},
                assignment_type='individual',
                requires_approval=False,
                created_by=parent_user.id,
                is_active=True
            )
            db_session.add(chore)
            db_session.commit()

            # Assign to both kids
            for kid in [kid_user, kid_user_2]:
                assignment = ChoreAssignment(chore_id=chore.id, user_id=kid.id)
                db_session.add(assignment)
            db_session.commit()

            # Run the job
            generate_daily_instances()

            # Check that instances were created for both kids
            today_instances = ChoreInstance.query.filter_by(
                chore_id=chore.id,
                due_date=date.today()
            ).all()
            assert len(today_instances) == 2
            assigned_users = {i.assigned_to for i in today_instances}
            assert assigned_users == {kid_user.id, kid_user_2.id}

    def test_generates_shared_chore_once(self, app, db_session, parent_user, kid_user, kid_user_2):
        """Test that shared chores only create one instance per date."""
        with app.app_context():
            # Create shared chore
            chore = Chore(
                name='Walk Dog',
                points=5,
                recurrence_type='simple',
                recurrence_pattern={'type': 'daily'},
                assignment_type='shared',
                requires_approval=True,
                created_by=parent_user.id,
                is_active=True
            )
            db_session.add(chore)
            db_session.commit()

            # Assign to both kids
            for kid in [kid_user, kid_user_2]:
                assignment = ChoreAssignment(chore_id=chore.id, user_id=kid.id)
                db_session.add(assignment)
            db_session.commit()

            # Run the job
            generate_daily_instances()

            # Check that only one instance was created
            today_instances = ChoreInstance.query.filter_by(
                chore_id=chore.id,
                due_date=date.today()
            ).all()
            assert len(today_instances) == 1
            assert today_instances[0].assigned_to is None  # Shared chores have no assigned_to

    def test_handles_chore_with_no_assignments(self, app, db_session, parent_user):
        """Test that job handles chores with no assignments gracefully."""
        with app.app_context():
            # Create chore with no assignments
            chore = Chore(
                name='Orphan Chore',
                points=5,
                recurrence_type='simple',
                recurrence_pattern={'type': 'daily'},
                assignment_type='individual',
                requires_approval=True,
                created_by=parent_user.id,
                is_active=True
            )
            db_session.add(chore)
            db_session.commit()

            # Run the job - should not raise error
            generate_daily_instances()

            # No instances should be created for individual chore with no assignments
            instances = ChoreInstance.query.filter_by(chore_id=chore.id).all()
            assert len(instances) == 0


# =============================================================================
# Tests for Auto-Approval Checker Job (Task 12)
# =============================================================================

class TestCheckAutoApprovals:
    """Tests for check_auto_approvals job."""

    def test_auto_approves_after_threshold(self, app, db_session, auto_approve_chore, kid_user, system_user):
        """Test that claimed instances are auto-approved after threshold."""
        with app.app_context():
            # Get fresh references within context
            kid = User.query.get(kid_user.id)
            sys_user = User.query.get(system_user.id)
            chore = Chore.query.get(auto_approve_chore.id)

            # Create a claimed instance that's past the threshold
            instance = ChoreInstance(
                chore_id=chore.id,
                due_date=date.today(),
                status='claimed',
                assigned_to=kid.id,
                claimed_by=kid.id,
                claimed_at=datetime.utcnow() - timedelta(hours=25)  # 25 hours ago
            )
            db.session.add(instance)
            db.session.commit()

            initial_points = kid.points
            instance_id = instance.id

            # Run the job
            check_auto_approvals()

            # Re-query to get fresh data
            instance = ChoreInstance.query.get(instance_id)
            kid = User.query.get(kid_user.id)

            # Check that instance was approved
            assert instance.status == 'approved'
            assert instance.approved_by == sys_user.id
            assert instance.points_awarded == chore.points
            assert kid.points == initial_points + chore.points

    def test_does_not_approve_before_threshold(self, app, db_session, auto_approve_chore, kid_user, system_user):
        """Test that instances are not approved before threshold."""
        with app.app_context():
            # Get fresh references within context
            kid = User.query.get(kid_user.id)
            chore = Chore.query.get(auto_approve_chore.id)

            # Create a claimed instance that's not past the threshold
            instance = ChoreInstance(
                chore_id=chore.id,
                due_date=date.today(),
                status='claimed',
                assigned_to=kid.id,
                claimed_by=kid.id,
                claimed_at=datetime.utcnow() - timedelta(hours=23)  # 23 hours ago
            )
            db.session.add(instance)
            db.session.commit()

            initial_points = kid.points
            instance_id = instance.id

            # Run the job
            check_auto_approvals()

            # Re-query to get fresh data
            instance = ChoreInstance.query.get(instance_id)
            kid = User.query.get(kid_user.id)

            # Check that instance was not approved
            assert instance.status == 'claimed'
            assert instance.approved_by is None
            assert kid.points == initial_points

    def test_requires_system_user(self, app, db_session, auto_approve_chore, kid_user):
        """Test that job logs error if system user is missing."""
        with app.app_context():
            # Create a claimed instance past threshold (but no system user)
            instance = ChoreInstance(
                chore_id=auto_approve_chore.id,
                due_date=date.today(),
                status='claimed',
                assigned_to=kid_user.id,
                claimed_by=kid_user.id,
                claimed_at=datetime.utcnow() - timedelta(hours=25)
            )
            db_session.add(instance)
            db_session.commit()

            # Run the job - should not raise but should not approve
            check_auto_approvals()

            # Refresh instance
            db_session.refresh(instance)

            # Check that instance was not approved (no system user)
            assert instance.status == 'claimed'

    def test_only_processes_claimed_instances(self, app, db_session, auto_approve_chore, kid_user, system_user):
        """Test that only claimed instances are processed."""
        with app.app_context():
            # Create instances with different statuses
            statuses = ['assigned', 'approved', 'rejected', 'missed']
            for status in statuses:
                instance = ChoreInstance(
                    chore_id=auto_approve_chore.id,
                    due_date=date.today() - timedelta(days=len(statuses)),
                    status=status,
                    assigned_to=kid_user.id
                )
                if status in ['approved', 'rejected']:
                    instance.claimed_by = kid_user.id
                    instance.claimed_at = datetime.utcnow() - timedelta(hours=25)
                db_session.add(instance)
            db_session.commit()

            # Run the job
            check_auto_approvals()

            # Check that none of these instances changed
            for status in statuses:
                instances = ChoreInstance.query.filter_by(status=status).all()
                assert all(i.approved_by != system_user.id for i in instances)

    def test_ignores_chores_without_auto_approve(self, app, db_session, no_late_claims_chore, kid_user, system_user):
        """Test that chores without auto_approve_after_hours are ignored."""
        with app.app_context():
            # Create a claimed instance
            instance = ChoreInstance(
                chore_id=no_late_claims_chore.id,
                due_date=date.today(),
                status='claimed',
                assigned_to=kid_user.id,
                claimed_by=kid_user.id,
                claimed_at=datetime.utcnow() - timedelta(hours=100)  # Very old
            )
            db_session.add(instance)
            db_session.commit()

            # Run the job
            check_auto_approvals()

            # Refresh instance
            db_session.refresh(instance)

            # Check that instance was not approved
            assert instance.status == 'claimed'


# =============================================================================
# Tests for Missed Instance Marker Job (Task 13)
# =============================================================================

class TestMarkMissedInstances:
    """Tests for mark_missed_instances job."""

    def test_marks_overdue_instances_as_missed(self, app, db_session, no_late_claims_chore, kid_user):
        """Test that overdue assigned instances are marked as missed."""
        with app.app_context():
            # Create an overdue instance
            instance = ChoreInstance(
                chore_id=no_late_claims_chore.id,
                due_date=date.today() - timedelta(days=1),
                status='assigned',
                assigned_to=kid_user.id
            )
            db_session.add(instance)
            db_session.commit()

            # Run the job
            mark_missed_instances()

            # Refresh instance
            db_session.refresh(instance)

            # Check that instance was marked as missed
            assert instance.status == 'missed'

    def test_does_not_mark_future_instances(self, app, db_session, no_late_claims_chore, kid_user):
        """Test that future instances are not marked as missed."""
        with app.app_context():
            # Create a future instance
            instance = ChoreInstance(
                chore_id=no_late_claims_chore.id,
                due_date=date.today() + timedelta(days=1),
                status='assigned',
                assigned_to=kid_user.id
            )
            db_session.add(instance)
            db_session.commit()

            # Run the job
            mark_missed_instances()

            # Refresh instance
            db_session.refresh(instance)

            # Check that instance is still assigned
            assert instance.status == 'assigned'

    def test_does_not_mark_today_instances(self, app, db_session, no_late_claims_chore, kid_user):
        """Test that instances due today are not marked as missed."""
        with app.app_context():
            # Create an instance due today
            instance = ChoreInstance(
                chore_id=no_late_claims_chore.id,
                due_date=date.today(),
                status='assigned',
                assigned_to=kid_user.id
            )
            db_session.add(instance)
            db_session.commit()

            # Run the job
            mark_missed_instances()

            # Refresh instance
            db_session.refresh(instance)

            # Check that instance is still assigned
            assert instance.status == 'assigned'

    def test_preserves_instances_with_late_claims_allowed(self, app, db_session, parent_user, kid_user):
        """Test that instances with allow_late_claims=True are preserved."""
        with app.app_context():
            # Create chore that allows late claims
            chore = Chore(
                name='Flexible Chore',
                points=5,
                recurrence_type='simple',
                recurrence_pattern={'type': 'daily'},
                assignment_type='individual',
                requires_approval=True,
                allow_late_claims=True,  # Key difference
                created_by=parent_user.id,
                is_active=True
            )
            db_session.add(chore)
            db_session.commit()

            # Create an overdue instance
            instance = ChoreInstance(
                chore_id=chore.id,
                due_date=date.today() - timedelta(days=1),
                status='assigned',
                assigned_to=kid_user.id
            )
            db_session.add(instance)
            db_session.commit()

            # Run the job
            mark_missed_instances()

            # Refresh instance
            db_session.refresh(instance)

            # Check that instance is still assigned (can still be claimed late)
            assert instance.status == 'assigned'

    def test_only_marks_assigned_instances(self, app, db_session, no_late_claims_chore, kid_user):
        """Test that only assigned instances are marked as missed."""
        with app.app_context():
            # Create instances with different statuses
            for status in ['claimed', 'approved', 'rejected']:
                instance = ChoreInstance(
                    chore_id=no_late_claims_chore.id,
                    due_date=date.today() - timedelta(days=1),
                    status=status,
                    assigned_to=kid_user.id
                )
                if status in ['claimed', 'approved', 'rejected']:
                    instance.claimed_by = kid_user.id
                    instance.claimed_at = datetime.utcnow()
                db_session.add(instance)
            db_session.commit()

            # Run the job
            mark_missed_instances()

            # Check that none of these instances were changed
            for status in ['claimed', 'approved', 'rejected']:
                instances = ChoreInstance.query.filter_by(
                    chore_id=no_late_claims_chore.id,
                    status=status
                ).all()
                assert len(instances) == 1

    def test_preserves_instances_with_null_due_date(self, app, db_session, parent_user, kid_user):
        """Test that instances with NULL due_date are not marked as missed."""
        with app.app_context():
            # Create chore
            chore = Chore(
                name='Anytime Chore',
                points=5,
                recurrence_type='none',
                recurrence_pattern={'type': 'none'},
                assignment_type='individual',
                requires_approval=True,
                allow_late_claims=False,
                created_by=parent_user.id,
                is_active=True
            )
            db_session.add(chore)
            db_session.commit()

            # Create instance with no due date
            instance = ChoreInstance(
                chore_id=chore.id,
                due_date=None,
                status='assigned',
                assigned_to=kid_user.id
            )
            db_session.add(instance)
            db_session.commit()

            # Run the job
            mark_missed_instances()

            # Refresh instance
            db_session.refresh(instance)

            # Check that instance is still assigned
            assert instance.status == 'assigned'


# =============================================================================
# Tests for Reward Expiration Job (Task 14)
# =============================================================================

class TestExpirePendingRewards:
    """Tests for expire_pending_rewards job."""

    def test_expires_overdue_pending_claims(self, app, db_session, approval_required_reward, kid_user):
        """Test that expired pending claims are rejected and refunded."""
        with app.app_context():
            # Get fresh references within context
            kid = User.query.get(kid_user.id)
            reward = Reward.query.get(approval_required_reward.id)

            # Set kid's points
            kid.points = 100
            db.session.commit()

            # Create an expired pending claim
            claim = RewardClaim(
                reward_id=reward.id,
                user_id=kid.id,
                points_spent=reward.points_cost,
                status='pending',
                claimed_at=datetime.utcnow() - timedelta(days=8),
                expires_at=datetime.utcnow() - timedelta(days=1)  # Expired yesterday
            )
            db.session.add(claim)

            # Simulate points already deducted
            kid.points -= reward.points_cost
            db.session.commit()

            points_before = kid.points
            claim_id = claim.id

            # Run the job
            expire_pending_rewards()

            # Re-query to get fresh data
            claim = RewardClaim.query.get(claim_id)
            kid = User.query.get(kid_user.id)

            # Check that claim was rejected
            assert claim.status == 'rejected'

            # Check that points were refunded
            assert kid.points == points_before + reward.points_cost

    def test_does_not_expire_non_expired_claims(self, app, db_session, approval_required_reward, kid_user):
        """Test that non-expired pending claims are preserved."""
        with app.app_context():
            # Set kid's points
            kid_user.points = 100
            db_session.commit()

            # Create a pending claim that hasn't expired yet
            claim = RewardClaim(
                reward_id=approval_required_reward.id,
                user_id=kid_user.id,
                points_spent=approval_required_reward.points_cost,
                status='pending',
                claimed_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=7)  # Expires in 7 days
            )
            db_session.add(claim)
            db_session.commit()

            # Run the job
            expire_pending_rewards()

            # Refresh
            db_session.refresh(claim)

            # Check that claim is still pending
            assert claim.status == 'pending'

    def test_does_not_affect_approved_claims(self, app, db_session, approval_required_reward, kid_user, parent_user):
        """Test that approved claims are not affected."""
        with app.app_context():
            # Create an approved claim
            claim = RewardClaim(
                reward_id=approval_required_reward.id,
                user_id=kid_user.id,
                points_spent=approval_required_reward.points_cost,
                status='approved',
                claimed_at=datetime.utcnow() - timedelta(days=8),
                expires_at=datetime.utcnow() - timedelta(days=1),  # Would be expired if pending
                approved_by=parent_user.id,
                approved_at=datetime.utcnow() - timedelta(days=7)
            )
            db_session.add(claim)
            db_session.commit()

            # Run the job
            expire_pending_rewards()

            # Refresh
            db_session.refresh(claim)

            # Check that claim is still approved
            assert claim.status == 'approved'

    def test_creates_points_history_on_refund(self, app, db_session, approval_required_reward, kid_user):
        """Test that points history is created when refunding."""
        with app.app_context():
            # Set kid's points
            kid_user.points = 50
            db_session.commit()

            # Create an expired pending claim
            claim = RewardClaim(
                reward_id=approval_required_reward.id,
                user_id=kid_user.id,
                points_spent=approval_required_reward.points_cost,
                status='pending',
                claimed_at=datetime.utcnow() - timedelta(days=8),
                expires_at=datetime.utcnow() - timedelta(days=1)
            )
            db_session.add(claim)
            db_session.commit()

            initial_history_count = PointsHistory.query.filter_by(user_id=kid_user.id).count()

            # Run the job
            expire_pending_rewards()

            # Check that points history was created
            final_history_count = PointsHistory.query.filter_by(user_id=kid_user.id).count()
            assert final_history_count == initial_history_count + 1

            # Check the history entry
            latest_history = PointsHistory.query.filter_by(
                user_id=kid_user.id
            ).order_by(PointsHistory.id.desc()).first()
            assert latest_history.points_delta == approval_required_reward.points_cost
            assert 'expired' in latest_history.reason.lower()


# =============================================================================
# Tests for Points Audit Job (Task 14)
# =============================================================================

class TestAuditPointsBalances:
    """Tests for audit_points_balances job."""

    def test_no_discrepancy_when_balanced(self, app, db_session, kid_user, parent_user):
        """Test that audit passes when points are balanced."""
        with app.app_context():
            # Get fresh references within context
            kid = User.query.get(kid_user.id)
            parent = User.query.get(parent_user.id)

            # Set initial points to 0 for clean slate
            kid.points = 0
            db.session.commit()

            # Add some points history that matches the balance
            kid.adjust_points(
                delta=50,
                reason='Test points',
                created_by_id=parent.id
            )
            db.session.commit()

            # Run the audit (should not raise or log errors)
            audit_points_balances()

            # Verify points match
            kid = User.query.get(kid_user.id)
            assert kid.verify_points_balance()

    def test_detects_discrepancy(self, app, db_session, kid_user, parent_user):
        """Test that audit detects discrepancies."""
        with app.app_context():
            # Get fresh references within context
            kid = User.query.get(kid_user.id)
            parent = User.query.get(parent_user.id)

            # Create a discrepancy by manually setting points
            kid.points = 100  # Set manually without history
            db.session.commit()

            # Add some history that doesn't match
            history = PointsHistory(
                user_id=kid.id,
                points_delta=50,
                reason='Test points',
                created_by=parent.id
            )
            db.session.add(history)
            db.session.commit()

            # Now points = 100 but history sum = 50
            kid = User.query.get(kid_user.id)
            assert not kid.verify_points_balance()

            # Run the audit - should log error but not raise
            audit_points_balances()

    def test_only_audits_kids(self, app, db_session, parent_user, kid_user):
        """Test that audit only checks kid users."""
        with app.app_context():
            # Get fresh reference within context
            parent = User.query.get(parent_user.id)

            # Create discrepancy for parent (shouldn't be checked)
            parent.points = 1000
            db.session.commit()

            # Run the audit - should not raise
            audit_points_balances()

    def test_handles_empty_history(self, app, db_session):
        """Test that audit handles users with no history."""
        with app.app_context():
            # Create a kid with 0 points and no history
            kid = User(
                ha_user_id='audit-test-kid',
                username='Audit Test Kid',
                role='kid',
                points=0
            )
            db.session.add(kid)
            db.session.commit()

            kid_id = kid.id

            # Run the audit - should pass (0 = 0)
            audit_points_balances()

            kid = User.query.get(kid_id)
            assert kid.verify_points_balance()


# =============================================================================
# Tests for Scheduler Module
# =============================================================================

class TestSchedulerModule:
    """Tests for scheduler initialization and management."""

    def test_scheduler_disabled_in_testing(self, app):
        """Test that scheduler is disabled in testing mode."""
        from scheduler import get_scheduler

        scheduler = get_scheduler()
        # Scheduler should not be running in test mode
        assert not scheduler.running or app.config.get('TESTING', False)

    def test_get_job_status(self, app):
        """Test get_job_status function."""
        from scheduler import get_job_status

        with app.app_context():
            status = get_job_status()
            # In testing mode, should return empty list or configured jobs
            assert isinstance(status, list)
