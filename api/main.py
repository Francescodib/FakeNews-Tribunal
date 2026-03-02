from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import analysis, auth
from core.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    get_logger(__name__).info("api.start")
    yield
    get_logger(__name__).info("api.stop")


app = FastAPI(
    title="FakeNews Tribunal",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")


@app.get("/api/v1/health", tags=["health"])
async def health():
    return {"status": "ok"}
