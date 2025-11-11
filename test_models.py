#!/usr/bin/env python
"""
Test script to verify SQLAlchemy models work correctly.

This script creates sample data and tests model methods.
"""

import sys
from datetime import date, datetime, timedelta

from addon.app import create_app
from addon.models import db, User, Chore, ChoreAssignment, ChoreInstance, Reward, RewardClaim, PointsHistory
from addon.schemas import validate_recurrence_pattern, calculate_next_due_date, EXAMPLE_PATTERNS


def test_models():
    """Test all models and their methods."""
    app = create_app()

    with app.app_context():
        print("=" * 70)
        print("Testing ChoreControl Models")
        print("=" * 70)

        # Clean up any existing data
        print("\n1. Cleaning database...")
        db.session.query(PointsHistory).delete()
        db.session.query(RewardClaim).delete()
        db.session.query(ChoreInstance).delete()
        db.session.query(ChoreAssignment).delete()
        db.session.query(Chore).delete()
        db.session.query(Reward).delete()
        db.session.query(User).delete()
        db.session.commit()
        print("   ✓ Database cleaned")

        # Test User model
        print("\n2. Creating users...")
        parent = User(
            ha_user_id="ha_parent_123",
            username="Mom",
            role="parent",
            points=0
        )
        kid1 = User(
            ha_user_id="ha_kid_456",
            username="Alice",
            role="kid",
            points=0
        )
        kid2 = User(
            ha_user_id="ha_kid_789",
            username="Bob",
            role="kid",
            points=0
        )
        db.session.add_all([parent, kid1, kid2])
        db.session.commit()
        print(f"   ✓ Created 3 users: {parent}, {kid1}, {kid2}")

        # Test Chore model with recurrence pattern
        print("\n3. Creating chores...")
        daily_pattern = EXAMPLE_PATTERNS["daily"]
        is_valid, error = validate_recurrence_pattern(daily_pattern)
        print(f"   Daily pattern validation: {is_valid} (error: {error})")

        chore1 = Chore(
            name="Take out trash",
            description="Roll bins to curb",
            points=5,
            recurrence_type="simple",
            recurrence_pattern=daily_pattern,
            start_date=date.today(),
            assignment_type="individual",
            requires_approval=True,
            created_by=parent.id
        )

        weekly_pattern = EXAMPLE_PATTERNS["monday_wednesday_friday"]
        chore2 = Chore(
            name="Feed the dog",
            description="Morning and evening",
            points=3,
            recurrence_type="complex",
            recurrence_pattern=weekly_pattern,
            start_date=date.today(),
            assignment_type="individual",
            requires_approval=False,
            created_by=parent.id
        )

        db.session.add_all([chore1, chore2])
        db.session.commit()
        print(f"   ✓ Created 2 chores: {chore1}, {chore2}")

        # Test ChoreAssignment
        print("\n4. Creating chore assignments...")
        assignment1 = ChoreAssignment(
            chore_id=chore1.id,
            user_id=kid1.id
        )
        assignment2 = ChoreAssignment(
            chore_id=chore2.id,
            user_id=kid2.id
        )
        db.session.add_all([assignment1, assignment2])
        db.session.commit()
        print(f"   ✓ Assigned chores to kids")

        # Test ChoreInstance
        print("\n5. Creating chore instance...")
        instance = ChoreInstance(
            chore_id=chore1.id,
            due_date=date.today(),
            status='assigned'
        )
        db.session.add(instance)
        db.session.commit()
        print(f"   ✓ Created instance: {instance}")

        # Test can_claim method
        print("\n6. Testing can_claim method...")
        can_claim = instance.can_claim(kid1.id)
        print(f"   Kid1 can claim: {can_claim}")
        assert can_claim == True, "Kid1 should be able to claim"

        can_claim_kid2 = instance.can_claim(kid2.id)
        print(f"   Kid2 can claim: {can_claim_kid2}")
        assert can_claim_kid2 == False, "Kid2 should not be able to claim"

        # Claim the chore
        print("\n7. Claiming chore...")
        instance.status = 'claimed'
        instance.claimed_by = kid1.id
        instance.claimed_at = datetime.utcnow()
        db.session.commit()
        print(f"   ✓ Chore claimed by {kid1.username}")

        # Test award_points method
        print("\n8. Approving chore and awarding points...")
        instance.award_points(approver_id=parent.id)
        db.session.commit()
        print(f"   ✓ Points awarded: {instance.points_awarded}")
        print(f"   Kid1 points: {kid1.points}")

        # Verify points history
        print("\n9. Verifying points history...")
        calculated_points = kid1.calculate_current_points()
        print(f"   Calculated points from history: {calculated_points}")
        print(f"   Stored points: {kid1.points}")
        assert kid1.verify_points_balance(), "Points should match history"
        print(f"   ✓ Points balance verified")

        # Test Reward model
        print("\n10. Creating rewards...")
        reward = Reward(
            name="Ice cream trip",
            description="Trip to the ice cream shop",
            points_cost=20,
            cooldown_days=7,
            max_claims_per_kid=2
        )
        db.session.add(reward)
        db.session.commit()
        print(f"   ✓ Created reward: {reward}")

        # Test can_claim method on reward
        print("\n11. Testing reward claim validation...")
        can_claim, reason = reward.can_claim(kid1.id)
        print(f"   Kid1 can claim reward: {can_claim} (reason: {reason})")
        # Kid1 only has 5 points, needs 20
        assert can_claim == False, "Kid1 should not have enough points"

        # Give kid1 more points
        print("\n12. Adding bonus points...")
        kid1.adjust_points(
            delta=20,
            reason="Bonus points",
            created_by_id=parent.id
        )
        db.session.commit()
        print(f"   ✓ Kid1 now has {kid1.points} points")

        # Try claiming reward again
        can_claim, reason = reward.can_claim(kid1.id)
        print(f"   Kid1 can claim reward: {can_claim}")
        assert can_claim == True, "Kid1 should now be able to claim"

        # Claim reward
        print("\n13. Claiming reward...")
        claim = RewardClaim(
            reward_id=reward.id,
            user_id=kid1.id,
            points_spent=reward.points_cost,
            status='approved'
        )
        db.session.add(claim)
        kid1.adjust_points(
            delta=-reward.points_cost,
            reason=f"Claimed reward: {reward.name}",
            created_by_id=kid1.id,
            reward_claim_id=claim.id
        )
        db.session.commit()
        print(f"   ✓ Reward claimed, Kid1 now has {kid1.points} points")

        # Test recurrence pattern calculation
        print("\n14. Testing recurrence pattern calculations...")
        next_date = calculate_next_due_date(daily_pattern, date.today())
        print(f"   Next due date (daily): {next_date}")

        next_date_weekly = calculate_next_due_date(weekly_pattern, date.today())
        print(f"   Next due date (M/W/F): {next_date_weekly}")

        # Test relationships
        print("\n15. Testing relationships...")
        print(f"   Parent created {len(parent.created_chores)} chores")
        print(f"   Kid1 has {len(kid1.chore_assignments)} chore assignments")
        print(f"   Kid1 has {len(kid1.points_history)} points history entries")
        print(f"   Chore1 has {len(chore1.assignments)} assignments")
        print(f"   Chore1 has {len(chore1.instances)} instances")

        print("\n" + "=" * 70)
        print("✓ All tests passed!")
        print("=" * 70)

        # Summary
        print("\nSUMMARY:")
        print(f"  - {User.query.count()} users")
        print(f"  - {Chore.query.count()} chores")
        print(f"  - {ChoreAssignment.query.count()} assignments")
        print(f"  - {ChoreInstance.query.count()} instances")
        print(f"  - {Reward.query.count()} rewards")
        print(f"  - {RewardClaim.query.count()} reward claims")
        print(f"  - {PointsHistory.query.count()} points history entries")


if __name__ == '__main__':
    test_models()
