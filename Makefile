.PHONY: dev test lint format db-up db-down frontend-build seed

dev: frontend-build
	uv run fastapi dev app/main.py

test:
	uv run python -m pytest -x --tb=short -q

lint:
	uv run python -m ruff check app/ tests/
	uv run python -m ruff format --check app/ tests/

format:
	uv run python -m ruff format app/ tests/
	uv run python -m ruff check --fix app/ tests/

db-up:
	docker compose up -d

db-down:
	docker compose down

seed:
	uv run python -c "import asyncio; from app.seed import run_seed; asyncio.run(run_seed())"

frontend-build:
	cd frontend && npm run build
