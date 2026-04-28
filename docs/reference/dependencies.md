# Dependencies Reference

**Status**: Living
**Last updated**: 2026-04-27
**Source**: Kaziro Design Document §13 + `.cursor/rules/{002-backend,003-frontend}.mdc`

The canonical, opinionated list of runtime + dev dependencies for both
workspaces. Add a new dep? Add a row here, with a one-line rationale,
in the same PR.

Versioning policy:

- **Backend (Python)**: pin to compatible-release ranges in
  `backend/pyproject.toml` (`>=x.y,<x+1.0`). Reproducible installs via
  `uv.lock`.
- **Frontend (Node)**: pin exact versions in `frontend/package.json`;
  reproducible installs via `pnpm-lock.yaml`.
- We upgrade dependencies on a fortnightly cadence (Renovate / Dependabot
  PRs), not ad-hoc.

## Backend — runtime

| Package              | Version | Purpose                                                    |
| -------------------- | ------- | ---------------------------------------------------------- |
| `python`             | `>=3.12,<3.13` | Runtime — typed unions, performance, asyncio improvements. |
| `fastapi`            | `>=0.115,<0.116` | Web framework + OpenAPI generation.                  |
| `uvicorn[standard]`  | `>=0.32`  | ASGI server (production: gunicorn + uvicorn workers).     |
| `pydantic`           | `>=2.9,<3.0` | Schemas, validation, settings.                         |
| `pydantic-settings`  | `>=2.5`   | `BaseSettings` for env-driven config.                     |
| `sqlalchemy`         | `>=2.0,<2.1` | ORM with async session support.                        |
| `asyncpg`            | `>=0.30`  | Postgres async driver.                                    |
| `psycopg[binary]`    | `>=3.2`   | Postgres sync driver for Alembic (``postgresql+psycopg``; bare ``postgresql://`` in ``DATABASE_URL_SYNC`` is rewritten in ``alembic/env.py``). |
| `alembic`            | `>=1.13`  | DB migrations.                                            |
| `pgvector`           | `>=0.3`   | Python bindings for the pgvector type.                    |
| `supabase`           | `>=2.8`   | Supabase Python SDK (auth, storage).                      |
| `python-jose[cryptography]` | `>=3.3` | JWT verification.                                  |
| `langgraph`          | `>=0.2`   | Agentic graph framework.                                  |
| `langchain-openrouter` | `>=0.1` | LangChain [OpenRouter](https://docs.langchain.com/oss/python/integrations/chat/openrouter) chat models (`ChatOpenRouter`). |
| `langchain-openai`   | `>=0.2`   | `OpenAIEmbeddings` pointed at OpenRouter's OpenAI-compatible `/v1/embeddings`. |
| `openai`             | `>=1.51`  | Transitive / HTTP client used by `langchain-openai` embeddings. |
| `openrouter`         | (via `langchain-openrouter`) | Official OpenRouter Python SDK used by `ChatOpenRouter`. |
| `tiktoken`           | `>=0.8`   | Token counting for budget tracking.                       |
| `celery[redis]`      | `>=5.4`   | Task queue.                                               |
| `redis`              | `>=5.0`   | Redis client (cache + Pub/Sub).                           |
| `httpx`              | `>=0.27`  | Async HTTP client (Firecrawl, RapidAPI).                  |
| `tenacity`           | `>=9.0`   | Retry decorators for external calls.                      |
| `structlog`          | `>=24.4`  | Structured logging.                                       |
| `prometheus-client`  | `>=0.21`  | Metrics + `/metrics` endpoint.                            |
| `opentelemetry-distro` | `>=0.48` | OTel auto-instrumentation bundle.                       |
| `opentelemetry-instrumentation-fastapi` | `>=0.48` | FastAPI tracing.                       |
| `opentelemetry-instrumentation-celery` | `>=0.48`  | Celery tracing.                       |
| `opentelemetry-instrumentation-sqlalchemy` | `>=0.48` | SQLAlchemy tracing.                |
| `sentry-sdk[fastapi,celery]` | `>=2.17` | Error tracking.                                  |
| `weasyprint`         | `>=63.0`  | HTML → PDF rendering for generated CVs / cover letters.   |
| `jinja2`             | `>=3.1`   | Templating for PDF + emails.                              |
| `python-multipart`   | `>=0.0.12` | Multipart form-data parsing (file uploads).              |
| `bleach`             | `>=6.1`   | HTML sanitisation for user-supplied rich text.            |
| `pypdf`              | `>=5.0`   | Read user-uploaded CV PDFs.                               |

## Backend — dev / test

| Package                 | Version | Purpose                                                |
| ----------------------- | ------- | ------------------------------------------------------ |
| `pytest`                | `>=8.3` | Test runner.                                           |
| `pytest-asyncio`        | `>=0.24` | Async test support.                                   |
| `pytest-cov`            | `>=5.0` | Coverage reporting.                                    |
| `pytest-mock`           | `>=3.14` | Mock fixtures.                                        |
| `respx`                 | `>=0.21` | Stub ``httpx`` calls (GoTrue proxy tests).             |
| `vcrpy`                 | `>=6.0` | Record/replay HTTP cassettes (LLM, Firecrawl).         |
| `factory-boy`           | `>=3.3` | Test factories for models.                             |
| `freezegun`             | `>=1.5` | Freeze time in tests.                                  |
| `httpx`                 | `>=0.27` | Async HTTP client (also used by `TestClient`).        |
| `ruff`                  | `>=0.7` | Linter + formatter.                                    |
| `mypy`                  | `>=1.13` | Static type-checker.                                  |
| `pre-commit`            | `>=4.0` | Git hooks runner.                                      |
| `locust`                | `>=2.32` | Load testing.                                         |

## Frontend — runtime

| Package                 | Version | Purpose                                                |
| ----------------------- | ------- | ------------------------------------------------------ |
| `svelte`                | `^5.0`  | UI framework — runes-based reactivity.                 |
| `@sveltejs/kit`         | `^2.0`  | Routing, SSR, build.                                   |
| `@sveltejs/adapter-vercel` | `^5.0` | Vercel deploy adapter.                              |
| `vite`                  | `^5.4`  | Bundler.                                               |
| `typescript`            | `^5.6`  | Static types.                                          |
| `tailwindcss`           | `^3.4`  | Utility-first CSS.                                     |
| `daisyui`               | `^4.12` | Tailwind component library.                            |
| `@tanstack/svelte-query` | `^5.59` | Server-state management.                              |
| `@supabase/supabase-js` | `^2.45` | Supabase client (auth + storage).                      |
| `@supabase/ssr`         | `^0.10` | Cookie-aware Supabase clients for SvelteKit SSR (shared session with `hooks.server.ts`). |
| `pdfjs-dist`            | `^4.7`  | Render uploaded CVs in-browser for preview.            |
| `@tiptap/core`          | `^2.8`  | Rich-text editor for cover-letter editing.             |
| `@tiptap/starter-kit`   | `^2.8`  | Default TipTap extensions.                             |
| `zod`                   | `^3.23` | Form + payload validation on the client.               |
| `lucide-svelte`         | `^0.453` | Icon set.                                             |
| `date-fns`              | `^4.1`  | Date formatting.                                       |
| `@sentry/sveltekit`     | `^8.34` | Browser + SSR error reporting.                         |

## Frontend — dev / test

| Package                | Version | Purpose                                                 |
| ---------------------- | ------- | ------------------------------------------------------- |
| `vitest`               | `^2.1`  | Unit-test runner.                                       |
| `@testing-library/svelte` | `^5.2` | Component testing.                                   |
| `@playwright/test`     | `^1.48` | End-to-end tests.                                       |
| `eslint`               | `^9.13` | Linting.                                                |
| `eslint-plugin-svelte` | `^2.46` | Svelte-aware linting.                                   |
| `prettier`             | `^3.3`  | Formatting.                                             |
| `prettier-plugin-svelte` | `^3.2` | Svelte-aware formatting.                              |
| `svelte-check`         | `^4.0`  | TypeScript checks for `.svelte` files.                  |

## Infra

| Tool                  | Version | Purpose                                                 |
| --------------------- | ------- | ------------------------------------------------------- |
| Docker                | latest  | Container runtime (local + production base images).     |
| docker-compose        | v2      | Local dev orchestration.                                |
| PostgreSQL            | 16+     | Database (with `pgvector` extension installed).         |
| Redis                 | 7+      | Cache, Celery broker, Pub/Sub.                          |
| Kubernetes            | 1.30+   | Production runtime.                                     |
| ArgoCD                | latest  | GitOps deploys to k8s.                                  |
| GitHub Actions        | n/a     | CI.                                                     |
| Vercel                | n/a     | Frontend deploys.                                       |

## Adding a new dependency

1. Justify it in the PR description: what problem does it solve, what
   alternatives were rejected.
2. Pin the version per the policy above.
3. Add a row here with a one-line `Purpose`.
4. If it changes runtime architecture, write or update an ADR.
5. If it requires a new env var, add it to
   [`env-vars.md`](env-vars.md).
