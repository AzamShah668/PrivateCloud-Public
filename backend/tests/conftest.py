"""Shared test fixtures for the PrivateCloud backend."""

from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.auth import create_access_token
from app.main import app


@pytest.fixture()
def client():
    """FastAPI test client — no real DB needed."""
    return TestClient(app)


@pytest.fixture()
def admin_token():
    """JWT token for a user with role='admin'."""
    return create_access_token({"sub": "testadmin", "role": "admin"})


@pytest.fixture()
def user_token():
    """JWT token for a regular user."""
    return create_access_token({"sub": "testuser", "role": "user"})


@pytest.fixture()
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture()
def user_headers(user_token):
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture(autouse=True)
def mock_get_user_by_username():
    """
    Mock the DB lookup so get_current_user succeeds without a real database.
    Returns an admin user when username is 'testadmin', a regular user otherwise.
    """
    def _lookup(username: str):
        if username == "testadmin":
            return {
                "id": 1,
                "username": "testadmin",
                "password_hash": "$2b$12$fake",
                "role": "admin",
                "daily_quota": 10,
                "created_at": "2025-01-01T00:00:00+00:00",
            }
        if username == "testuser":
            return {
                "id": 2,
                "username": "testuser",
                "password_hash": "$2b$12$fake",
                "role": "user",
                "daily_quota": 3,
                "created_at": "2025-01-01T00:00:00+00:00",
            }
        return None

    with patch("app.auth.get_user_by_username", side_effect=_lookup):
        yield
