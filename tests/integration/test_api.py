"""
Integration tests for the FastAPI application.

Uses httpx.AsyncClient with ASGITransport and the in-memory SQLite DB
(via the conftest.py fixtures). No real LLM calls, no real PostgreSQL.
BackgroundTasks that would start LLM debate are patched out.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_health(test_app: AsyncClient):
    response = await test_app.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Auth — Register
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_register_success(test_app: AsyncClient):
    payload = {"email": "newuser@example.com", "password": "ValidPass1!"}
    response = await test_app.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.integration
async def test_register_duplicate_email(test_app: AsyncClient):
    payload = {"email": "duplicate@example.com", "password": "ValidPass1!"}
    # First registration must succeed
    r1 = await test_app.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201
    # Second with same email must be rejected
    r2 = await test_app.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == 409


@pytest.mark.integration
async def test_register_invalid_email(test_app: AsyncClient):
    payload = {"email": "notanemail", "password": "ValidPass1!"}
    response = await test_app.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.integration
async def test_register_short_password(test_app: AsyncClient):
    payload = {"email": "user2@example.com", "password": "short"}
    response = await test_app.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Auth — Login
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_login_success(test_app: AsyncClient):
    email = "login-ok@example.com"
    password = "ValidPass1!"
    # Register first
    await test_app.post("/api/v1/auth/register", json={"email": email, "password": password})
    # Then login
    response = await test_app.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.integration
async def test_login_wrong_password(test_app: AsyncClient):
    email = "login-bad@example.com"
    # Register
    await test_app.post("/api/v1/auth/register", json={"email": email, "password": "GoodPass1!"})
    # Login with wrong password
    response = await test_app.post("/api/v1/auth/login", json={"email": email, "password": "WrongPass!"})
    assert response.status_code == 401


@pytest.mark.integration
async def test_login_nonexistent_user(test_app: AsyncClient):
    response = await test_app.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "SomePass1!"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Auth — /me
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_me_authenticated(test_app: AsyncClient, auth_headers: dict):
    response = await test_app.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "email" in data
    assert "is_admin" in data
    assert data["is_admin"] is False


@pytest.mark.integration
async def test_me_unauthenticated(test_app: AsyncClient):
    # FastAPI's HTTPBearer returns 403 when no Authorization header is present
    response = await test_app.get("/api/v1/auth/me")
    assert response.status_code in (401, 403)


@pytest.mark.integration
async def test_me_invalid_token(test_app: AsyncClient):
    response = await test_app.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer this.is.not.valid"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Auth — PATCH /me
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_update_me_email(test_app: AsyncClient):
    email = f"patch-me-{uuid.uuid4().hex[:6]}@example.com"
    password = "ValidPass1!"
    # Register
    reg = await test_app.post("/api/v1/auth/register", json={"email": email, "password": password})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    # Change email
    new_email = f"changed-{uuid.uuid4().hex[:6]}@example.com"
    response = await test_app.patch("/api/v1/auth/me", json={"email": new_email}, headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == new_email


@pytest.mark.integration
async def test_update_me_wrong_current_password(test_app: AsyncClient):
    email = f"patch-pw-{uuid.uuid4().hex[:6]}@example.com"
    password = "ValidPass1!"
    reg = await test_app.post("/api/v1/auth/register", json={"email": email, "password": password})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    # Try to change password with wrong current_password
    response = await test_app.patch(
        "/api/v1/auth/me",
        json={"current_password": "WrongPass!", "new_password": "NewValidPass1!"},
        headers=headers,
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_submit_analysis(test_app: AsyncClient, auth_headers: dict):
    """Submit an analysis — the background debate task is patched so no LLM is called."""
    with patch("api.routers.analysis._run_debate", new=AsyncMock()):
        response = await test_app.post(
            "/api/v1/analysis",
            json={
                "claim": "The Earth is approximately 4.5 billion years old.",
                "language": "en",
                "llm_provider": "anthropic",
            },
            headers=auth_headers,
        )
    # 202 Accepted
    assert response.status_code == 202
    data = response.json()
    assert "analysis_id" in data
    assert "status_url" in data
    return data["analysis_id"]


@pytest.mark.integration
async def test_get_analysis(test_app: AsyncClient, auth_headers: dict):
    """Submit then retrieve an analysis by ID."""
    with patch("api.routers.analysis._run_debate", new=AsyncMock()):
        submit = await test_app.post(
            "/api/v1/analysis",
            json={"claim": "The Earth is approximately 4.5 billion years old.", "language": "en"},
            headers=auth_headers,
        )
    assert submit.status_code == 202
    analysis_id = submit.json()["analysis_id"]

    response = await test_app.get(f"/api/v1/analysis/{analysis_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == analysis_id
    assert data["status"] in ("pending", "running", "completed", "failed")


@pytest.mark.integration
async def test_list_analyses(test_app: AsyncClient, auth_headers: dict):
    """List analyses — returns a paginated response."""
    # Ensure at least one analysis exists
    with patch("api.routers.analysis._run_debate", new=AsyncMock()):
        await test_app.post(
            "/api/v1/analysis",
            json={"claim": "This is a claim long enough to submit.", "language": "en"},
            headers=auth_headers,
        )
    response = await test_app.get("/api/v1/analysis", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert isinstance(data["items"], list)


@pytest.mark.integration
async def test_delete_analysis(test_app: AsyncClient, auth_headers: dict):
    """Submit then delete an analysis."""
    with patch("api.routers.analysis._run_debate", new=AsyncMock()):
        submit = await test_app.post(
            "/api/v1/analysis",
            json={"claim": "This claim will be deleted after submission.", "language": "en"},
            headers=auth_headers,
        )
    assert submit.status_code == 202
    analysis_id = submit.json()["analysis_id"]

    delete_response = await test_app.delete(
        f"/api/v1/analysis/{analysis_id}", headers=auth_headers
    )
    assert delete_response.status_code == 204

    # Verify it is gone
    get_response = await test_app.get(f"/api/v1/analysis/{analysis_id}", headers=auth_headers)
    assert get_response.status_code == 404


@pytest.mark.integration
async def test_get_analysis_not_found(test_app: AsyncClient, auth_headers: dict):
    fake_id = str(uuid.uuid4())
    response = await test_app.get(f"/api/v1/analysis/{fake_id}", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.integration
async def test_analysis_requires_auth(test_app: AsyncClient):
    response = await test_app.get("/api/v1/analysis")
    assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_create_webhook(test_app: AsyncClient, auth_headers: dict):
    response = await test_app.post(
        "/api/v1/webhooks",
        json={"url": "https://example.com/webhook", "secret": "mysecret"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["url"] == "https://example.com/webhook"
    assert data["is_active"] is True


@pytest.mark.integration
async def test_list_webhooks(test_app: AsyncClient, auth_headers: dict):
    # Create one first
    await test_app.post(
        "/api/v1/webhooks",
        json={"url": "https://example.com/webhook2"},
        headers=auth_headers,
    )
    response = await test_app.get("/api/v1/webhooks", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.integration
async def test_webhooks_require_auth(test_app: AsyncClient):
    response = await test_app.get("/api/v1/webhooks")
    assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Batch
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_submit_batch(test_app: AsyncClient, auth_headers: dict):
    """Submit a batch — background debate tasks are patched out."""
    with patch("api.routers.batch._run_debate", new=AsyncMock()):
        response = await test_app.post(
            "/api/v1/batch",
            json={
                "claims": [
                    "First claim: the sky is blue and it is a well known fact.",
                    "Second claim: water boils at 100 Celsius at sea level.",
                ],
                "language": "en",
                "llm_provider": "anthropic",
            },
            headers=auth_headers,
        )
    assert response.status_code == 202
    data = response.json()
    assert "batch_id" in data
    assert "analysis_ids" in data
    assert len(data["analysis_ids"]) == 2
    assert data["total"] == 2


@pytest.mark.integration
async def test_list_batches(test_app: AsyncClient, auth_headers: dict):
    with patch("api.routers.batch._run_debate", new=AsyncMock()):
        await test_app.post(
            "/api/v1/batch",
            json={
                "claims": ["List batch claim: the moon orbits the Earth once a month."],
                "language": "en",
            },
            headers=auth_headers,
        )
    response = await test_app.get("/api/v1/batch", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.integration
async def test_batch_requires_auth(test_app: AsyncClient):
    response = await test_app.get("/api/v1/batch")
    assert response.status_code in (401, 403)


@pytest.mark.integration
async def test_batch_empty_claims_rejected(test_app: AsyncClient, auth_headers: dict):
    response = await test_app.post(
        "/api/v1/batch",
        json={"claims": []},
        headers=auth_headers,
    )
    assert response.status_code == 422
