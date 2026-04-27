# Deployment

**Status**: Active
**Last updated**: 2026-04-27
**Source**: Sections 2.3 and 9.2 of [`Kaziro_Design_Document.pdf`](../../Kaziro_Design_Document.pdf)
**Related ADRs**: [ADR-0003](../decisions/ADR-0003-auth-supabase.md), [ADR-0004](../decisions/ADR-0004-task-queue-celery-redis.md), [ADR-0007](../decisions/ADR-0007-frontend-sveltekit.md)
**Code (target)**: `infra/`, `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`, `.github/workflows/`

## 1. Environments

| Environment   | Purpose                                       | URL                                | Branch          |
| ------------- | --------------------------------------------- | ---------------------------------- | --------------- |
| `development` | Local laptops                                 | `http://localhost:5173` / `:8000`  | feature branches |
| `staging`     | Pre-production validation, E2E + load tests   | `https://staging.kaziro.io`        | `main`          |
| `production`  | Live customer traffic                         | `https://app.kaziro.io`            | `main` (tagged) |

The `ENVIRONMENT` env var carries the active environment name and is read
by `backend/config.py` and the frontend build.

## 2. Local development

### 2.1 One-command bring-up

```bash
# From repo root
make dev          # or: docker compose up --build
```

`docker-compose.yml` brings up:

- `postgres` — PostgreSQL 16 + pgvector (or use Supabase local stack).
- `redis` — Redis 7.
- `backend` — FastAPI (Uvicorn, hot-reload).
- `worker` — Celery worker.
- `beat` — Celery beat (scheduler).
- `frontend` — Vite dev server.
- `prometheus` + `grafana` — observability stack (optional profile).
- `jaeger` — local tracing UI (optional profile).

### 2.2 Pre-flight

- Copy `.env.example` to `.env` at repo root and fill in API keys
  (`OPENROUTER_API_KEY`, `RAPIDAPI_KEY`, `FIRECRAWL_API_KEY`, Supabase keys).
- Run migrations: `make migrate` (wraps `alembic upgrade head`).
- Seed dev DB: `make seed`.
- Open the app at <http://localhost:5173>.

### 2.3 Useful targets

| Command           | What it does                                          |
| ----------------- | ----------------------------------------------------- |
| `make dev`        | Bring up the full stack with hot reload               |
| `make migrate`    | `alembic upgrade head`                                |
| `make migration`  | `alembic revision --autogenerate -m "..."`            |
| `make test`       | `pytest backend/tests/ --cov=backend`                 |
| `make lint`       | `ruff check . && ruff format --check . && mypy backend` |
| `make e2e`        | `playwright test` against running stack               |
| `make logs`       | Tail backend + worker + beat logs                     |
| `make psql`       | Open psql against local Postgres                      |

## 3. Container images

### 3.1 Backend image (`backend/Dockerfile`)

Multi-stage build:

1. `builder` — Python 3.12-slim + uv install of dependencies into a venv.
2. `runtime` — Copies the venv and the `backend/` source. Runs as `appuser`
   (UID 1000). Entrypoint switches between `uvicorn`, `celery worker`, and
   `celery beat` based on the `KAZIRO_ROLE` env var.

```dockerfile
# (sketch)
FROM python:3.12-slim AS builder
RUN pip install uv
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY backend/ /app/
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER 1000
ENTRYPOINT ["./entrypoint.sh"]
```

### 3.2 Frontend image (`frontend/Dockerfile`)

Multi-stage build:

1. `builder` — Node 20 + pnpm; runs `pnpm build` (SvelteKit Node adapter
   for self-hosting; or build artefact uploaded to Vercel).
2. `runtime` — `node:20-slim` running `node build/`.

For Vercel/Netlify deployment, the frontend image isn't used in production
— the platform builds from the repo on push.

## 4. Production deployment matrix

| Service               | Local (compose)     | Production                                             |
| --------------------- | ------------------- | ------------------------------------------------------ |
| FastAPI backend       | container `:8000`   | Kubernetes Deployment (≥ 2 replicas) behind Ingress    |
| Celery workers        | container           | Kubernetes Deployment (HPA on `kaziro_celery_queue_depth`) |
| Celery beat           | container           | Kubernetes Deployment (1 replica, leader-elected)      |
| Redis                 | container `:6379`   | Managed (Upstash / ElastiCache / Memorystore)          |
| PostgreSQL + pgvector | Supabase local      | Supabase Cloud                                         |
| Object storage        | Supabase local      | Supabase Storage Cloud                                 |
| Frontend              | Vite dev `:5173`    | Vercel (preferred) or Netlify CDN                      |
| Firecrawl             | Cloud API           | Cloud API                                              |
| OpenRouter            | Cloud API           | Cloud API                                              |
| Metrics               | Prometheus container | Managed Prometheus + Grafana Cloud                    |
| Logs                  | stdout              | Centralised store (Loki / DataDog)                     |
| Traces                | Jaeger container    | Grafana Tempo                                          |

## 5. Kubernetes manifests

`infra/k8s/` contains:

