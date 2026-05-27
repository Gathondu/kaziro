# backend — AGENTS.md

> Scope: everything under `backend/`. For LangGraph agent files
> specifically, the deeper [`agents/AGENTS.md`](agents/AGENTS.md) wins.
> Inherits from the [root AGENTS.md](../AGENTS.md).

## What lives here

```
backend/
├── AGENTS.md                  ← you are here
├── pyproject.toml             ← deps + tool config (ruff, mypy, pytest)
├── uv.lock
├── alembic.ini
├── main.py                    ← FastAPI entry (app factory)
├── tasks/celery_app.py        ← Celery app factory + Beat schedule
├── config.py                  ← Pydantic Settings — env-driven config
├── api/                       ← FastAPI routers (thin controllers)
│   ├── deps.py                ← shared deps (auth, db session, current_user)
│   ├── middleware/            ← request-id, rate-limit, error-envelope wiring
│   ├── schemas/               ← Pydantic request/response models per resource
│   └── routes/                ← ``/api/v1/*`` routers (jobs, applications, admin, …)
├── services/                  ← business logic (stateless, async)
├── db/
│   ├── base.py                ← SQLAlchemy declarative Base
│   ├── session.py             ← async session factory
│   ├── models/                ← ORM models (one per table)
│   └── repositories/          ← all queries — never raw SQL elsewhere
├── agents/                    ← LangGraph agents (own AGENTS.md)
├── tasks/                     ← Celery task definitions
├── schemas/                   ← Pydantic request/response models
├── utils/                     ← cross-cutting helpers (jwt, time, ids)
├── alembic/                   ← migrations
└── tests/                     ← mirrors source tree
```

## Stack reminders

- **Python 3.12+**, with `from __future__ import annotations` at the top
  of every file.
- **FastAPI** for HTTP, **uvicorn** in dev, **gunicorn + uvicorn workers**
  in production.
- **SQLAlchemy 2.0 async** + **asyncpg**. Never mix sync and async DB
  calls.
- **Pydantic v2** for all schemas and settings.
- **Celery + Redis** for async work (cron-driven pipeline runs, retries).
- **structlog** for logs. **prometheus-client** for metrics. **OpenTelemetry**
  for traces.

Full deps: [`docs/reference/dependencies.md`](../docs/reference/dependencies.md).

## Layering — non-negotiable

```
HTTP route  →  service  →  repository  →  DB
              (or)  →  Celery task     →  agent  →  LLM / external API
```

- **Routes** validate input (Pydantic), call a service, return a
  response. No business logic. No DB queries. Never longer than ~30 lines.
- **Services** orchestrate one use case. Stateless, async, return
  Pydantic models, raise typed exceptions.
- **Repositories** own all DB access. Every method takes a session and a
  scoping ID (usually `user_id`). Never accept raw SQL strings.
- **Agents** are called only by the **pipeline orchestrator** (or
  exceptionally by a service that handles a single agent flow). Agents
  never import from `api/`.
- **Tasks** call services. They are thin wrappers around an
  `asyncio.run(...)` call.

## Cardinal rules summary (links to enforced rules)

These mirror [`.cursor/rules/002-backend.mdc`](../.cursor/rules/002-backend.mdc).
Read the rule itself for full detail.

- Type-annotate every function signature. No implicit `Any`.
- Pydantic v2 BaseModel for all schemas — never dataclasses.
- `structlog` only — never `print()` or stdlib `logging`.
- Every log line must carry `user_id`, `job_posting_id`, `agent_name`,
  or whichever IDs are relevant.
- Routes return structured errors:
  `{"error": {"code": "...", "message": "..."}}` — see
  [`docs/architecture/04-api-design.md`](../docs/architecture/04-api-design.md).
- Settings come from `backend/config.py`. Never hardcode secrets, URLs,
  or models.
- Functions ≤ 50 lines. Extract helpers aggressively.
- `ruff check` + `ruff format` clean. `mypy` clean. No `# type: ignore`.

## Database & migrations

- ORM: SQLAlchemy 2.0 async. Models in `backend/db/models/`.
- Sessions: always opened via the `get_session` dependency
  (`backend/api/deps.py`) or `async_session_factory()` in tasks. **Never
  share a session across requests/tasks.**
