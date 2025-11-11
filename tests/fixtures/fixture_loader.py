"""
Pytest fixtures for loading sample data.

This module provides fixtures that can be used in unit tests
to load realistic sample data.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any

import pytest


# Path to the sample data JSON file
FIXTURES_DIR = Path(__file__).parent
SAMPLE_DATA_FILE = FIXTURES_DIR / "sample_data.json"


def load_sample_data() -> Dict[str, Any]:
    """
    Load sample data from JSON file.

    Returns:
        Dictionary containing all sample data
    """
    with open(SAMPLE_DATA_FILE, 'r') as f:
        return json.load(f)


@pytest.fixture
def sample_data():
    """
    Pytest fixture that provides all sample data.

    Usage:
        def test_something(sample_data):
            users = sample_data['users']
            assert len(users) == 3
    """
    return load_sample_data()


@pytest.fixture
def sample_users(sample_data):
    """
    Pytest fixture that provides sample users.

    Returns:
        List of user dictionaries
    """
    return sample_data['users']


@pytest.fixture
def sample_chores(sample_data):
    """
    Pytest fixture that provides sample chores.

    Returns:
        List of chore dictionaries
    """
    return sample_data['chores']


@pytest.fixture
def sample_instances(sample_data):
    """
    Pytest fixture that provides sample chore instances.

    Returns:
        List of chore instance dictionaries
    """
    return sample_data['chore_instances']


@pytest.fixture
def sample_rewards(sample_data):
    """
    Pytest fixture that provides sample rewards.

    Returns:
        List of reward dictionaries
    """
    return sample_data['rewards']


@pytest.fixture
def sample_reward_claims(sample_data):
    """
    Pytest fixture that provides sample reward claims.

    Returns:
        List of reward claim dictionaries
    """
    return sample_data['reward_claims']


@pytest.fixture
def sample_points_history(sample_data):
    """
    Pytest fixture that provides sample points history.

    Returns:
        List of points history dictionaries
    """
    return sample_data['points_history']


@pytest.fixture
def sample_parent(sample_users):
    """
    Pytest fixture that provides a sample parent user.

    Returns:
        Parent user dictionary
    """
    return next(u for u in sample_users if u['role'] == 'parent')


@pytest.fixture
def sample_kids(sample_users):
    """
    Pytest fixture that provides sample kid users.

    Returns:
        List of kid user dictionaries
    """
    return [u for u in sample_users if u['role'] == 'kid']


# TODO: When models are implemented, add these fixtures:
#
# @pytest.fixture
# def db_session():
#     """Provide a database session for tests."""
#     # Setup test database
#     # Yield session
#     # Teardown
#     pass
#
# @pytest.fixture
# def populated_db(db_session, sample_data):
#     """Populate database with sample data."""
#     # Create all objects from sample_data
#     # Add to db_session
#     # Commit
#     # Yield
#     # Rollback/cleanup
#     pass
