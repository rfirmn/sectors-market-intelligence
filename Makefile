.PHONY: install test smoke-test lint format dev-api clean smoke-test-engine

install:
	uv sync

test:
	uv run pytest -v

smoke-test:
	uv run python scripts/smoke_test.py

smoke-test-llm:
	uv run python scripts/smoke_test_llm.py

smoke-test-engine:
	uv run python scripts/smoke_test_engine.py

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
