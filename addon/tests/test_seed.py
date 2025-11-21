"""Tests for the seed data generator."""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch

# Add parent directory to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from models import db, User, Chore, ChoreInstance, Reward, RewardClaim, PointsHistory, ChoreAssignment
from seed import SeedDataGenerator


@pytest.fixture(scope='function')
def seed_app():
    """Create application instance for seed testing."""
    app = create_app('testing')

    # Create database tables
    with app.app_context():
        db.create_all()

    yield app

    # Clean up
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def seed_generator(seed_app):
    """Create a seed generator for testing."""
    with seed_app.app_context():
        generator = SeedDataGenerator(verbose=False)
        yield generator


class TestSeedDataGenerator:
    """Tests for the SeedDataGenerator class."""

    def test_create_users(self, seed_app, seed_generator):
        """Test that create_users creates the correct number of users with passwords."""
        with seed_app.app_context():
            users = seed_generator.create_users(num_parents=2, num_kids=3)

            # Check counts
            assert len(users['parents']) == 2
            assert len(users['kids']) == 3
            assert User.query.count() == 5

            # Check parent properties
            for parent in users['parents']:
                assert parent.role == 'parent'
                assert parent.has_password()
                assert parent.check_password('password')

            # Check kid properties
            for kid in users['kids']:
                assert kid.role == 'kid'
                assert kid.has_password()
                assert kid.check_password('password')

    def test_create_chores(self, seed_app, seed_generator):
        """Test that create_chores creates chores correctly."""
        with seed_app.app_context():
            # First create a parent to be the creator
            users = seed_generator.create_users(num_parents=1, num_kids=0)
            parent = users['parents'][0]

            chores = seed_generator.create_chores(num_chores=10, created_by_user=parent)

            # Check count
            assert len(chores) == 10
            assert Chore.query.count() == 10

            # Check properties
            for chore in chores:
                assert chore.name is not None
                assert chore.points > 0
                assert chore.is_active is True
                assert chore.created_by == parent.id

    def test_create_assignments(self, seed_app, seed_generator):
        """Test that create_assignments links chores to kids."""
        with seed_app.app_context():
            users = seed_generator.create_users(num_parents=1, num_kids=3)
            chores = seed_generator.create_chores(num_chores=5, created_by_user=users['parents'][0])
            assignments = seed_generator.create_assignments(chores, users['kids'])

            # Check that assignments were created
            assert len(assignments) > 0
            assert ChoreAssignment.query.count() == len(assignments)

            # Check assignment properties
            for assignment in assignments:
                assert assignment.chore_id is not None
                assert assignment.user_id is not None

    def test_create_chore_instances(self, seed_app, seed_generator):
        """Test that create_chore_instances creates instances with various statuses."""
        with seed_app.app_context():
            users = seed_generator.create_users(num_parents=1, num_kids=3)
            chores = seed_generator.create_chores(num_chores=5, created_by_user=users['parents'][0])
            instances = seed_generator.create_chore_instances(chores, users['kids'], num_instances=20)

            # Check count
            assert len(instances) == 20
            assert ChoreInstance.query.count() == 20

            # Check that various statuses exist
            statuses = [i.status for i in instances]
            # At least some instances should be in different states
            assert len(set(statuses)) > 1

    def test_create_rewards(self, seed_app, seed_generator):
        """Test that create_rewards creates rewards correctly."""
        with seed_app.app_context():
            rewards = seed_generator.create_rewards(num_rewards=7)

            # Check count
            assert len(rewards) == 7
            assert Reward.query.count() == 7

            # Check properties
            for reward in rewards:
                assert reward.name is not None
                assert reward.points_cost > 0
                assert reward.is_active is True

    def test_create_reward_claims(self, seed_app, seed_generator):
        """Test that create_reward_claims creates claims correctly."""
        with seed_app.app_context():
            users = seed_generator.create_users(num_parents=1, num_kids=3)
            rewards = seed_generator.create_rewards(num_rewards=5)
            claims = seed_generator.create_reward_claims(rewards, users['kids'], num_claims=5)

            # Check count
            assert len(claims) == 5
            assert RewardClaim.query.count() == 5

            # Check properties
            for claim in claims:
                assert claim.reward_id is not None
                assert claim.user_id is not None
                assert claim.points_spent > 0

    def test_create_points_history(self, seed_app, seed_generator):
        """Test that create_points_history creates history entries."""
        with seed_app.app_context():
            users = seed_generator.create_users(num_parents=1, num_kids=3)
            chores = seed_generator.create_chores(num_chores=5, created_by_user=users['parents'][0])
            instances = seed_generator.create_chore_instances(chores, users['kids'], num_instances=15)
            rewards = seed_generator.create_rewards(num_rewards=3)
            claims = seed_generator.create_reward_claims(rewards, users['kids'], num_claims=3)
            history = seed_generator.create_points_history(instances, claims, users['kids'])

            # Check that history was created
            assert len(history) > 0
            assert PointsHistory.query.count() == len(history)

    def test_generate_all(self, seed_app, seed_generator):
        """Test that generate_all creates all data correctly."""
        with seed_app.app_context():
            seed_generator.generate_all(
                num_kids=3,
                num_chores=10,
                num_instances=20,
                num_rewards=5,
                num_claims=3,
                reset=False
            )

            # Check all entities were created
            assert User.query.count() == 5  # 2 parents + 3 kids
            assert Chore.query.count() == 10
            assert ChoreInstance.query.count() == 20
            assert Reward.query.count() == 5
            assert RewardClaim.query.count() == 3

    def test_clear_database_preserves_admin(self, seed_app, seed_generator):
        """Test that clear_database preserves the admin user."""
        with seed_app.app_context():
            # Create admin user first
            admin = User(
                ha_user_id='local-admin',
                username='admin',
                role='parent',
                points=0
            )
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()
            admin_id = admin.id

            # Create some other data
            seed_generator.generate_all(
                num_kids=2,
                num_chores=5,
                num_instances=10,
                num_rewards=3,
                num_claims=2,
                reset=False
            )

            # Now clear the database
            seed_generator.clear_database()

            # Admin should still exist
            admin_after = User.query.filter_by(ha_user_id='local-admin').first()
            assert admin_after is not None
            assert admin_after.id == admin_id
            assert admin_after.username == 'admin'
            assert admin_after.role == 'parent'
            assert admin_after.check_password('admin')

            # All other data should be cleared
            assert User.query.count() == 1  # Only admin
            assert Chore.query.count() == 0
            assert ChoreInstance.query.count() == 0
            assert Reward.query.count() == 0
            assert RewardClaim.query.count() == 0
            assert PointsHistory.query.count() == 0

    def test_clear_database_creates_admin_if_missing(self, seed_app, seed_generator):
        """Test that clear_database creates admin user if it doesn't exist."""
        import warnings
        from sqlalchemy.exc import SAWarning

        with seed_app.app_context():
            # Create some data without admin
            other_user = User(
                ha_user_id='other-user',
                username='other',
                role='parent',
                points=0
            )
            db.session.add(other_user)
            db.session.commit()

            # Clear reference to avoid identity map conflicts
            del other_user
            db.session.expire_all()

            # Clear the database (ignore SQLAlchemy identity map warnings in tests)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SAWarning)
                seed_generator.clear_database()

            # Admin should be created
            admin = User.query.filter_by(ha_user_id='local-admin').first()
            assert admin is not None
            assert admin.username == 'admin'
            assert admin.role == 'parent'
            assert admin.check_password('admin')

            # Other user should be deleted
            other = User.query.filter_by(ha_user_id='other-user').first()
            assert other is None

    def test_reset_preserves_admin(self, seed_app, seed_generator):
        """Test that running with reset=True preserves the admin user."""
        with seed_app.app_context():
            # Create admin user
            admin = User(
                ha_user_id='local-admin',
                username='admin',
                role='parent',
                points=0
            )
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()

            # Run generate_all with reset=True (mock the confirm to return True)
            with patch.object(seed_generator, 'confirm_reset', return_value=True):
                seed_generator.generate_all(
                    num_kids=2,
                    num_chores=5,
                    num_instances=10,
                    num_rewards=3,
                    num_claims=2,
                    reset=True
                )

            # Admin should still exist
            admin_after = User.query.filter_by(ha_user_id='local-admin').first()
            assert admin_after is not None
            assert admin_after.username == 'admin'
            assert admin_after.check_password('admin')

            # New seed data should also exist
            # 2 parents + 2 kids + 1 admin = 5 users
            assert User.query.count() == 5

    def test_user_passwords_work(self, seed_app, seed_generator):
        """Test that seeded users can authenticate with default password."""
        with seed_app.app_context():
            users = seed_generator.create_users(num_parents=2, num_kids=3)

            # Test all users can authenticate
            for parent in users['parents']:
                user = User.query.get(parent.id)
                assert user.has_password()
                assert user.check_password('password')
                assert not user.check_password('wrong')

            for kid in users['kids']:
                user = User.query.get(kid.id)
                assert user.has_password()
                assert user.check_password('password')
                assert not user.check_password('wrong')

    def test_chore_instances_have_valid_references(self, seed_app, seed_generator):
        """Test that chore instances reference valid chores and users."""
        with seed_app.app_context():
            users = seed_generator.create_users(num_parents=1, num_kids=3)
            chores = seed_generator.create_chores(num_chores=5, created_by_user=users['parents'][0])
            instances = seed_generator.create_chore_instances(chores, users['kids'], num_instances=15)

            chore_ids = {c.id for c in chores}
            kid_ids = {k.id for k in users['kids']}

            for instance in instances:
                # Chore ID should be valid
                assert instance.chore_id in chore_ids

                # If claimed, claimer should be valid
                if instance.claimed_by:
                    assert instance.claimed_by in kid_ids

    def test_points_history_updates_balances(self, seed_app, seed_generator):
        """Test that creating points history updates user point balances."""
        with seed_app.app_context():
            users = seed_generator.create_users(num_parents=1, num_kids=3)
            chores = seed_generator.create_chores(num_chores=5, created_by_user=users['parents'][0])
            instances = seed_generator.create_chore_instances(chores, users['kids'], num_instances=15)
            rewards = seed_generator.create_rewards(num_rewards=3)
            claims = seed_generator.create_reward_claims(rewards, users['kids'], num_claims=3)
            seed_generator.create_points_history(instances, claims, users['kids'])

            # Check that kids have updated points
            for kid in users['kids']:
                user = User.query.get(kid.id)
                # Points should be non-negative
                assert user.points >= 0

    def test_created_counts_tracking(self, seed_app, seed_generator):
        """Test that the generator tracks created counts correctly."""
        with seed_app.app_context():
            seed_generator.generate_all(
                num_kids=3,
                num_chores=10,
                num_instances=20,
                num_rewards=5,
                num_claims=3,
                reset=False
            )

            # Check counts match expectations
            assert seed_generator.created_counts['users'] == 5  # 2 parents + 3 kids
            assert seed_generator.created_counts['chores'] == 10
            assert seed_generator.created_counts['instances'] == 20
            assert seed_generator.created_counts['rewards'] == 5
            assert seed_generator.created_counts['reward_claims'] == 3
            assert seed_generator.created_counts['points_history'] > 0

    def test_verbose_mode(self, seed_app, capsys):
        """Test that verbose mode produces output."""
        with seed_app.app_context():
            generator = SeedDataGenerator(verbose=True)
            generator.create_users(num_parents=1, num_kids=1)

            captured = capsys.readouterr()
            assert 'Created parent' in captured.out
            assert 'Created kid' in captured.out


