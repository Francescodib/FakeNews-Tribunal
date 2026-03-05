# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build tools needed by some wheels (e.g. cryptography)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only the package manifest first so Docker caches this layer
COPY pyproject.toml .

# Create a virtual-env inside the build stage so we can copy it cleanly
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install all runtime dependencies (no editable install — just deps)
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir \
        "fastapi>=0.135.1" \
        "uvicorn[standard]>=0.41.0" \
        "litellm>=1.81.11" \
        "tavily-python>=0.7.21" \
        "sqlalchemy[asyncio]>=2.0.0,<3.0" \
        "alembic>=1.18.4" \
        "asyncpg>=0.31.0" \
        "python-jose[cryptography]>=3.5.0" \
        "bcrypt>=4.0.0" \
        "pydantic-settings>=2.13.1" \
        "structlog>=25.5.0" \
        "typer>=0.24.1" \
        "httpx>=0.28.1" \
        "slowapi>=0.1.9" \
        "fpdf2>=2.8.7"


# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Copy the pre-built venv from the builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source (excludes whatever is in .dockerignore)
COPY --chown=appuser:appgroup . .

USER appuser

EXPOSE 8000

# PYTHONPATH lets Python find the top-level packages (api, core, db, …)
ENV PYTHONPATH="/app"

# uvicorn without --reload in production; workers can be tuned via UVICORN_WORKERS
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
