# syntax=docker/dockerfile:1.7

# ---- builder ----
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Install dependencies first for better layer caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy source and install the project itself
COPY src ./src
RUN uv sync --frozen --no-dev

# ---- runtime ----
FROM python:3.12-slim AS runtime

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NEWS_AGGREGATOR_HOME=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash app

WORKDIR /app

# Copy the prebuilt virtualenv and project from builder
COPY --from=builder /app /app
COPY config /app/config
COPY templates /app/templates
COPY example.env /app/example.env

RUN mkdir -p /app/data /app/logs && chown -R app:app /app
USER app

# Default: run the scheduler. Override with `--once` for one-shot.
CMD ["news-aggregator"]
