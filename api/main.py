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
from db.session import AsyncSessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    get_logger(__name__).info("api.start")
    if settings.ENV == "development":
        async with AsyncSessionLocal() as db:
            await seed_dev_users(db)
    yield
    get_logger(__name__).info("api.stop")


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
