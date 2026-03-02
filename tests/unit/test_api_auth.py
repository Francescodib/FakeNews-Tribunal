import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch

from api.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
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
