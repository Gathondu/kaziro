# syntax=docker/dockerfile:1.7
# Multi-stage build for the FastAPI backend.
#
# Stage layout:
#   * ``base``    — Python + system deps shared by every later stage.
#   * ``builder`` — installs the locked dependencies into a virtualenv.
#   * ``runtime`` — slim image with the venv + source code and a non-root user.
#
# Build context is the repository root; the application source lives under
# ``backend/``. Run with::
#
#     docker build -f backend/Dockerfile -t kaziro/backend .

ARG PYTHON_VERSION=3.12

# --- base ---------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# WeasyPrint and a few of our wheels need these system libraries at runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libffi-dev \
        libssl-dev \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

# --- builder ------------------------------------------------------------
FROM base AS builder

# Install ``uv`` from its official image — keeps wheel builds reproducible.
COPY --from=ghcr.io/astral-sh/uv:0.5.6 /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy the lockfile first so dependency layers are cached across rebuilds.
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./

RUN uv sync --frozen --no-install-project --no-dev

# --- runtime ------------------------------------------------------------
FROM base AS runtime

ARG APP_USER=kaziro
ARG APP_UID=10001

RUN groupadd --system --gid ${APP_UID} ${APP_USER} \
    && useradd --system --uid ${APP_UID} --gid ${APP_USER} --create-home ${APP_USER}

WORKDIR /app

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONPATH=/app

COPY --from=builder /app/.venv /app/.venv
COPY backend ./backend

USER ${APP_USER}

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
    CMD curl --fail --silent http://localhost:8000/health || exit 1

ENTRYPOINT ["python", "backend/docker/entrypoint.py"]
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
