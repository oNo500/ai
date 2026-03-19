.PHONY: install install-js install-py
.PHONY: dev dev-js dev-agent
.PHONY: build test lint format typecheck
.PHONY: setup-env

# ── Install ────────────────────────────────────────────────────────────────────

install: install-js install-py

install-js:
	pnpm install

install-py:
	uv sync

# ── Dev ────────────────────────────────────────────────────────────────────────

dev: dev-js dev-agent

dev-js:
	pnpm dev

dev-agent:
	uv run uvicorn agentic.src.main:app --reload --app-dir .

# ── Build ──────────────────────────────────────────────────────────────────────

build:
	pnpm build

# ── Test ───────────────────────────────────────────────────────────────────────

test:
	pnpm turbo run test
	uv run pytest

# ── Lint & Format ──────────────────────────────────────────────────────────────

lint:
	pnpm lint
	uv run ruff check agentic/

format:
	uv run ruff format agentic/

typecheck:
	pnpm typecheck

# ── Docker ─────────────────────────────────────────────────────────────────────

docker-up:
	docker compose -f docker/docker-compose.yml up -d

docker-down:
	docker compose -f docker/docker-compose.yml down

# ── Setup ──────────────────────────────────────────────────────────────────────

setup-env:
	pnpm setup:env
