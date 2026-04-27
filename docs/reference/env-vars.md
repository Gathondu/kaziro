# Environment Variables Reference

**Status**: Living
**Last updated**: 2026-04-27
**Source**: Kaziro Design Document §13 + `.cursor/rules/002-backend.mdc`
**Related**: [`docs/architecture/08-deployment.md`](../architecture/08-deployment.md), [`docs/architecture/07-security.md`](../architecture/07-security.md)

This is the canonical list of environment variables consumed by the
Kaziro backend, frontend, and infra. Anything new added to
`backend/config.py` or `frontend/.env*` MUST be reflected here in the same PR.

Conventions:

- **Required** vars cause `Settings()` to fail at boot if missing.
- **Default** column shows the value used when the var is unset (or
  `—` if there is no default).
- **Scope** = `backend`, `frontend`, `worker` (Celery), or `infra`.
- All secrets live in the platform secret store (Doppler / Vault /
  Kubernetes secrets) — never commit `.env` with real values.

## Application

| Variable       | Required | Default       | Scope           | Description                                                                     |
| -------------- | -------- | ------------- | --------------- | ------------------------------------------------------------------------------- |
| `APP_ENV`      | Yes      | `development` | backend, worker | Environment name: `development`, `staging`, `production`.                       |
| `APP_NAME`     | No       | `kaziro`      | backend, worker | Used in logs, metrics labels, OpenTelemetry service name.                       |
| `LOG_LEVEL`    | No       | `INFO`        | backend, worker | `DEBUG`, `INFO`, `WARNING`, `ERROR`.                                            |
| `LOG_FORMAT`   | No       | `json`        | backend, worker | `json` (production) or `console` (local dev).                                   |
| `DEBUG`        | No       | `false`       | backend         | FastAPI debug mode. Always `false` in production.                               |
| `API_HOST`     | No       | `0.0.0.0`     | backend         | Bind address.                                                                   |
| `API_PORT`     | No       | `8000`        | backend         | HTTP port.                                                                      |
| `CORS_ORIGINS` | Yes      | —             | backend         | Comma-separated browser origins; must list **at least one** (empty fails boot). |

## Database (Supabase / Postgres)

| Variable                | Required | Default | Scope           | Description                                                      |
| ----------------------- | -------- | ------- | --------------- | ---------------------------------------------------------------- |
| `DATABASE_URL`          | Yes      | —       | backend, worker | Async SQLAlchemy URL: `postgresql+asyncpg://user:pw@host/db`.    |
| `DATABASE_URL_SYNC`     | Yes      | —       | worker, alembic | Sync URL for Alembic migrations: `postgresql://user:pw@host/db`. |
| `DATABASE_POOL_SIZE`    | No       | `10`    | backend, worker | SQLAlchemy connection-pool size.                                 |
| `DATABASE_MAX_OVERFLOW` | No       | `5`     | backend, worker | Pool overflow cap.                                               |
| `DATABASE_ECHO`         | No       | `false` | backend, worker | Log every SQL statement. Local dev only.                         |

## Supabase

| Variable                    | Required | Default     | Scope             | Description                                                          |
| --------------------------- | -------- | ----------- | ----------------- | -------------------------------------------------------------------- |
| `SUPABASE_URL`              | Yes      | —           | backend, frontend | Supabase project URL.                                                |
| `SUPABASE_ANON_KEY`         | Yes      | —           | frontend          | Public, RLS-restricted key for the browser SDK.                      |
| `SUPABASE_SERVICE_KEY`      | Yes      | —           | backend, worker   | Service-role key — bypasses RLS. Backend-only.                       |
| `SUPABASE_JWT_SECRET`       | Yes      | —           | backend           | Secret used to verify Supabase-issued JWTs.                          |
| `SUPABASE_STORAGE_BUCKET`   | No       | `documents` | backend           | Default storage bucket for CV uploads + generated PDFs.              |
| `SUPABASE_JOB_POSTS_BUCKET` | No       | `job_posts` | backend, worker   | Cached RapidAPI LinkedIn job-search JSON (sorted keyword filenames). |

## Redis

