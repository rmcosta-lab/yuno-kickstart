.PHONY: install dev-api dev-frontend generate-openapi generate-client generate \
	python-check frontend-check check postgres-up postgres-down

install:
	uv sync --all-packages
	pnpm --dir frontend install

dev-api:
	uv run --package yuno-api uvicorn app.main:app --reload --port 8000

dev-frontend:
	pnpm --dir frontend dev

generate-openapi:
	uv run python api/scripts/export_openapi.py

generate-client: generate-openapi
	pnpm --dir frontend api:generate

generate: generate-client

python-check:
	uv run ruff check .
	uv run pytest

frontend-check:
	pnpm --dir frontend lint
	pnpm --dir frontend typecheck
	pnpm --dir frontend build

check: python-check frontend-check

postgres-up:
	docker compose up -d postgres

postgres-down:
	docker compose down
