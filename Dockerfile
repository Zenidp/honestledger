FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first (layer cache)
COPY pyproject.toml uv.lock ./

# Install dependencies (no dev deps, no venv — install to system)
RUN uv sync --frozen --no-dev --no-editable

# Copy application code
COPY backend/ ./backend/

# Expose port
EXPOSE 8080

# Cloud Run expects PORT env var
CMD uv run uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}