class TestSeedDataIntegrity:
    """Tests for seed data integrity and relationships."""

    def test_chore_assignment_relationship(self, seed_app, seed_generator):
        """Test that chore assignments properly link chores and users."""
        with seed_app.app_context():
            users = seed_generator.create_users(num_parents=1, num_kids=3)
            chores = seed_generator.create_chores(num_chores=5, created_by_user=users['parents'][0])
            seed_generator.create_assignments(chores, users['kids'])

            # Check relationships work
            for chore in Chore.query.all():
                for assignment in chore.assignments:
                    assert assignment.user is not None
                    assert assignment.user.role == 'kid'

    def test_reward_claim_relationship(self, seed_app, seed_generator):
        """Test that reward claims properly reference rewards and users."""
        with seed_app.app_context():
            users = seed_generator.create_users(num_parents=1, num_kids=3)
            rewards = seed_generator.create_rewards(num_rewards=5)
            claims = seed_generator.create_reward_claims(rewards, users['kids'], num_claims=5)

            for claim in claims:
                # Relationships should work
                assert claim.reward is not None
                assert claim.user is not None
                assert claim.user.role == 'kid'
                # Points spent should match reward cost
                assert claim.points_spent == claim.reward.points_cost

    def test_points_history_references(self, seed_app, seed_generator):
        """Test that points history entries have valid references."""
        with seed_app.app_context():
            users = seed_generator.create_users(num_parents=1, num_kids=3)
            chores = seed_generator.create_chores(num_chores=5, created_by_user=users['parents'][0])
            instances = seed_generator.create_chore_instances(chores, users['kids'], num_instances=15)
            rewards = seed_generator.create_rewards(num_rewards=3)
            claims = seed_generator.create_reward_claims(rewards, users['kids'], num_claims=3)
            seed_generator.create_points_history(instances, claims, users['kids'])

            for entry in PointsHistory.query.all():
                # User reference should be valid
                assert entry.user is not None
                assert entry.user.role == 'kid'

                # Should have either chore_instance_id or reward_claim_id
                has_chore_ref = entry.chore_instance_id is not None
                has_reward_ref = entry.reward_claim_id is not None
                assert has_chore_ref or has_reward_ref


