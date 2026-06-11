# backend-django — AGENTS.md

> Scope: everything under `backend-django/`. Inherits from the root
> [`AGENTS.md`](../AGENTS.md).

## What lives here

This is the parallel Django migration backend. It must not replace the
existing FastAPI backend until a later cutover milestone.

```
backend-django/
├── config/              # Django settings, ASGI/WSGI, URLs, Celery
├── apps/
│   ├── accounts/        # Django-owned auth and UUID user model
│   ├── core/            # shared schemas, envelopes, health, Ninja API
│   ├── profiles/
│   ├── jobs/
│   ├── applications/
│   ├── documents/
│   ├── pipeline/        # Celery/LangGraph migration target
│   └── notifications/
└── tests/
```

## Rules

- Use Django Ninja for HTTP APIs, mounted under `/api/v1`.
- Preserve the current API envelope: `{ data, meta, error }`.
- Keep route functions thin: endpoint -> service -> repository/query layer.
- Use a custom UUID primary-key user model from the first migration.
- Keep Celery queue names compatible with the existing backend.
- Use structured logging; no `print()` in committed code.
- Do not depend on Supabase Auth in new code.

## Commands

```bash
uv sync
uv run python manage.py check
uv run python manage.py test
uv run python manage.py runserver 0.0.0.0:8001
```