| Variable          | Required | Default | Scope           | Description                                 |
| ----------------- | -------- | ------- | --------------- | ------------------------------------------- |
| `REDIS_URL`       | Yes      | —       | backend, worker | `redis://` / `rediss://` Valkey or Redis URL. On AWS, App Runner and **`deploy-aws.yml`** `db-migrate` get this from Terraform (App Runner/ECS env + `terraform output redis_url` in CI); not only from `KAZIRO_BACKEND_ENV_JSON`. |
| `REDIS_CACHE_DB`  | No       | `0`     | backend         | DB index for app cache.                     |
| `REDIS_BROKER_DB` | No       | `1`     | worker          | DB index for Celery broker.                 |
| `REDIS_RESULT_DB` | No       | `2`     | worker          | DB index for Celery results.                |
| `REDIS_PUBSUB_DB` | No       | `3`     | backend         | DB index for WebSocket fan-out via Pub/Sub. |
| `WS_CONNECTIONS_TABLE` | No  | —       | backend, worker | DynamoDB table holding active WebSocket connections by user. |
| `WS_MANAGEMENT_API_ENDPOINT` | No | —   | backend, worker | API Gateway WebSocket Management endpoint (HTTPS URL with stage) used to `post_to_connection`. |

## Celery

| Variable                      | Required | Default                                      | Scope         | Description                                          |
| ----------------------------- | -------- | -------------------------------------------- | ------------- | ---------------------------------------------------- |
| `CELERY_BROKER_URL`           | Yes      | derived from `REDIS_URL` + `REDIS_BROKER_DB` | worker        | Celery broker URL.                                   |
| `CELERY_RESULT_BACKEND`       | Yes      | derived from `REDIS_URL` + `REDIS_RESULT_DB` | worker        | Celery result backend URL.                           |
| `CELERY_TASK_ALWAYS_EAGER`    | No       | `false`                                      | worker, tests | Run tasks inline (testing only).                     |
| `CELERY_WORKER_CONCURRENCY`   | No       | `4`                                          | worker        | Concurrency per worker.                              |
| `CELERY_WORKER_POOL`          | No       | `solo` on Windows, `prefork` on Unix         | worker        | Celery `--pool` (e.g. `solo` for local Windows dev). |
| `CELERY_TASK_TIME_LIMIT`      | No       | `1800`                                       | worker        | Hard time limit per task in seconds.                 |
| `CELERY_TASK_SOFT_TIME_LIMIT` | No       | `1500`                                       | worker        | Soft time limit; raises `SoftTimeLimitExceeded`.     |

## OpenRouter / LLM

