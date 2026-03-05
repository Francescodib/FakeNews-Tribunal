"""
Root conftest.py — shared fixtures for all tests.

Sets up:
- Environment variables (JWT_SECRET_KEY, DATABASE_URL, ENV=test) before any
  project module is imported.
- SQLite in-memory async database with schema creation.
- FastAPI test client (httpx.AsyncClient) with DB dependency override.
- auth_headers / admin_headers fixtures.
- SQLite dialect patches for PostgreSQL-specific column types (JSONB, UUID).
"""

from __future__ import annotations

import os
import uuid

# ---------------------------------------------------------------------------
# Set required environment variables BEFORE any project module is imported.
# This prevents pydantic-settings from reading the real .env file and
# ensures the JWT validator passes with a known test secret.
# ---------------------------------------------------------------------------
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-that-is-long-enough-32ch")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENV", "test")

# ---------------------------------------------------------------------------
# Patch the SQLite dialect so it can render PostgreSQL-specific column types
# (JSONB and dialects.postgresql.UUID) that are used in db/models.py.
# This must happen BEFORE SQLAlchemy inspects the models.
# ---------------------------------------------------------------------------
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler  # noqa: E402


def _visit_JSONB(self, type_, **kw):  # noqa: N802
    """Render JSONB as plain TEXT for SQLite."""
    return "TEXT"


def _visit_UUID_pg(self, type_, **kw):  # noqa: N802
    """Render postgresql.UUID as TEXT (UUIDs stored as strings) for SQLite."""
    return "TEXT"


if not hasattr(SQLiteTypeCompiler, "visit_JSONB"):
    SQLiteTypeCompiler.visit_JSONB = _visit_JSONB  # type: ignore[attr-defined]

if not hasattr(SQLiteTypeCompiler, "visit_UUID"):
    SQLiteTypeCompiler.visit_UUID = _visit_UUID_pg  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Now it is safe to import project modules.
# ---------------------------------------------------------------------------
import secrets  # noqa: E402
from collections.abc import AsyncGenerator  # noqa: E402
from unittest.mock import AsyncMock, patch  # noqa: E402

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool  # noqa: E402

from api.main import app  # noqa: E402

# ---------------------------------------------------------------------------
# pytest-asyncio 0.21+ with asyncio_mode="auto" in pyproject.toml handles
# all async fixtures automatically. No need to declare pytest_plugins here.
# ---------------------------------------------------------------------------
from api.middleware.auth_middleware import (  # noqa: E402
    create_access_token,
    hash_password,
    hash_token,
    refresh_token_expiry,
)
from db.models import Base  # noqa: E402
from db.repository import create_refresh_token, create_user  # noqa: E402
from db.session import get_db  # noqa: E402

# ---------------------------------------------------------------------------
# Async SQLite engine (in-memory, shared across the test session).
#
# StaticPool ensures all connections share the same in-memory database even
# when multiple sessions are opened within the same test.
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

_test_engine = create_async_engine(
    TEST_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

_TestSessionLocal = async_sessionmaker(
    bind=_test_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


# ---------------------------------------------------------------------------
# Session-scoped: create all tables once for the whole test session.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
async def create_tables():
    """Create all ORM tables in the in-memory SQLite DB once per session."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
# Function-scoped DB session.
# ---------------------------------------------------------------------------

@pytest.fixture()
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an AsyncSession backed by the in-memory SQLite DB.
    Each test gets a fresh session; changes are visible within the test but
    the session is closed (and committed changes persist in the shared memory DB).
    For isolation between tests we rely on unique email addresses and UUIDs.
    """
    async with _TestSessionLocal() as session:
        yield session


# ---------------------------------------------------------------------------
# FastAPI test app with DB override.
# ---------------------------------------------------------------------------

async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _TestSessionLocal() as session:
        yield session


@pytest.fixture()
def anyio_backend():
    return "asyncio"


@pytest.fixture()
async def test_app(create_tables) -> AsyncGenerator[AsyncClient, None]:
    """
    AsyncClient wired to the FastAPI app with:
    - get_db dependency overridden to use the test SQLite DB.
    - run_startup_checks patched to a no-op (avoids alembic check and delays).
    - ENV is 'test' so dev seeding does not run.
    """
    app.dependency_overrides[get_db] = _override_get_db

    with patch("api.main.run_startup_checks", new=AsyncMock()):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Auth helper fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
async def auth_headers(test_db: AsyncSession) -> dict[str, str]:
    """
    Create a regular (non-admin) test user and return an Authorization header.
    A unique email is used per call to avoid conflicts.
    """
    email = f"testuser-{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPassword1!"
    user = await create_user(test_db, email, hash_password(password))
    access_token = create_access_token(user.id)
    refresh_value = secrets.token_urlsafe(64)
    await create_refresh_token(
        test_db, user.id, hash_token(refresh_value), refresh_token_expiry()
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture()
async def admin_headers(test_db: AsyncSession) -> dict[str, str]:
    """
    Create an admin test user and return an Authorization header.
    """
    from db.repository import update_user

    email = f"admin-{uuid.uuid4().hex[:8]}@example.com"
    password = "AdminPassword1!"
    user = await create_user(test_db, email, hash_password(password))
    await update_user(test_db, user, is_admin=True)
    access_token = create_access_token(user.id)
    refresh_value = secrets.token_urlsafe(64)
    await create_refresh_token(
        test_db, user.id, hash_token(refresh_value), refresh_token_expiry()
    )
    return {"Authorization": f"Bearer {access_token}"}
