# syntax=docker/dockerfile:1

# ---- Stage 1: build the frontend ----
FROM node:22-bookworm-slim AS frontend
WORKDIR /frontend

# Install deps first for layer caching
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Build the SPA -> /frontend/dist
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: python API that also serves the built SPA ----
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random

# Build dependencies for asyncmy (Cython extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python deps (cached on lockfile changes)
COPY pyproject.toml uv.lock ./
RUN uv venv /venv \
 && UV_PROJECT_ENVIRONMENT=/venv uv sync --frozen --no-dev

# Application code
COPY src ./src
COPY scripts ./scripts
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

# Built frontend from stage 1 -> served by FastAPI as static files
COPY --from=frontend /frontend/dist ./frontend_dist

ENV PATH="/venv/bin:$PATH"

EXPOSE 8000

# Apply migrations, then serve API + SPA on one port
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn src.main:app --host 0.0.0.0 --port 8000"]