- Multi-tenancy: every query filters on `user_id`. RLS is the safety net
  — see [`docs/architecture/07-security.md`](../docs/architecture/07-security.md).
- Migrations: Alembic. Generate with `uv run alembic revision --autogenerate -m "<message>"`.
  Review the generated SQL before committing — autogen misses `ENUM`
  changes and `pgvector` index types.
- Detail: [`docs/architecture/03-data-model.md`](../docs/architecture/03-data-model.md)
  + [`.cursor/rules/004-database.mdc`](../.cursor/rules/004-database.mdc).

## Celery rules

- Tasks live in `backend/tasks/<domain>.py` and are imported by
  `backend/tasks/celery_app.py` (``celery -A backend.tasks.celery_app:celery_app``).
- Every task: `@app.task(bind=True, autoretry_for=(...,),
  retry_backoff=True, max_retries=N)`.
- Tasks are sync wrappers — async work runs via
  `backend.tasks.async_runner.run_sqlalchemy_async` (wraps `asyncio.run`,
  disposes the global async engine, then calls
  `backend.tasks.loop_bound_reset.reset_loop_bound_clients` so OpenRouter /
  LangChain singletons are not tied to a closed loop).
- Use distinct queues per stage so we can scale them independently:
  `parser`, `evaluator`, `research`, `document`, `default`.
- Beat schedule lives in `backend/tasks/celery_app.py` with explicit cron strings.
  Document every entry.
- On Windows, `create_celery_app` sets `worker_pool` to `solo` by default
  (prefork/billiard is unstable on NT). Override with `CELERY_WORKER_POOL` or
  `celery worker --pool=threads` if you need local concurrency.

## Observability

- Bind context per request / task at the entry point: e.g.,
  `log = logger.bind(user_id=..., request_id=...)`.
- Emit a metric for every external call (LLM, Firecrawl, RapidAPI) with
  outcome label.
- Emit a span (`tracer.start_as_current_span(...)`) for every service
  method that orchestrates >1 external call or DB roundtrip.
- Detail + catalog: [`docs/architecture/06-observability.md`](../docs/architecture/06-observability.md)
  + [`.cursor/rules/006-observability.mdc`](../.cursor/rules/006-observability.mdc).

## Testing

- Layout mirrors source: `backend/tests/<area>/test_<file>.py`.
- Run: `uv run pytest --cov=backend`.
- Async tests: `@pytest.mark.asyncio`.
- LLM and Firecrawl calls **always** mocked via VCR cassettes — no live
  external calls in CI.
- Required fixtures live in `backend/tests/conftest.py`: `db_session`,
  `client`, `auth_user`, `mock_llm`, `vcr_cassette`.
- Detail: [`docs/design/testing-strategy.md`](../docs/design/testing-strategy.md)
  + [`.cursor/rules/005-testing.mdc`](../.cursor/rules/005-testing.mdc).

## When you add…

- **A new endpoint** → see the checklist in
  [`docs/architecture/04-api-design.md`](../docs/architecture/04-api-design.md#adding-a-new-endpoint).
- **A new model / migration** →
  [`docs/architecture/03-data-model.md`](../docs/architecture/03-data-model.md).
- **A new env var** → add to `config.py`, `.env.example`, and
  [`docs/reference/env-vars.md`](../docs/reference/env-vars.md).
- **A new dependency** →
  [`docs/reference/dependencies.md`](../docs/reference/dependencies.md).
- **A new metric / alert** →
  [`docs/architecture/06-observability.md`](../docs/architecture/06-observability.md).
- **A new agent or agent node** → read
  [`agents/AGENTS.md`](agents/AGENTS.md).

## Anti-patterns we reject

- ❌ Business logic in routes.
- ❌ Raw SQL strings outside repositories.
- ❌ DB queries in agents (load via repository in a `load_data` node).
- ❌ Sync DB calls in async paths.
- ❌ Mixing requests-level and task-level sessions.
- ❌ Hardcoded model strings — always `settings.LLM_MODEL_*`,
  `settings.LLM_EMBEDDING_MODEL`, and `settings.LLM_EMBEDDING_DIM`.
- ❌ Logging sensitive content (CV bodies, email contents, API keys).
- ❌ `# type: ignore` to silence mypy. Fix the type properly.