class TestAdminUserPreservation:
    """Specific tests for admin user preservation during seed operations."""

    def test_admin_preserved_with_modified_password(self, seed_app, seed_generator):
        """Test that admin is preserved even if password was changed."""
        with seed_app.app_context():
            # Create admin with custom password
            admin = User(
                ha_user_id='local-admin',
                username='admin',
                role='parent',
                points=0
            )
            admin.set_password('custom-password')
            db.session.add(admin)
            db.session.commit()

            # Clear database
            seed_generator.clear_database()

            # Admin should be preserved with original password
            admin_after = User.query.filter_by(ha_user_id='local-admin').first()
            assert admin_after is not None
            assert admin_after.check_password('custom-password')

    def test_admin_preserved_with_points_history(self, seed_app, seed_generator):
        """Test that admin's associated data is cleared but user is kept."""
        with seed_app.app_context():
            # Create admin
            admin = User(
                ha_user_id='local-admin',
                username='admin',
                role='parent',
                points=0
            )
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()

            # Generate data
            seed_generator.generate_all(
                num_kids=2,
                num_chores=5,
                num_instances=10,
                num_rewards=3,
                num_claims=2,
                reset=False
            )

            # Clear database
            seed_generator.clear_database()

            # Admin should exist but no other data
            assert User.query.count() == 1
            admin_after = User.query.first()
            assert admin_after.ha_user_id == 'local-admin'

    def test_multiple_resets_preserve_admin(self, seed_app, seed_generator):
        """Test that multiple resets consistently preserve admin."""
        with seed_app.app_context():
            # Create admin
            admin = User(
                ha_user_id='local-admin',
                username='admin',
                role='parent',
                points=0
            )
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()
            admin_id = admin.id

            # Run multiple resets
            for _ in range(3):
                with patch.object(seed_generator, 'confirm_reset', return_value=True):
                    seed_generator.generate_all(
                        num_kids=2,
                        num_chores=3,
                        num_instances=5,
                        num_rewards=2,
                        num_claims=1,
                        reset=True
                    )

                # Admin should still be the same
                admin_after = User.query.filter_by(ha_user_id='local-admin').first()
                assert admin_after is not None
                assert admin_after.id == admin_id
