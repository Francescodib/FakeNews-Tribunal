from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.rate_limit import limiter
from api.routers import admin, analysis, auth, batch, providers, webhooks
from api.seed import seed_dev_users
from core.config import settings
from core.logging import configure_logging, get_logger
from core.startup_checks import run_startup_checks
from db.session import AsyncSessionLocal, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    log = get_logger(__name__)
    log.info("api.start")

    # Run startup checks: config summary, dev warnings, DB reachability,
    # and Alembic migration state.  Never raises — only logs warnings.
    await run_startup_checks(settings, engine)

    if settings.ENV == "development":
        async with AsyncSessionLocal() as db:
            await seed_dev_users(db)
    yield
    log.info("api.stop")


app = FastAPI(
    title="FakeNews Tribunal",
    version="0.4.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(providers.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(batch.router, prefix="/api/v1")


@app.get("/api/v1/health", tags=["health"])
async def health():
    return {"status": "ok"}


@app.get("/api/v1/config", tags=["config"])
async def config():
    return {"default_provider": settings.DEFAULT_PROVIDER}