```
infra/k8s/
├── base/
│   ├── kustomization.yaml
│   ├── backend-deployment.yaml
│   ├── backend-service.yaml
│   ├── worker-deployment.yaml
│   ├── beat-deployment.yaml
│   ├── ingress.yaml
│   ├── networkpolicies.yaml
│   ├── secret.envFrom.yaml      # references external secrets, no values
│   └── configmap.yaml
├── overlays/
│   ├── staging/
│   └── production/
└── monitoring/
    ├── servicemonitor.yaml
    └── prometheus-rule.yaml
```

Key practices:

- **No literal secrets** in manifests — they are pulled at deploy time from
  the secrets manager via `external-secrets-operator`.
- **HPA** on the worker deployment uses both CPU and the custom Prometheus
  metric `kaziro_celery_queue_depth`.
- **PodDisruptionBudget** on backend (`minAvailable: 1`) protects rolling
  upgrades.
- **NetworkPolicy** restricts pod-to-pod traffic to the minimum required.

## 6. CI/CD pipeline

`.github/workflows/ci.yml`:

1. **PR opened** → Lint (`ruff`, `mypy`, `pnpm lint`), unit tests
   (`pytest`, `vitest`). Target: < 3 minutes.
2. **Merge to `main`** → Full test suite including integration tests
   (against ephemeral Postgres+Redis). Build Docker images, push to
   registry, create GitHub release with auto-generated changelog.
3. **Staging deploy** → ArgoCD syncs `infra/k8s/overlays/staging/`. After
   pods are ready, run Playwright E2E against staging.
4. **Manual approval** → Required to promote to production.
5. **Production deploy** → Blue/green rollout via ArgoCD; smoke tests
   against the green environment before swapping traffic. Automatic
   rollback on alert spike.

Frontend (Vercel) deploys on every push to `main` (production) and on every
PR (preview URL). PR previews are commented on by the Vercel bot.

## 7. Database migrations

- **Local**: `make migrate` (Alembic `upgrade head`) against your Postgres.
- **AWS (`deploy-aws.yml`)**: After the backend image is pushed to ECR, a
  **`db-migrate`** job loads `kaziro/<environment>/backend/runtime-env-json`
  from Secrets Manager (same JSON as `KAZIRO_BACKEND_ENV_JSON` on App Runner),
  runs `alembic upgrade head` inside that image, then Terraform applies.
  Failed migrations stop the workflow before infra rollout.
- **Kubernetes** (if used): migrations run as a `Job` **before** new backend
  pods roll out (same compatibility rules as below).
- Always **backwards-compatible** between “migrate” and “new API revision live”:
  never drop a column or rename in the same release as the code that depends on
  it. Prefer two-phase migrations (add → backfill → switch reads → drop old).
- The migration job uses credentials from the runtime secret (typically
  **service-role** DB access where applicable) — RLS may be bypassed for DDL.
- Failed migrations halt the deploy; fix forward or roll back the migration.

## 8. Configuration

- All config values live in env vars (see
  [`reference/env-vars.md`](../reference/env-vars.md)).
- Loaded via Pydantic `BaseSettings` in `backend/config.py`. Single
  `settings` singleton imported everywhere.
- Required vars have no default; the app fails fast on startup if any
  required var is missing.
- The Kubernetes `ConfigMap` carries non-secret values (`ENVIRONMENT`,
  `LOG_LEVEL`, model overrides). Secrets are mounted from the secrets
  manager.

## 9. Secrets management

- Source of truth: external secrets manager (Vault / AWS Secrets
  Manager / GCP Secret Manager).
- `external-secrets-operator` syncs values into Kubernetes `Secret` objects
  every 15 minutes.
- Rotation policy: 90 days max for OpenRouter/RapidAPI/Firecrawl keys; 30 days
  for `SECRET_KEY`. Rotation is zero-downtime — keys are rolled while pods
  pick up the new value via env var refresh on next restart.

## 10. Backups & disaster recovery

- **PostgreSQL**: Supabase managed daily snapshots, 30-day retention. Point-
  in-time recovery enabled.
- **Storage**: Supabase Storage versioning enabled on the `cv` and
  `documents` buckets.
- **Recovery objective**: RPO 1 hour, RTO 4 hours.
- DR drill quarterly: restore to a clone project, verify backend can connect
  and key flows pass.

## 11. Cost controls

- Per-user pipeline rate limits (see
  [`07-security.md`](07-security.md#6-rate-limiting--abuse-prevention))
  cap LLM cost runaway.
- Token usage tracked via `kaziro_llm_tokens_used_total`; budget alerts
  fire at 80% of the monthly cap.
- Worker HPA scales **up** quickly but **down** with a 10-minute cool-down
  to avoid thrash.

## 12. Frontend deploy (Vercel)

- Repository connected to a Vercel project. Build command: `pnpm build`.
  Output dir: `frontend/.svelte-kit/output`.
- Environment variables set per environment (`Preview`, `Production`):
  - `VITE_API_URL`
  - `VITE_SUPABASE_URL`
  - `VITE_SUPABASE_ANON_KEY`
- Preview deployments are auto-created for every PR with a unique URL.
- Production deploy on push to `main`. Promotion requires the same approval
  step as the backend.