| Variable                     | Required | Default                         | Scope           | Description                                                                 |
| ---------------------------- | -------- | ------------------------------- | --------------- | --------------------------------------------------------------------------- |
| `OPENROUTER_API_KEY`         | Yes      | —                               | backend, worker | [OpenRouter](https://openrouter.ai/) API key.                               |
| `OPENROUTER_API_BASE`        | No       | `https://openrouter.ai/api/v1`  | backend, worker | Override API base (self-hosted or non-default endpoint).                    |
| `OPENROUTER_APP_URL`         | No       | —                               | backend, worker | `HTTP-Referer` for OpenRouter attribution (recommended in production).      |
| `OPENROUTER_APP_TITLE`       | No       | —                               | backend, worker | `X-Title` for OpenRouter attribution.                                       |
| `OPENROUTER_TIMEOUT_SECONDS` | No       | `60`                            | backend, worker | Per-request timeout (seconds; converted for the OpenRouter client).         |
| `OPENROUTER_MAX_RETRIES`     | No       | `3`                             | backend, worker | Retries on 5xx / rate-limit.                                                |
| `LLM_MODEL_PARSER`           | No       | `openai/gpt-4o-mini`            | worker          | Parser chat model ([OpenRouter model id](https://openrouter.ai/models)).    |
| `LLM_MODEL_EVALUATOR`        | No       | `openai/gpt-4o`                 | worker          | Evaluator (all 3 passes).                                                   |
| `LLM_MODEL_RESEARCH`         | No       | `openai/gpt-4o`                 | worker          | Research brief generation.                                                  |
| `LLM_MODEL_DOCUMENT`         | No       | `openai/gpt-4o`                 | worker          | Document agent.                                                             |
| `LLM_EMBEDDING_MODEL`        | No       | `openai/text-embedding-3-small` | worker          | Embedding model for `job_postings.embedding` (OpenAI-compat on OpenRouter). |

## External integrations

| Variable                           | Required | Default           | Scope  | Description                                                         |
| ---------------------------------- | -------- | ----------------- | ------ | ------------------------------------------------------------------- |
| `RAPIDAPI_KEY`                     | Yes      | —                 | worker | RapidAPI key for the JSearch / job-search provider.                 |
| `RAPIDAPI_HOST`                    | Yes      | —                 | worker | RapidAPI host header (e.g., `jsearch.p.rapidapi.com`).              |
| `RAPIDAPI_JOB_FETCH_LIMIT`         | No       | `100`             | worker | Max jobs per RapidAPI request (clamped 10–5000; builder + fetcher). |
| `RAPIDAPI_FETCH_MAX_ATTEMPTS`      | No       | `6`               | worker | Retries for RapidAPI GET on 429 / 5xx / transient network errors.   |
| `RAPIDAPI_FETCH_RETRY_AFTER_CAP_S` | No       | `120`             | worker | Max seconds to honor upstream `Retry-After` on 429.                 |
| `FIRECRAWL_API_KEY`                | Yes      | —                 | worker | Firecrawl API key.                                                  |
| `FIRECRAWL_BASE_URL`               | No       | Firecrawl default | worker | Override (self-host or staging).                                    |

## Observability

| Variable                      | Required | Default                            | Scope                     | Description                            |
| ----------------------------- | -------- | ---------------------------------- | ------------------------- | -------------------------------------- |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No       | —                                  | backend, worker           | OpenTelemetry OTLP collector endpoint. |
| `OTEL_SERVICE_NAME`           | No       | `kaziro-backend` / `kaziro-worker` | backend, worker           | Trace service name.                    |
| `OTEL_SAMPLE_RATE`            | No       | `0.1`                              | backend, worker           | Trace sample rate (0.0 – 1.0).         |
| `PROMETHEUS_METRICS_PATH`     | No       | `/metrics`                         | backend                   | Prometheus scrape path.                |
| `SENTRY_DSN`                  | No       | —                                  | backend, worker, frontend | Sentry DSN; absence disables Sentry.   |
| `SENTRY_ENV`                  | No       | mirrors `APP_ENV`                  | backend, worker, frontend | Sentry environment label.              |
| `SENTRY_TRACES_SAMPLE_RATE`   | No       | `0.05`                             | backend, worker           | Sentry transaction sample rate.        |

### LangSmith

| Variable             | Required | Default           | Scope           | Description                                                                                                    |
| -------------------- | -------- | ----------------- | --------------- | -------------------------------------------------------------------------------------------------------------- |
| `LANGSMITH_TRACING`  | Yes      | `true`            | backend, worker | When `true` and `LANGSMITH_API_KEY` is set, enables `@traceable` export (startup calls `langsmith.configure`). |
| `LANGSMITH_API_KEY`  | Yes      | `api_key`         | backend, worker | LangSmith API key; required for hosted export when tracing is on.                                              |
| `LANGSMITH_PROJECT`  | Yes      | `Kaziro`          | backend, worker | Project / session name in the LangSmith UI.                                                                    |
| `LANGSMITH_ENDPOINT` | Yes      | LangSmith default | backend, worker | API base URL (e.g. regional or self-hosted).                                                                   |

## Frontend (`frontend/.env`)

Frontend env vars are exposed to the browser only when prefixed with
`PUBLIC_` (SvelteKit convention).

| Variable                   | Required | Default       | Description                                              |
| -------------------------- | -------- | ------------- | -------------------------------------------------------- |
| `PUBLIC_API_BASE_URL`      | Yes      | —             | Backend REST base URL (e.g., `https://api.kaziro.com`).  |
| `PUBLIC_WS_URL`            | Yes      | —             | Backend WebSocket URL (e.g., `wss://api.kaziro.com/ws`). |
| `PUBLIC_SUPABASE_URL`      | Yes      | —             | Mirrors `SUPABASE_URL`.                                  |
| `PUBLIC_SUPABASE_ANON_KEY` | Yes      | —             | Mirrors `SUPABASE_ANON_KEY`.                             |
| `PUBLIC_SENTRY_DSN`        | No       | —             | Browser Sentry DSN.                                      |
| `PUBLIC_APP_ENV`           | No       | `development` | Surfaces in error reports + dev-tooling.                 |
| `PUBLIC_SITE_URL`          | No       | —               | Canonical public site origin (no trailing slash) for SEO on `/` (`canonical`, `og:url`). When unset, the app uses the incoming request origin. |

## Local dev only

| Variable         | Required | Default | Description                                         |
| ---------------- | -------- | ------- | --------------------------------------------------- |
| `RELOAD`         | No       | `true`  | uvicorn `--reload` flag.                            |
| `MOCK_LLM`       | No       | `false` | Replace LLM calls with deterministic stubs (tests). |
| `MOCK_FIRECRAWL` | No       | `false` | Use VCR cassettes for Firecrawl in tests.           |

## Adding a new env var

1. Add it to `backend/config.py` (`Settings` class) **with** a type and
   default (or `Field(...)` if required).
2. Add a row here in the right table.
3. Add it to `.env.example` at the repo root.
4. If the var is a secret, document in [`docs/architecture/07-security.md`](../architecture/07-security.md)
   how it is provisioned (Doppler, Vault, k8s secret).
5. Mention it in the relevant `AGENTS.md` if it changes how the workspace
   behaves locally.
