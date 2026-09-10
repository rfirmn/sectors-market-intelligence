.PHONY: install test smoke-test lint format dev-api clean

install:
	uv sync

test:
	uv run pytest -v

smoke-test:
	uv run python scripts/smoke_test.py

lint:
	uv run ruff check .
	npx pyright

format:
	uv run ruff check --fix .
	uv run ruff format .

dev-api:
	uv run uvicorn src.api.main:app --reload --port 8000

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache
