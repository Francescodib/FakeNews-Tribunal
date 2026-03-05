"""
Startup checks that run inside the FastAPI lifespan.

These checks are intentionally *non-fatal* (they log warnings rather than
raising) so that a rolling deploy or a temporary DB blip does not prevent
the process from starting.  The only exception is a hard DB-unreachable
situation in production, which is surfaced as a WARNING with explicit
guidance, but still does not abort the process.
"""

from __future__ import annotations

import re

from alembic.config import Config as AlembicConfig
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text

from core.config import Settings
from core.logging import get_logger

log = get_logger(__name__)

# Alembic config file path — resolved relative to the project root at import
# time so that the check works regardless of cwd at runtime.
_ALEMBIC_INI = "alembic.ini"


async def _check_db_reachable(engine) -> bool:
    """Return True if a trivial SELECT 1 succeeds."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "startup.db_unreachable",
            error=str(exc),
            hint="Check that PostgreSQL is running and DATABASE_URL is correct.",
        )
        return False


def _check_migrations(engine_sync_url: str) -> None:
    """
    Compare the current DB revision against the Alembic head revision.

    Uses the *sync* URL variant because Alembic's MigrationContext works
    with synchronous connections.  We convert asyncpg → psycopg2 only for
    this inspection (no actual data is read).
    """
    try:
        # Convert async driver URL to a sync one for Alembic introspection.
        # asyncpg → psycopg2 (standard sync driver).
        sync_url = re.sub(
            r"^postgresql\+asyncpg://",
            "postgresql+psycopg2://",
            engine_sync_url,
        )

        alembic_cfg = AlembicConfig(_ALEMBIC_INI)
        script = ScriptDirectory.from_config(alembic_cfg)
        head_revisions: list[str] = [
            rev.revision for rev in script.get_revisions("heads")
        ]

        from sqlalchemy import create_engine as _sync_engine

        sync_engine = _sync_engine(sync_url, connect_args={}, pool_pre_ping=True)
        try:
            with sync_engine.connect() as conn:
                ctx = MigrationContext.configure(conn)
                current_revisions: set[str] = set(ctx.get_current_heads())
        finally:
            sync_engine.dispose()

        head_set = set(head_revisions)
        if current_revisions == head_set:
            log.info(
                "startup.migrations_ok",
                revision=", ".join(sorted(current_revisions)) or "(none)",
            )
        else:
            log.warning(
                "startup.migrations_behind",
                current=", ".join(sorted(current_revisions)) or "(none)",
                head=", ".join(sorted(head_set)),
                hint=(
                    "Run `PYTHONPATH=. alembic upgrade head` to apply pending migrations. "
                    "The server will continue but may malfunction if schema is outdated."
                ),
            )
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "startup.migrations_check_failed",
            error=str(exc),
            hint="Could not verify Alembic migration state. Continuing anyway.",
        )


def _log_config_summary(settings: Settings) -> None:
    """Log non-sensitive configuration values for operator visibility."""
    log.info(
        "startup.config",
        env=settings.ENV,
        default_provider=settings.DEFAULT_PROVIDER,
        cors_origins=settings.CORS_ORIGINS,
        access_token_expire_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        refresh_token_expire_days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
        max_debate_rounds=settings.MAX_DEBATE_ROUNDS,
        max_batch_size=settings.MAX_BATCH_SIZE,
        webhook_max_retries=settings.WEBHOOK_MAX_RETRIES,
        tavily_configured=bool(settings.TAVILY_API_KEY),
        anthropic_configured=bool(settings.ANTHROPIC_API_KEY),
        openai_configured=bool(settings.OPENAI_API_KEY),
        gemini_configured=bool(settings.GEMINI_API_KEY),
        # Never log DATABASE_URL (contains credentials), JWT_SECRET_KEY, or API key values.
    )


def _log_dev_warnings(settings: Settings) -> None:
    """Emit structured warnings for non-optimal dev-mode settings."""
    if settings.ACCESS_TOKEN_EXPIRE_MINUTES > 60:
        log.warning(
            "startup.long_token_ttl",
            access_token_expire_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            hint="Token TTL is set high (dev default). Set ACCESS_TOKEN_EXPIRE_MINUTES=30 in production.",
        )

    if "*" in settings.CORS_ORIGINS or "http://localhost:3000" in settings.CORS_ORIGINS:
        log.warning(
            "startup.insecure_cors",
            cors_origins=settings.CORS_ORIGINS,
            hint="CORS_ORIGINS includes localhost/wildcard. Tighten for production.",
        )

    if not settings.TAVILY_API_KEY:
        log.warning(
            "startup.no_tavily_key",
            hint="TAVILY_API_KEY is not set. Web search will be disabled.",
        )


async def run_startup_checks(settings: Settings, engine) -> None:
    """
    Entry point called from ``api/main.py`` lifespan.

    Parameters
    ----------
    settings:
        The application Settings singleton.
    engine:
        The SQLAlchemy async engine already created by ``db.session``.
    """
    _log_config_summary(settings)

    if settings.ENV == "development":
        _log_dev_warnings(settings)

    db_ok = await _check_db_reachable(engine)

    if db_ok:
        # Migration check requires a synchronous psycopg2 connection; skip if
        # psycopg2 is not installed (e.g. minimal dev environments using only asyncpg).
        try:
            import importlib.util as _ilu

            if _ilu.find_spec("psycopg2") is not None:
                # Run in a thread so we don't block the event loop.
                import asyncio

                await asyncio.to_thread(
                    _check_migrations, str(engine.url).replace("+asyncpg", "+psycopg2")
                )
            else:
                log.info(
                    "startup.migrations_check_skipped",
                    reason="psycopg2 not installed; cannot perform sync migration check.",
                )
        except Exception as exc:  # noqa: BLE001
            log.warning("startup.migrations_check_error", error=str(exc))
    else:
        log.warning(
            "startup.migrations_check_skipped",
            reason="DB unreachable; skipping migration check.",
        )
