# Kaziro — root Makefile.
# One-stop convenience commands. Run ``make help`` for the full list.

SHELL := /usr/bin/env bash

# Override on the CLI: ``make migrate MSG="add jobs"``
MSG ?=

# Tool dispatchers — keep them centralised so we can swap them out later.
COMPOSE  := docker compose
UV       := uv
PNPM     := pnpm
ALEMBIC  := $(UV) run alembic

BACKEND_DIR  := backend
FRONTEND_DIR := frontend

.DEFAULT_GOAL := help

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

.PHONY: help
help: ## Show this help.
	@awk 'BEGIN {FS = ":.*?## "; printf "\nKaziro Make targets\n\n"} \
		/^[a-zA-Z0-9_.-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ---------------------------------------------------------------------------
# Local dev orchestration (docker-compose)
# ---------------------------------------------------------------------------

.PHONY: dev
dev: ## Boot the full stack (postgres, redis, backend, all workers, beat, frontend).
	$(COMPOSE) up --build

.PHONY: dev-detached
dev-detached: ## Boot the full stack in the background.
	$(COMPOSE) up --build -d

.PHONY: down
down: ## Stop the stack and wipe named volumes.
	$(COMPOSE) down -v

.PHONY: logs
logs: ## Tail logs for every service.
	$(COMPOSE) logs -f --tail=100

# ---------------------------------------------------------------------------
# Per-service dev loops (run on the host without docker)
# ---------------------------------------------------------------------------

.PHONY: dev-backend
dev-backend: ## Run the FastAPI app with autoreload on the host.
	cd $(BACKEND_DIR) && $(UV) run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: dev-frontend
dev-frontend: ## Run the Vite dev server on the host.
	cd $(FRONTEND_DIR) && $(PNPM) dev

.PHONY: dev-worker
dev-worker: ## Run a single Celery worker on the host listening to all queues.
	cd $(BACKEND_DIR) && $(UV) run celery -A backend.tasks.celery_app:celery_app worker --loglevel=info --concurrency=2 -Q default,parser,evaluator,research,document,maintenance

.PHONY: dev-worker-parser
dev-worker-parser: ## Run a host-side Celery worker dedicated to the parser queue.
	cd $(BACKEND_DIR) && $(UV) run celery -A backend.tasks.celery_app:celery_app worker --loglevel=info --concurrency=4 -Q parser -n worker-parser@%h

.PHONY: dev-worker-evaluator
dev-worker-evaluator: ## Run a host-side Celery worker dedicated to the evaluator queue.
	cd $(BACKEND_DIR) && $(UV) run celery -A backend.tasks.celery_app:celery_app worker --loglevel=info --concurrency=2 -Q evaluator -n worker-evaluator@%h

.PHONY: dev-worker-research-doc
dev-worker-research-doc: ## Run a host-side Celery worker for research + document queues.
	cd $(BACKEND_DIR) && $(UV) run celery -A backend.tasks.celery_app:celery_app worker --loglevel=info --concurrency=2 -Q research,document -n worker-research-doc@%h

.PHONY: dev-beat
dev-beat: ## Run the Celery Beat scheduler on the host.
	cd $(BACKEND_DIR) && $(UV) run celery -A backend.tasks.celery_app:celery_app beat --loglevel=info

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

.PHONY: test
test: test-backend test-frontend ## Run the full test suite (backend + frontend).

.PHONY: test-backend
test-backend: ## Run backend pytest with coverage.
	cd $(BACKEND_DIR) && $(UV) run pytest --cov=backend --cov-report=term-missing

.PHONY: test-frontend
test-frontend: ## Run frontend Vitest suite.
	cd $(FRONTEND_DIR) && $(PNPM) test

.PHONY: e2e
e2e: ## Run Playwright end-to-end tests (requires the backend up).
	cd $(FRONTEND_DIR) && $(PNPM) e2e

# ---------------------------------------------------------------------------
# Lint / format / typecheck
# ---------------------------------------------------------------------------

.PHONY: lint
lint: lint-backend lint-frontend ## Run all linters.

.PHONY: lint-backend
lint-backend: ## Backend: ruff + mypy.
	cd $(BACKEND_DIR) && $(UV) run ruff check .
	cd $(BACKEND_DIR) && $(UV) run ruff format --check .
	cd $(BACKEND_DIR) && $(UV) run mypy .

.PHONY: lint-frontend
lint-frontend: ## Frontend: prettier --check + eslint + svelte-check.
	cd $(FRONTEND_DIR) && $(PNPM) lint
	cd $(FRONTEND_DIR) && $(PNPM) check

.PHONY: format
format: format-backend format-frontend ## Auto-format every workspace.

.PHONY: format-backend
format-backend: ## Backend: ruff format + ruff check --fix.
	cd $(BACKEND_DIR) && $(UV) run ruff format .
	cd $(BACKEND_DIR) && $(UV) run ruff check --fix .

.PHONY: format-frontend
format-frontend: ## Frontend: prettier --write.
	cd $(FRONTEND_DIR) && $(PNPM) format

# ---------------------------------------------------------------------------
# Database / migrations
# ---------------------------------------------------------------------------

.PHONY: migrate
migrate: ## Apply Alembic migrations to ``head``.
	cd $(BACKEND_DIR) && $(ALEMBIC) upgrade head

.PHONY: migration
migration: ## Create a new Alembic revision: ``make migration MSG="add jobs table"``.
	@if [ -z "$(MSG)" ]; then \
		echo "Usage: make migration MSG=\"description\""; exit 2; \
	fi
	cd $(BACKEND_DIR) && $(ALEMBIC) revision --autogenerate -m "$(MSG)"

.PHONY: seed
seed: ## Load development seed data (Phase 1+).
	cd $(BACKEND_DIR) && $(UV) run python -m backend.scripts.seed

.PHONY: psql
psql: ## Open a psql shell against the dev Postgres container.
	$(COMPOSE) exec postgres psql -U kaziro -d kaziro

.PHONY: redis-cli
redis-cli: ## Open a redis-cli shell against the dev Redis container.
	$(COMPOSE) exec redis redis-cli

# ---------------------------------------------------------------------------
# Housekeeping
# ---------------------------------------------------------------------------

.PHONY: clean
clean: ## Remove caches, build artefacts, and coverage reports.
	rm -rf $(BACKEND_DIR)/.pytest_cache $(BACKEND_DIR)/.ruff_cache $(BACKEND_DIR)/.mypy_cache
	rm -rf $(BACKEND_DIR)/htmlcov $(BACKEND_DIR)/.coverage $(BACKEND_DIR)/coverage.xml
	find $(BACKEND_DIR) -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf $(FRONTEND_DIR)/.svelte-kit $(FRONTEND_DIR)/.vercel $(FRONTEND_DIR)/build $(FRONTEND_DIR)/dist
	rm -rf $(FRONTEND_DIR)/coverage $(FRONTEND_DIR)/playwright-report $(FRONTEND_DIR)/test-results

.PHONY: install
install: ## Install backend (uv) and frontend (pnpm) dependencies.
	cd $(BACKEND_DIR) && $(UV) sync
	cd $(FRONTEND_DIR) && $(PNPM) install
