"""Tests for Work-Together chore functionality."""

import pytest
from datetime import date, datetime
from models import (
    db, User, Chore, ChoreInstance, ChoreInstanceClaim, ChoreAssignment
)
from services.instance_service import (
    InstanceService, BadRequestError, ForbiddenError, NotFoundError
)


@pytest.fixture
def wt_parent(db_session):
    """Create a parent user for work-together tests."""
    user = User(
        ha_user_id='parent_wt_test',
        username='Parent',
        role='parent',
        points=0
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def wt_kid1(db_session):
    """Create first kid user for work-together tests."""
    user = User(
        ha_user_id='kid1_wt_test',
        username='Kid1',
        role='kid',
        points=100
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def wt_kid2(db_session):
    """Create second kid user for work-together tests."""
    user = User(
        ha_user_id='kid2_wt_test',
        username='Kid2',
        role='kid',
        points=50
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def work_together_chore(db_session, wt_parent, wt_kid1, wt_kid2):
    """Create a work-together enabled shared chore."""
    chore = Chore(
        name='Clean Kitchen Together',
        points=20,
        recurrence_type='none',
        assignment_type='shared',
        allow_work_together=True,
        created_by=wt_parent.id,
        is_active=True
    )
    db_session.add(chore)
    db_session.flush()

    # Assign both kids
    for kid in [wt_kid1, wt_kid2]:
        assignment = ChoreAssignment(chore_id=chore.id, user_id=kid.id)
        db_session.add(assignment)

    db_session.commit()
    return chore


@pytest.fixture
def work_together_instance(db_session, work_together_chore):
    """Create an instance of the work-together chore."""
    instance = ChoreInstance(
        chore_id=work_together_chore.id,
        due_date=date.today(),
        assigned_to=None,
        status='assigned'
    )
    db_session.add(instance)
    db_session.commit()
    return instance


class TestWorkTogetherClaiming:
    """Tests for claiming work-together chores."""

    def test_multiple_kids_can_claim(self, db_session, work_together_instance, wt_kid1, wt_kid2):
        """Multiple kids should be able to claim a work-together chore."""
        # First kid claims
        instance = InstanceService.claim(work_together_instance.id, wt_kid1.id)
        assert len(instance.claims) == 1
        assert instance.claims[0].user_id == wt_kid1.id
        assert instance.status == 'assigned'  # Still open for more claims

        # Second kid claims
        instance = InstanceService.claim(work_together_instance.id, wt_kid2.id)
        assert len(instance.claims) == 2
        # Should auto-close since all assigned kids have claimed
        assert instance.status == 'claiming_closed'

    def test_same_kid_cannot_claim_twice(self, db_session, work_together_instance, wt_kid1):
        """Same kid should not be able to claim twice."""
        InstanceService.claim(work_together_instance.id, wt_kid1.id)

        with pytest.raises(BadRequestError) as exc_info:
            InstanceService.claim(work_together_instance.id, wt_kid1.id)
        assert 'already claimed' in str(exc_info.value.message).lower()

    def test_auto_close_when_all_claim(self, db_session, work_together_instance, wt_kid1, wt_kid2):
        """Claiming should auto-close when all assigned kids have claimed."""
        InstanceService.claim(work_together_instance.id, wt_kid1.id)
        instance = InstanceService.claim(work_together_instance.id, wt_kid2.id)

        assert instance.status == 'claiming_closed'
        assert instance.claiming_closed_at is not None
        assert instance.claiming_closed_by is None  # Auto-closed

    def test_cannot_claim_after_closed(self, db_session, work_together_chore, wt_kid1, wt_kid2, wt_parent):
        """Kids should not be able to claim after claiming is closed."""
        # Create instance with only kid1 assigned
        instance = ChoreInstance(
            chore_id=work_together_chore.id,
            due_date=date.today(),
            assigned_to=None,
            status='assigned'
        )
        db_session.add(instance)
        db_session.commit()

        # Kid1 claims
        InstanceService.claim(instance.id, wt_kid1.id)

        # Parent closes claiming
        InstanceService.close_claiming(instance.id, wt_parent.id)

        # Kid2 tries to claim - should fail
        with pytest.raises(BadRequestError) as exc_info:
            InstanceService.claim(instance.id, wt_kid2.id)
        assert 'closed' in str(exc_info.value.message).lower()


class TestCloseClaiming:
    """Tests for closing claiming."""

    def test_parent_can_close_claiming_early(self, db_session, work_together_instance, wt_kid1, wt_parent):
        """Parent should be able to close claiming before all kids claim."""
        # Only one kid claims
        InstanceService.claim(work_together_instance.id, wt_kid1.id)

        # Parent closes claiming
        instance = InstanceService.close_claiming(work_together_instance.id, wt_parent.id)

        assert instance.status == 'claiming_closed'
        assert instance.claiming_closed_by == wt_parent.id

    def test_kid_cannot_close_claiming(self, db_session, work_together_instance, wt_kid1):
        """Kids should not be able to close claiming."""
        InstanceService.claim(work_together_instance.id, wt_kid1.id)

        with pytest.raises(ForbiddenError):
            InstanceService.close_claiming(work_together_instance.id, wt_kid1.id)

    def test_cannot_close_with_no_claims(self, db_session, work_together_instance, wt_parent):
        """Cannot close claiming if no one has claimed."""
        with pytest.raises(BadRequestError) as exc_info:
            InstanceService.close_claiming(work_together_instance.id, wt_parent.id)
        assert 'no claims' in str(exc_info.value.message).lower()


class TestClaimApproval:
    """Tests for approving/rejecting individual claims."""

    def test_cannot_approve_before_claiming_closed(self, db_session, work_together_instance, wt_kid1, wt_parent):
        """Cannot approve claims before claiming is closed."""
        InstanceService.claim(work_together_instance.id, wt_kid1.id)
        instance = db.session.get(ChoreInstance, work_together_instance.id)
        claim = instance.claims[0]

        with pytest.raises(BadRequestError) as exc_info:
            InstanceService.approve_claim(claim.id, wt_parent.id)
        assert 'closed' in str(exc_info.value.message).lower()

    def test_approve_individual_claims(self, db_session, work_together_instance, wt_kid1, wt_kid2, wt_parent):
        """Each claim should be approved individually."""
        # Both kids claim (auto-closes)
        InstanceService.claim(work_together_instance.id, wt_kid1.id)
        InstanceService.claim(work_together_instance.id, wt_kid2.id)

        instance = db.session.get(ChoreInstance, work_together_instance.id)
        claim1 = [c for c in instance.claims if c.user_id == wt_kid1.id][0]
        claim2 = [c for c in instance.claims if c.user_id == wt_kid2.id][0]

        # Approve first claim
        InstanceService.approve_claim(claim1.id, wt_parent.id)
        db.session.refresh(claim1)
        assert claim1.status == 'approved'
        assert claim1.points_awarded == 20  # Full points

        # Second claim still pending
        db.session.refresh(claim2)
        assert claim2.status == 'claimed'

    def test_each_kid_gets_full_points(self, db_session, work_together_instance, wt_kid1, wt_kid2, wt_parent):
        """Each kid should get full points, not split."""
        # Get initial points
        kid1_initial = db.session.get(User, wt_kid1.id).points
        kid2_initial = db.session.get(User, wt_kid2.id).points

        # Both kids claim
        InstanceService.claim(work_together_instance.id, wt_kid1.id)
        InstanceService.claim(work_together_instance.id, wt_kid2.id)

        instance = db.session.get(ChoreInstance, work_together_instance.id)
        for claim in instance.claims:
            InstanceService.approve_claim(claim.id, wt_parent.id)

        # Check both kids got full points
        kid1_after = db.session.get(User, wt_kid1.id).points
        kid2_after = db.session.get(User, wt_kid2.id).points

        assert kid1_after == kid1_initial + 20
        assert kid2_after == kid2_initial + 20

    def test_reject_claim_with_reason(self, db_session, work_together_instance, wt_kid1, wt_kid2, wt_parent):
        """Claims can be rejected with a reason."""
        InstanceService.claim(work_together_instance.id, wt_kid1.id)
        InstanceService.claim(work_together_instance.id, wt_kid2.id)

        instance = db.session.get(ChoreInstance, work_together_instance.id)
        claim1 = [c for c in instance.claims if c.user_id == wt_kid1.id][0]

        InstanceService.reject_claim(claim1.id, wt_parent.id, "Didn't actually help")

        db.session.refresh(claim1)
        assert claim1.status == 'rejected'
        assert claim1.rejection_reason == "Didn't actually help"

    def test_instance_approved_when_all_claims_resolved(self, db_session, work_together_instance, wt_kid1, wt_kid2, wt_parent):
        """Instance status should become 'approved' when all claims are resolved."""
        InstanceService.claim(work_together_instance.id, wt_kid1.id)
        InstanceService.claim(work_together_instance.id, wt_kid2.id)

        instance = db.session.get(ChoreInstance, work_together_instance.id)
        claims = list(instance.claims)

        # Approve first, reject second
        InstanceService.approve_claim(claims[0].id, wt_parent.id)
        db.session.refresh(instance)
        assert instance.status == 'claiming_closed'  # Not all resolved yet

        InstanceService.reject_claim(claims[1].id, wt_parent.id, "No")
        db.session.refresh(instance)
        assert instance.status == 'approved'  # All resolved


class TestBackwardCompatibility:
    """Tests for backward compatibility with regular shared chores."""

    def test_regular_shared_chore_unchanged(self, db_session, wt_parent, wt_kid1, wt_kid2):
        """Regular shared chores (without work_together) should work as before."""
        # Create regular shared chore (NOT work-together)
        chore = Chore(
            name='Regular Shared Chore',
            points=10,
            recurrence_type='none',
            assignment_type='shared',
            allow_work_together=False,  # Not a work-together chore
            created_by=wt_parent.id,
            is_active=True
        )
        db_session.add(chore)
        db_session.flush()

        for kid in [wt_kid1, wt_kid2]:
            assignment = ChoreAssignment(chore_id=chore.id, user_id=kid.id)
            db_session.add(assignment)

        instance = ChoreInstance(
            chore_id=chore.id,
            due_date=date.today(),
            assigned_to=None,
            status='assigned'
        )
        db_session.add(instance)
        db_session.commit()

        # First kid claims - should work as normal (claim the instance directly)
        result = InstanceService.claim(instance.id, wt_kid1.id)
        assert result.status == 'claimed'
        assert result.claimed_by == wt_kid1.id
        assert len(result.claims) == 0  # No ChoreInstanceClaim records

        # Second kid cannot claim (already claimed)
        with pytest.raises(BadRequestError):
            InstanceService.claim(instance.id, wt_kid2.id)
