"""Pytest configuration and fixtures for ChoreControl tests."""

import pytest
import sys
from pathlib import Path

# Add parent directory to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from models import db, User, Chore, ChoreInstance, Reward, RewardClaim, PointsHistory


@pytest.fixture(scope='function')
def app():
    """Create application instance for testing."""
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
def client(app):
    """Create test client for making requests."""
    return app.test_client()


@pytest.fixture(scope='function')
def db_session(app):
    """Create database session for tests."""
    with app.app_context():
        yield db.session


@pytest.fixture
def parent_user(db_session):
    """Create a parent user for testing."""
    user = User(
        ha_user_id='parent-ha-001',
        username='Test Parent',
        role='parent',
        points=0
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def kid_user(db_session):
    """Create a kid user for testing."""
    user = User(
        ha_user_id='kid-ha-001',
        username='Test Kid',
        role='kid',
        points=50
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def kid_user_2(db_session):
    """Create a second kid user for testing."""
    user = User(
        ha_user_id='kid-ha-002',
        username='Test Kid 2',
        role='kid',
        points=25
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def parent_headers(parent_user):
    """Create headers for parent authentication."""
    return {'X-Ingress-User': parent_user.ha_user_id}


@pytest.fixture
def kid_headers(kid_user):
    """Create headers for kid authentication."""
    return {'X-Ingress-User': kid_user.ha_user_id}


@pytest.fixture
def unauthenticated_headers():
    """Create headers without authentication."""
    return {}


@pytest.fixture
def sample_chore(db_session, parent_user):
    """Create a sample chore for testing."""
    chore = Chore(
        name='Take out trash',
        description='Roll bins to curb',
        points=5,
        recurrence_type='simple',
        recurrence_pattern={'type': 'simple', 'interval': 'weekly', 'every_n': 1},
        assignment_type='individual',
        requires_approval=True,
        created_by=parent_user.id,
        is_active=True
    )
    db_session.add(chore)
    db_session.commit()
    return chore


@pytest.fixture
def sample_reward(db_session):
    """Create a sample reward for testing."""
    reward = Reward(
        name='Ice cream trip',
        description='Go get ice cream',
        points_cost=20,
        cooldown_days=7,
        max_claims_total=None,
        max_claims_per_kid=None,
        is_active=True
    )
    db_session.add(reward)
    db_session.commit()
    return reward


@pytest.fixture
def user_with_points_history(db_session, kid_user, parent_user):
    """Create a kid user with some points history."""
    from datetime import datetime, timedelta

    # Add some points history with explicit timestamps to ensure proper ordering
    base_time = datetime.utcnow() - timedelta(hours=5)

    history_entries = [
        PointsHistory(
            user_id=kid_user.id,
            points_delta=10,
            reason='Completed chore: Dishes',
            created_by=parent_user.id,
            created_at=base_time
        ),
        PointsHistory(
            user_id=kid_user.id,
            points_delta=15,
            reason='Completed chore: Vacuum',
            created_by=parent_user.id,
            created_at=base_time + timedelta(hours=1)
        ),
        PointsHistory(
            user_id=kid_user.id,
            points_delta=25,
            reason='Completed chore: Laundry',
            created_by=parent_user.id,
            created_at=base_time + timedelta(hours=2)
        ),
        PointsHistory(
            user_id=kid_user.id,
            points_delta=-10,
            reason='Claimed reward: Extra screen time',
            created_by=kid_user.id,
            created_at=base_time + timedelta(hours=3)
        ),
        PointsHistory(
            user_id=kid_user.id,
            points_delta=10,
            reason='Completed chore: Mow lawn',
            created_by=parent_user.id,
            created_at=base_time + timedelta(hours=4)
        )
    ]

    for entry in history_entries:
        db_session.add(entry)

    db_session.commit()
    return kid_user
