"""
Unit tests for auth endpoints — patches repository functions directly so no
real database is needed.  The startup DB-reachability check is suppressed for
speed (it would connect to the test SQLite DB but would still take a round-trip
through the startup_checks code).
"""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch

from api.main import app


@pytest.fixture()
async def client():
    """
    Yield an httpx AsyncClient wired to the FastAPI app.

    run_startup_checks is patched to a no-op so that tests do not incur the
    SQLite startup check delay and do not need Alembic tables to exist.
    """
    with patch("api.main.run_startup_checks", new=AsyncMock()):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_register_success(client):
    mock_user = AsyncMock()
    mock_user.id = __import__("uuid").uuid4()

    with (
        patch("api.routers.auth.get_user_by_email", return_value=None),
        patch("api.routers.auth.create_user", return_value=mock_user),
        patch("api.routers.auth.create_refresh_token", return_value=AsyncMock()),
    ):
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com", "password": "securepassword"},
        )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    mock_user = AsyncMock()
    with patch("api.routers.auth.get_user_by_email", return_value=mock_user):
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "existing@example.com", "password": "securepassword"},
        )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    with patch("api.routers.auth.get_user_by_email", return_value=None):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "wrong"},
        )
    assert response.status_code == 401
