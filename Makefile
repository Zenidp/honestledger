.PHONY: install install-frontend run run-frontend run-all smoke-test lint test clean

install:
	uv sync

install-frontend:
	cd frontend && npm install

run:
	uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000

run-dev:
	uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

run-frontend:
	cd frontend && npm run dev

run-all:
	uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
	cd frontend && npm run dev

smoke-test:
	uv run python scripts/smoke_test.py

demo:
	uv run python scripts/run_demo.py

lint:
	uv run ruff check backend/ scripts/
	uv run ruff format --check backend/ scripts/

test:
	uv run pytest tests/ -v

clean:
	rm -rf .venv __pycache__ **/__pycache__ **/*.pyc dist build *.egg-info
