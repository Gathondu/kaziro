# Kaziro root Makefile.

SHELL := /usr/bin/env bash

MSG ?=

COMPOSE := docker compose
UV := uv
PNPM := pnpm

BACKEND_DIR := backend
FRONTEND_DIR := frontend

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help.
	@awk 'BEGIN {FS = ":.*?## "; printf "\nKaziro Make targets\n\n"} /^[a-zA-Z0-9_.-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: dev
dev: ## Boot the full local stack.
	$(COMPOSE) up --build

.PHONY: dev-detached
dev-detached: ## Boot the full local stack in the background.
	$(COMPOSE) up --build -d

.PHONY: down
down: ## Stop the stack and wipe named volumes.
	$(COMPOSE) down -v

.PHONY: logs
logs: ## Tail logs for every service.
	$(COMPOSE) logs -f --tail=100

.PHONY: dev-backend
dev-backend: ## Run the Django API on the host.
	cd $(BACKEND_DIR) && $(UV) run uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --reload --timeout-graceful-shutdown 2

.PHONY: dev-frontend
dev-frontend: ## Run the Next.js dev server on the host.
	cd $(FRONTEND_DIR) && $(PNPM) dev

.PHONY: dev-worker
dev-worker: ## Run a Celery worker listening to all queues.
	cd $(BACKEND_DIR) && $(UV) run celery -A config.celery:app worker --loglevel=info --concurrency=2 -Q default,parser,evaluator,research,document,maintenance,notification

.PHONY: dev-worker-parser
dev-worker-parser: ## Run a Celery worker dedicated to the parser queue.
	cd $(BACKEND_DIR) && $(UV) run celery -A config.celery:app worker --loglevel=info --concurrency=4 -Q parser -n worker-parser@%h

.PHONY: dev-worker-evaluator
dev-worker-evaluator: ## Run a Celery worker dedicated to the evaluator queue.
	cd $(BACKEND_DIR) && $(UV) run celery -A config.celery:app worker --loglevel=info --concurrency=2 -Q evaluator -n worker-evaluator@%h

.PHONY: dev-worker-research-doc
dev-worker-research-doc: ## Run a Celery worker for research and document queues.
	cd $(BACKEND_DIR) && $(UV) run celery -A config.celery:app worker --loglevel=info --concurrency=2 -Q research,document -n worker-research-doc@%h

.PHONY: dev-beat
dev-beat: ## Run the Celery Beat scheduler on the host.
	cd $(BACKEND_DIR) && $(UV) run celery -A config.celery:app beat --loglevel=info --schedule=/tmp/celerybeat-schedule

.PHONY: test
test: test-backend test-frontend ## Run backend and frontend checks.

.PHONY: test-backend
test-backend: ## Run Django tests.
	cd $(BACKEND_DIR) && $(UV) run python manage.py test

.PHONY: test-frontend
test-frontend: ## Run frontend type checks.
	cd $(FRONTEND_DIR) && $(PNPM) typecheck

.PHONY: e2e
e2e: ## Run Playwright end-to-end tests.
	cd $(FRONTEND_DIR) && $(PNPM) test:e2e

.PHONY: lint
lint: lint-backend lint-frontend ## Run backend and frontend linters.

.PHONY: lint-backend
lint-backend: ## Backend: ruff lint and format check.
	cd $(BACKEND_DIR) && $(UV) run ruff check .
	cd $(BACKEND_DIR) && $(UV) run ruff format --check .

.PHONY: lint-frontend
lint-frontend: ## Frontend: ESLint and TypeScript.
	cd $(FRONTEND_DIR) && $(PNPM) lint
	cd $(FRONTEND_DIR) && $(PNPM) typecheck

.PHONY: build-frontend
build-frontend: ## Frontend production build.
	cd $(FRONTEND_DIR) && $(PNPM) build

.PHONY: format
format: format-backend format-frontend ## Auto-format every workspace.

.PHONY: format-backend
format-backend: ## Backend: ruff format and fix.
	cd $(BACKEND_DIR) && $(UV) run ruff format .
	cd $(BACKEND_DIR) && $(UV) run ruff check --fix .

.PHONY: format-frontend
format-frontend: ## Frontend: run the project formatter if configured.
	cd $(FRONTEND_DIR) && $(PNPM) format

.PHONY: migrate
migrate: ## Apply Django database migrations.
	cd $(BACKEND_DIR) && $(UV) run python manage.py migrate

.PHONY: migration
migration: ## Create Django migrations. Optional: make migration MSG="description".
	cd $(BACKEND_DIR) && $(UV) run python manage.py makemigrations

.PHONY: psql
psql: ## Open a psql shell against the dev Postgres container.
	$(COMPOSE) exec postgres psql -U kaziro -d kaziro

.PHONY: redis-cli
redis-cli: ## Open a redis-cli shell against the dev Redis container.
	$(COMPOSE) exec redis redis-cli

.PHONY: clean
clean: ## Remove caches, build artifacts, and coverage reports.
	rm -rf $(BACKEND_DIR)/.pytest_cache $(BACKEND_DIR)/.ruff_cache $(BACKEND_DIR)/.mypy_cache
	rm -rf $(BACKEND_DIR)/htmlcov $(BACKEND_DIR)/.coverage $(BACKEND_DIR)/coverage.xml $(BACKEND_DIR)/db.sqlite3
	find $(BACKEND_DIR) -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf $(FRONTEND_DIR)/.next $(FRONTEND_DIR)/.vercel $(FRONTEND_DIR)/coverage
	rm -rf $(FRONTEND_DIR)/playwright-report $(FRONTEND_DIR)/test-results $(FRONTEND_DIR)/tsconfig.tsbuildinfo

.PHONY: install
install: ## Install backend and frontend dependencies.
	cd $(BACKEND_DIR) && $(UV) sync
	cd $(FRONTEND_DIR) && $(PNPM) install
