#!/usr/bin/env python3
"""
Seed data script for ChoreControl development and testing.

This script creates realistic sample data for development and testing.
It can be run multiple times safely (idempotent) and supports various
configuration options.

Usage:
    python seed.py --reset --verbose
    python seed.py --kids 5 --chores 20
    python seed.py --preserve
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from models import db, User, Chore, ChoreAssignment, ChoreInstance
from models import Reward, RewardClaim, PointsHistory
from app import create_app
from utils.instance_generator import generate_instances_for_chore

from seed_helpers import (
    PARENT_NAMES,
    KID_NAMES,
    KID_AGES,
    generate_random_date,
    generate_recent_dates,
    create_simple_recurrence_pattern,
    create_complex_recurrence_pattern,
    get_random_chore_data,
    get_random_reward_data,
    assign_chores_to_kids,
    generate_ha_user_id,
    generate_rejection_reason,
    get_random_status_distribution,
)


class SeedDataGenerator:
    """
    Generates seed data for the ChoreControl database.
    """

    def __init__(self, verbose: bool = False):
        """
        Initialize the seed data generator.

        Args:
            verbose: Whether to print detailed output
        """
        self.verbose = verbose
        self.created_counts = {
            "users": 0,
            "chores": 0,
            "assignments": 0,
            "instances": 0,
            "rewards": 0,
            "reward_claims": 0,
            "points_history": 0,
        }

    def log(self, message: str) -> None:
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(f"  {message}")

    def confirm_reset(self) -> bool:
        """
        Ask user to confirm database reset.

        Returns:
            True if user confirms, False otherwise
        """
        response = input("⚠️  This will DELETE all existing data. Continue? (yes/no): ")
        return response.lower() in ["yes", "y"]

    def clear_database(self) -> None:
        """Clear all data from the database, preserving admin user."""
        print("\n🗑️  Clearing existing data...")

        # Find the admin user to preserve
        admin_user = User.query.filter_by(ha_user_id='local-admin').first()

        db.session.query(PointsHistory).delete()
        db.session.query(RewardClaim).delete()
        db.session.query(Reward).delete()
        db.session.query(ChoreInstance).delete()
        db.session.query(ChoreAssignment).delete()
        db.session.query(Chore).delete()

        # Delete all users except admin
        if admin_user:
            db.session.query(User).filter(User.id != admin_user.id).delete()
            self.log("Preserved admin user")
        else:
            db.session.query(User).delete()

        db.session.commit()

        # Recreate admin if it didn't exist
        if not admin_user:
            # Expire all to avoid identity map conflicts
            db.session.expire_all()

            admin_user = User(
                ha_user_id='local-admin',
                username='admin',
                role='parent',
                points=0
            )
            admin_user.set_password('admin')
            db.session.add(admin_user)
            db.session.commit()
            self.log("Created admin user (username: 'admin', password: 'admin')")

        self.log("Database cleared successfully")

    def create_users(self, num_parents: int = 2, num_kids: int = 3) -> Dict[str, Any]:
        """
        Create parent and kid users.

        Args:
            num_parents: Number of parent users to create
            num_kids: Number of kid users to create

        Returns:
            Dictionary with 'parents' and 'kids' lists of user objects
        """
        print(f"\n👥 Creating {num_parents} parents and {num_kids} kids...")

        parents = []
        kids = []

        # Create parents
        for i in range(num_parents):
            username = PARENT_NAMES[i] if i < len(PARENT_NAMES) else f"Parent{i+1}"
            parent_data = {
                "ha_user_id": generate_ha_user_id(username),
                "username": username,
                "role": "parent",
                "points": 0,
            }

            parent = User(**parent_data)
            # Set default password for parent users so they can log in
            parent.set_password('password')
            db.session.add(parent)
            parents.append(parent)

            self.created_counts["users"] += 1
            self.log(f"Created parent: {username} (password: 'password')")

        # Create kids
        for i in range(num_kids):
            username = KID_NAMES[i] if i < len(KID_NAMES) else f"Kid{i+1}"
            kid_data = {
                "ha_user_id": generate_ha_user_id(username),
                "username": username,
                "role": "kid",
                "points": 0,  # Will be updated after points history is created
            }

            kid = User(**kid_data)
            # Set default password for kid users so they can log in
            kid.set_password('password')
            db.session.add(kid)
            kids.append(kid)

            self.created_counts["users"] += 1
            self.log(f"Created kid: {username} (age {KID_AGES.get(username, 'N/A')}, password: 'password')")

        db.session.commit()

        return {"parents": parents, "kids": kids}

    def create_chores(
        self,
        num_chores: int = 12,
        created_by_user: Optional[Any] = None
    ) -> List[Any]:
        """
        Create chores with various recurrence patterns.

        Args:
            num_chores: Number of chores to create
            created_by_user: User who created the chores (parent)

        Returns:
            List of created chore objects
        """
        print(f"\n📋 Creating {num_chores} chores...")

        chores = []
        chore_data_list = get_random_chore_data(num_chores)

        # Ensure we have enough chore data
        while len(chore_data_list) < num_chores:
            chore_data_list.extend(get_random_chore_data(1))

        for i, chore_data in enumerate(chore_data_list[:num_chores]):
            # Determine recurrence pattern
            recurrence_type = self._get_recurrence_type(i, num_chores)
            recurrence_pattern = self._get_recurrence_pattern(recurrence_type)

            # Determine assignment type - make some chores shared
            # ~20% of chores should be shared (claimable by any assigned kid)
            assignment_type = "shared" if i % 5 == 0 else "individual"

            # For one-off chores, some should have no start_date (anytime chores)
            start_date = None if (recurrence_type == "none" and i % 2 == 0) else datetime.now().date()

            # Create chore
            chore_dict = {
                "name": chore_data["name"],
                "description": chore_data["description"],
                "points": chore_data["points"],
                "recurrence_type": recurrence_type,
                "recurrence_pattern": recurrence_pattern,
                "start_date": start_date,
                "end_date": None,
                "assignment_type": assignment_type,
                "requires_approval": i % 7 != 0,  # Every 7th chore has auto-approval
                "auto_approve_after_hours": 24 if i % 7 == 0 else None,
                "is_active": True,
            }

            chore_obj = Chore(**chore_dict)
            if created_by_user:
                chore_obj.created_by = created_by_user.id
            db.session.add(chore_obj)
            chores.append(chore_obj)

            self.created_counts["chores"] += 1
            type_info = f"{recurrence_type}, {assignment_type}"
            if start_date is None:
                type_info += ", anytime"
            self.log(f"Created chore: {chore_dict['name']} ({type_info})")

        db.session.commit()

        return chores

    def _get_recurrence_type(self, index: int, total: int) -> str:
        """Determine recurrence type based on index."""
        if index < total * 0.2:  # 20% one-off
            return "none"
        elif index < total * 0.7:  # 50% simple recurring
            return "simple"
        else:  # 30% complex recurring
            return "complex"

    def _get_recurrence_pattern(self, recurrence_type: str) -> Optional[Dict[str, Any]]:
        """Generate recurrence pattern based on type."""
        if recurrence_type == "none":
            return None
        elif recurrence_type == "simple":
            import random
            intervals = ["daily", "weekly", "monthly"]
            return create_simple_recurrence_pattern(
                interval=random.choice(intervals),
                every_n=random.randint(1, 2)
            )
        else:  # complex
            import random
            # Random weekday pattern (e.g., Mon, Wed, Fri)
            days = random.sample([1, 2, 3, 4, 5, 6, 7], random.randint(2, 4))
            return create_complex_recurrence_pattern(days_of_week=days)

    def create_assignments(self, chores: List[Any], kids: List[Any]) -> List[Any]:
        """
        Create chore assignments linking chores to kids.

        Args:
            chores: List of chore objects
            kids: List of kid user objects

        Returns:
            List of created assignment objects
        """
        print(f"\n🔗 Creating chore assignments...")

        assignments = []
        chore_data_lookup = {c["name"]: c for c in get_random_chore_data(50)}

        for chore in chores:
            chore_data = chore_data_lookup.get(chore.name, {"age_min": 6})

            # Assign to age-appropriate kids
            for kid in kids:
                kid_age = KID_AGES.get(kid.username, 10)
                if kid_age >= chore_data.get("age_min", 0):
                    # Randomly assign (70% chance)
                    import random
                    if random.random() < 0.7:
                        assignment = {
                            "chore_id": chore.id,
                            "user_id": kid.id,
                            "due_date": None,  # For recurring, generated per instance
                        }

                        assignment_obj = ChoreAssignment(**assignment)
                        db.session.add(assignment_obj)
                        assignments.append(assignment_obj)

                        self.created_counts["assignments"] += 1
                        self.log(f"Assigned '{chore.name}' to {kid.username}")

        db.session.commit()

        return assignments

    def create_chore_instances(
        self,
        chores: List[Any],
        kids: List[Any],
        num_instances: int = 25
    ) -> List[Any]:
        """
        Create chore instances in various states.

        Args:
            chores: List of chore objects
            kids: List of kid user objects
            num_instances: Number of instances to create

        Returns:
            List of created instance objects
        """
        print(f"\n✅ Creating {num_instances} chore instances...")

        instances = []
        dates = generate_recent_dates(num_instances, days_back=7)

        import random

        for i in range(num_instances):
            chore = random.choice(chores)
            kid = random.choice(kids)
            due_date = dates[i].date()
            status = get_random_status_distribution()

            instance = {
                "chore_id": chore.id,
                "due_date": due_date,
                "status": status,
                "claimed_by": None,
                "claimed_at": None,
                "approved_by": None,
                "approved_at": None,
                "rejected_by": None,
                "rejected_at": None,
                "rejection_reason": None,
                "points_awarded": None,
            }

            # Set fields based on status
            if status in ["claimed", "approved", "rejected"]:
                instance["claimed_by"] = kid.id
                instance["claimed_at"] = dates[i] + timedelta(hours=random.randint(1, 12))

            if status in ["approved", "rejected"]:
                instance["approved_by"] = 1  # Parent ID
                instance["approved_at"] = instance["claimed_at"] + timedelta(hours=random.randint(1, 24))

            if status == "approved":
                instance["points_awarded"] = chore.points

            if status == "rejected":
                instance["rejected_by"] = 1  # Parent ID
                instance["rejected_at"] = instance["approved_at"]
                instance["rejection_reason"] = generate_rejection_reason()
                instance["approved_by"] = None
                instance["approved_at"] = None

            instance_obj = ChoreInstance(**instance)
            db.session.add(instance_obj)
            instances.append(instance_obj)

            self.created_counts["instances"] += 1
            self.log(f"Created instance: {chore.name} - {status}")

        db.session.commit()

        return instances

    def create_rewards(self, num_rewards: int = 7) -> List[Any]:
        """
        Create rewards with various point costs and limits.

        Args:
            num_rewards: Number of rewards to create

        Returns:
            List of created reward objects
        """
        print(f"\n🎁 Creating {num_rewards} rewards...")

        rewards = []
        reward_data_list = get_random_reward_data(num_rewards)

        import random

        for i, reward_data in enumerate(reward_data_list):
            reward_dict = {
                "name": reward_data["name"],
                "description": reward_data["description"],
                "points_cost": reward_data["points_cost"],
                "cooldown_days": random.choice([None, None, 7, 14]) if i % 3 == 0 else None,
                "max_claims_total": random.choice([None, None, 10, 20]) if i % 4 == 0 else None,
                "max_claims_per_kid": random.choice([None, None, 2, 3]) if i % 5 == 0 else None,
                "is_active": True,
            }

            reward_obj = Reward(**reward_dict)
            db.session.add(reward_obj)
            rewards.append(reward_obj)

            self.created_counts["rewards"] += 1
            self.log(f"Created reward: {reward_dict['name']} ({reward_dict['points_cost']} points)")

        db.session.commit()

        return rewards

    def create_reward_claims(
        self,
        rewards: List[Any],
        kids: List[Any],
        num_claims: int = 5
    ) -> List[Any]:
        """
        Create reward claims (some redeemed, some pending).

        Args:
            rewards: List of reward objects
            kids: List of kid user objects
            num_claims: Number of claims to create

        Returns:
            List of created claim objects
        """
        print(f"\n🎉 Creating {num_claims} reward claims...")

        claims = []
        import random

        for i in range(num_claims):
            reward = random.choice(rewards)
            kid = random.choice(kids)
            claimed_at = generate_random_date(days_back=7)
            status = random.choice(["approved", "approved", "approved", "pending"])

            claim = {
                "reward_id": reward.id,
                "user_id": kid.id,
                "points_spent": reward.points_cost,
                "claimed_at": claimed_at,
                "status": status,
                "approved_by": 1 if status == "approved" else None,
                "approved_at": claimed_at + timedelta(hours=1) if status == "approved" else None,
            }

            claim_obj = RewardClaim(**claim)
            db.session.add(claim_obj)
            claims.append(claim_obj)

            self.created_counts["reward_claims"] += 1
            self.log(f"Created claim: {kid.username} claimed '{reward.name}' - {status}")

        db.session.commit()

        return claims

    def create_points_history(
        self,
        instances: List[Any],
        claims: List[Any],
        kids: List[Any]
    ) -> List[Any]:
        """
        Create points history matching chore instances and reward claims.

        Args:
            instances: List of chore instance objects
            claims: List of reward claim objects
            kids: List of kid user objects

        Returns:
            List of created points history objects
        """
        print(f"\n💰 Creating points history...")

        history = []

        # Points from approved chore instances
        for instance in instances:
            if instance.status == "approved" and instance.points_awarded:
                entry = {
                    "user_id": instance.claimed_by,
                    "points_delta": instance.points_awarded,
                    "reason": f"Completed chore (instance {instance.id})",
                    "chore_instance_id": instance.id,
                    "reward_claim_id": None,
                    "created_by": instance.approved_by,
                    "created_at": instance.approved_at,
                }

                entry_obj = PointsHistory(**entry)
                db.session.add(entry_obj)
                history.append(entry_obj)

                self.created_counts["points_history"] += 1
                self.log(f"Points awarded: +{entry['points_delta']}")

        # Points spent on reward claims
        for claim in claims:
            if claim.status == "approved":
                entry = {
                    "user_id": claim.user_id,
                    "points_delta": -claim.points_spent,
                    "reason": f"Redeemed reward (claim {claim.id})",
                    "chore_instance_id": None,
                    "reward_claim_id": claim.id,
                    "created_by": claim.user_id,
                    "created_at": claim.approved_at or claim.claimed_at,
                }

                entry_obj = PointsHistory(**entry)
                db.session.add(entry_obj)
                history.append(entry_obj)

                self.created_counts["points_history"] += 1
                self.log(f"Points spent: {entry['points_delta']}")

        db.session.commit()

        # Update user points balances
        self._update_user_points(kids, history)

        return history

    def _update_user_points(self, kids: List[Any], history: List[Any]) -> None:
        """Update user points based on points history."""
        print(f"\n📊 Updating user points balances...")

        for kid in kids:
            kid_id = kid.id
            total_points = sum(
                entry.points_delta
                for entry in history
                if entry.user_id == kid_id
            )

            kid.points = max(0, total_points)  # Ensure non-negative

            self.log(f"{kid.username}: {kid.points} points")

        db.session.commit()

    def print_summary(self) -> None:
        """Print summary of created data."""
        print("\n" + "=" * 60)
        print("✨ SEED DATA GENERATION COMPLETE")
        print("=" * 60)
        print(f"Created:")
        print(f"  - {self.created_counts['users']} users")
        print(f"  - {self.created_counts['chores']} chores")
        print(f"  - {self.created_counts['assignments']} assignments")
        print(f"  - {self.created_counts['instances']} chore instances")
        print(f"  - {self.created_counts['rewards']} rewards")
        print(f"  - {self.created_counts['reward_claims']} reward claims")
        print(f"  - {self.created_counts['points_history']} points history entries")
        print("=" * 60)

    def generate_all(
        self,
        num_kids: int = 3,
        num_chores: int = 12,
        num_instances: int = 25,
        num_rewards: int = 7,
        num_claims: int = 5,
        reset: bool = False
    ) -> None:
        """
        Generate all seed data.

        Args:
            num_kids: Number of kid users to create
            num_chores: Number of chores to create
            num_instances: Number of chore instances to create
            num_rewards: Number of rewards to create
            num_claims: Number of reward claims to create
            reset: Whether to clear existing data first
        """
        print("\n🌱 ChoreControl Seed Data Generator")
        print("=" * 60)

        if reset:
            if not self.confirm_reset():
                print("\n❌ Seed generation cancelled.")
                return
            self.clear_database()

        # Create all data in dependency order
        users = self.create_users(num_parents=2, num_kids=num_kids)
        parents = users["parents"]
        kids = users["kids"]

        chores = self.create_chores(
            num_chores=num_chores,
            created_by_user=parents[0] if parents else None
        )

        assignments = self.create_assignments(chores, kids)

        # Generate instances for chores (this creates instances including those with no due date)
        print(f"\n🔄 Generating chore instances from definitions...")
        generated_count = 0
        for chore in chores:
            instances_created = generate_instances_for_chore(chore)
            generated_count += len(instances_created)
            if instances_created:
                self.log(f"Generated {len(instances_created)} instance(s) for '{chore.name}'")
        self.created_counts["instances"] += generated_count
        print(f"  Generated {generated_count} instances from chore definitions")

        # Also create some historical instances in various states
        instances = self.create_chore_instances(chores, kids, num_instances=num_instances)
        rewards = self.create_rewards(num_rewards=num_rewards)
        claims = self.create_reward_claims(rewards, kids, num_claims=num_claims)
        history = self.create_points_history(instances, claims, kids)

        self.print_summary()


def main():
    """Main entry point for seed script."""
    parser = argparse.ArgumentParser(
        description="Generate seed data for ChoreControl development",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python seed.py --reset --verbose
  python seed.py --kids 5 --chores 20
  python seed.py --preserve --verbose
        """
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear existing data before seeding (requires confirmation)"
    )

    parser.add_argument(
        "--preserve",
        action="store_true",
        help="Preserve existing data (add to it, don't clear)"
    )

    parser.add_argument(
        "--kids",
        type=int,
        default=3,
        help="Number of kid users to create (default: 3)"
    )

    parser.add_argument(
        "--chores",
        type=int,
        default=12,
        help="Number of chores to create (default: 12)"
    )

    parser.add_argument(
        "--instances",
        type=int,
        default=25,
        help="Number of chore instances to create (default: 25)"
    )

    parser.add_argument(
        "--rewards",
        type=int,
        default=7,
        help="Number of rewards to create (default: 7)"
    )

    parser.add_argument(
        "--claims",
        type=int,
        default=5,
        help="Number of reward claims to create (default: 5)"
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed output"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.reset and args.preserve:
        print("❌ Error: Cannot use --reset and --preserve together")
        sys.exit(1)

    # Disable scheduler for seeding
    import os
    os.environ['SCHEDULER_ENABLED'] = 'false'

    app = create_app()
    with app.app_context():
        generator = SeedDataGenerator(verbose=args.verbose)
        generator.generate_all(
            num_kids=args.kids,
            num_chores=args.chores,
            num_instances=args.instances,
            num_rewards=args.rewards,
            num_claims=args.claims,
            reset=args.reset
        )


if __name__ == "__main__":
    main()
