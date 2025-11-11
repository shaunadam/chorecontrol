"""
Pytest configuration and shared fixtures for ChoreControl tests.

This file provides common test fixtures that can be used across all test modules.
"""

import os
import tempfile

import pytest


@pytest.fixture(scope="session")
def app():
    """
    Create and configure a Flask application instance for testing.

    This fixture creates a test application with a temporary database.
    It's scoped to 'session' so it's created once per test session.

    TODO: Implement once Flask app is created in addon/app.py

    Example usage in tests:
        def test_something(app):
            assert app is not None
    """
    # TODO: Import and configure Flask app when ready
    # from addon.app import create_app
    # app = create_app('testing')
    # return app
    pytest.skip("Flask app not yet implemented")


@pytest.fixture(scope="function")
def client(app):
    """
    Create a test client for the Flask application.

    This fixture provides a test client that can make requests to the app
    without running a real server.

    TODO: Implement once Flask app fixture is ready

    Example usage in tests:
        def test_endpoint(client):
            response = client.get('/api/health')
            assert response.status_code == 200
    """
    pytest.skip("Flask app not yet implemented")


@pytest.fixture(scope="function")
def db(app):
    """
    Create a fresh database for each test.

    This fixture creates a temporary database, runs migrations,
    and tears it down after the test completes.

    TODO: Implement once SQLAlchemy models are ready

    Example usage in tests:
        def test_database(db):
            # Database is fresh and empty
            pass
    """
    pytest.skip("Database models not yet implemented")


@pytest.fixture(scope="function")
def sample_user(db):
    """
    Create a sample user for testing.

    TODO: Implement once User model is ready

    Example usage in tests:
        def test_user_points(sample_user):
            assert sample_user.points == 0
    """
    pytest.skip("User model not yet implemented")


@pytest.fixture(scope="function")
def sample_chore(db, sample_user):
    """
    Create a sample chore for testing.

    TODO: Implement once Chore model is ready

    Example usage in tests:
        def test_chore(sample_chore):
            assert sample_chore.points > 0
    """
    pytest.skip("Chore model not yet implemented")


@pytest.fixture(scope="function")
def auth_headers():
    """
    Provide authentication headers for API testing.

    Simulates Home Assistant ingress authentication headers.

    TODO: Update based on actual authentication implementation

    Example usage in tests:
        def test_protected_endpoint(client, auth_headers):
            response = client.get('/api/users', headers=auth_headers)
            assert response.status_code == 200
    """
    return {
        "X-Ingress-User": "test-ha-user-id",
        "X-Ingress-Name": "Test User",
    }


@pytest.fixture(scope="function")
def parent_headers():
    """
    Provide authentication headers for a parent user.

    TODO: Update based on actual role implementation
    """
    return {
        "X-Ingress-User": "parent-user-id",
        "X-Ingress-Name": "Parent User",
    }


@pytest.fixture(scope="function")
def kid_headers():
    """
    Provide authentication headers for a kid user.

    TODO: Update based on actual role implementation
    """
    return {
        "X-Ingress-User": "kid-user-id",
        "X-Ingress-Name": "Kid User",
    }


# Pytest markers are defined in pyproject.toml
# Available markers:
# - @pytest.mark.unit: Unit tests (fast, isolated)
# - @pytest.mark.integration: Integration tests (slower, test interactions)
# - @pytest.mark.e2e: End-to-end tests (slowest, full system tests)
# - @pytest.mark.slow: Slow running tests
