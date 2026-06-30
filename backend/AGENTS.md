# backend — AGENTS.md

> Scope: everything under `backend/`. Inherits from the root
> [`AGENTS.md`](../AGENTS.md).

## What lives here

```text
backend/
├── config/              # Django settings, URLs, ASGI/WSGI, Celery
├── apps/
│   ├── accounts/        # auth and UUID user model
│   ├── core/            # shared schemas, envelopes, health, Ninja API
│   ├── profiles/
│   ├── jobs/
│   ├── applications/
│   ├── documents/
│   ├── pipeline/        # Celery and LangGraph orchestration
│   └── notifications/
└── tests/
```

## Rules

- Use Django Ninja for HTTP APIs, mounted under `/api/v1`.
- Preserve the API envelope: `{ data, meta, error }`.
- Keep route functions thin: endpoint -> service -> repository/query layer.
- Use the custom UUID primary-key user model.
- Keep Celery queue names explicit and documented in `config/celery.py`.
- Use structured logging; no `print()` in committed code.
- Keep auth, profile, notification, and email behavior covered by tests.

## Commands

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run python manage.py check
uv run python manage.py migrate
uv run python manage.py test
uv run python manage.py runserver 0.0.0.0:8000
```
