# Stage 1: build frontend
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend + built frontend
FROM python:3.12-slim
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock LICENSE README.md ./
RUN uv sync --frozen --no-dev --no-editable

COPY backend/ ./backend/
COPY --from=frontend-build /frontend/dist ./frontend/dist

EXPOSE 8080

# Local dev: uvicorn backend.main:app (port 8000, Vite proxy handles /api)
# Cloud Run: uvicorn backend.main:_root (port 8080, single container)
CMD uv run uvicorn backend.main:_root --host 0.0.0.0 --port ${PORT:-8080}
