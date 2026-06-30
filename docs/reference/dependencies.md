# Dependencies Reference

**Status**: Living
**Last updated**: 2026-06-29

## Backend Runtime

| Package | Purpose |
| --- | --- |
| `django` | Web framework and ORM. |
| `django-ninja` | Typed API layer and OpenAPI generation. |
| `django-cors-headers` | CORS handling. |
| `dj-database-url` | Database URL parsing. |
| `psycopg[binary]` | PostgreSQL driver. |
| `pydantic[email]` | Schema validation. |
| `pydantic-settings` | Typed settings. |
| `pyjwt[crypto]` | JWT handling. |
| `celery[redis]` | Background workers. |
| `redis` | Broker/cache client. |
| `langgraph` | Agent workflow engine. |
| `resend[async]` | Transactional email. |
| `structlog` | Structured logging. |
| `uvicorn` | ASGI server for local/dev runtime. |
| `whitenoise` | Static asset serving for backend assets. |

## Backend Dev/Test

| Package | Purpose |
| --- | --- |
| `ruff` | Linting and formatting. |
| `mypy` | Static type checking. |
| `django-stubs` | Django typing support. |
| `pytest` | Test runner support. |
| `pytest-django` | Django test integration. |

## Frontend Runtime

| Package | Purpose |
| --- | --- |
| `next` | React framework and App Router. |
| `react` | UI runtime. |
| `react-dom` | DOM renderer. |
| `@tanstack/react-query` | Server-state fetching and caching. |
| `zustand` | Small client-side stores. |
| `tailwindcss` | Utility CSS. |
| `daisyui` | Tailwind component classes. |
| `zod` | Client-side validation. |
| `lucide-react` | Icons. |
| `@microsoft/fetch-event-source` | Streaming/event-source helper. |

## Frontend Dev/Test

| Package | Purpose |
| --- | --- |
| `typescript` | Static type checking. |
| `eslint` | Linting. |
| `eslint-config-next` | Next.js lint rules. |
| `@playwright/test` | End-to-end tests. |
| `playwright` | Browser automation runtime. |

## Policy

- Backend dependencies are declared in `backend/pyproject.toml` and locked by
  `backend/uv.lock`.
- Frontend dependencies are declared in `frontend/package.json` and locked by
  `frontend/pnpm-lock.yaml`.
- New runtime dependencies require a brief rationale in the PR and an update
  to this file.
