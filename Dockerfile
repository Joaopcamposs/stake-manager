# syntax=docker/dockerfile:1

# --- Frontend build ---
FROM node:22-slim AS frontend

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
COPY app/templates/ ../app/templates/
RUN npm run build

# --- Python deps ---
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

WORKDIR /app

COPY pyproject.toml .
RUN uv sync --no-dev --no-install-project

COPY app/ app/
RUN uv sync --no-dev

# --- Runtime ---
FROM python:3.14-slim-bookworm

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY app/ app/
COPY static/ static/
COPY --from=frontend /static/dist static/dist/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/app"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
