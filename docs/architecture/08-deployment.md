# Deployment

**Status**: Active  
**Last updated**: 2026-06-09  
**Related ADRs**: [ADR-0003](../decisions/ADR-0003-auth-supabase.md), [ADR-0004](../decisions/ADR-0004-task-queue-celery-redis.md), [ADR-0007](../decisions/ADR-0007-frontend-sveltekit.md)  
**Code**: `infra/backend/`, `backend/Dockerfile`, `frontend/`, `.github/workflows/`

## 1. Active Hosting Model

Kaziro uses a split production deployment:

| Service | Production target |
| --- | --- |
| FastAPI backend | Docker Compose on `https://167.233.100.112` |
| Redis broker/cache/pubsub | Docker Compose on the same server |
| Celery workers | Docker Compose on the same server |
| Celery beat | Docker Compose on the same server |
| PostgreSQL/Auth/Storage | Supabase Cloud |
| Frontend | Vercel, project root `frontend` |

AWS is no longer an active deploy target. The old Terraform stack is retained
only long enough to destroy existing Kaziro AWS resources; see
[`09-aws-deployment-runbook.md`](09-aws-deployment-runbook.md).

## 2. Local Development

```bash
# From repo root
make dev
# or
docker compose up --build
```

`docker-compose.yml` brings up local Postgres, Redis, FastAPI, Celery workers,
beat, and the Vite dev server.

Useful local commands:

| Command | What it does |
| --- | --- |
| `make dev` | Bring up the full local stack |
| `make migrate` | Run `alembic upgrade head` |
| `make test` | Run backend and frontend tests |
| `make lint` | Run backend and frontend lint/type checks |
| `make e2e` | Run Playwright tests against a running stack |

## 3. Backend Server Deploy

GitHub Actions workflow: `.github/workflows/deploy-backend.yml`.

The workflow runs on pushes to `main` that touch backend or deployment files,
and can also be started manually with `workflow_dispatch`.

Deployment sequence:

1. Build a clean tarball containing `backend/` and `infra/backend/`.
2. Write `BACKEND_ENV_PRODUCTION` from GitHub Secrets to an env file.
3. Upload both files to `167.233.100.112` over SSH.
4. Install Docker Engine and the Compose plugin if missing.
5. Stage files under `/opt/kaziro`.
6. Run `infra/backend/deploy.sh` on the server.
7. Provision or renew the Let's Encrypt IP certificate.
8. Start or update Redis, FastAPI, workers, beat, Caddy, and certbot.

Required GitHub secrets:

| Secret | Purpose |
| --- | --- |
| `SERVER_USERNAME` | SSH user, usually `root` |
| `SERVER_SSH_PRIVATE_KEY` | Private key with SSH access to the server |
| `BACKEND_ENV_PRODUCTION` | Full production backend env block |

Optional GitHub secrets:

| Secret | Default |
| --- | --- |
| `SERVER_HOST` | `167.233.100.112` |
| `SERVER_PORT` | `22` |
| `SERVER_APP_DIR` | `/opt/kaziro` |
| `CERTBOT_EMAIL` | unset |
| `SERVER_PASSWORD` | unset, only for password SSH or sudo |
| `SERVER_SSH_PASSPHRASE` | unset |

## 4. Server Runtime

Production server files live under `/opt/kaziro`:

```text
/opt/kaziro/
├── backend/
├── compose.yaml
├── .env.production
├── Caddyfile.http
├── Caddyfile.https
├── deploy.sh
└── renew-cert.sh
```

`infra/backend/compose.yaml` defines:

- `redis`
- `backend`
- `worker-default`
- `worker-parser`
- `worker-evaluator`
- `worker-research-doc`
- `beat`
- `caddy`
- `certbot`

`deploy.sh` validates required env vars, starts Redis/backend/Caddy, runs
Alembic migrations, provisions the IP certificate if needed, then starts the
complete compose stack. Caddy terminates HTTPS on `167.233.100.112` and reverse
proxies both REST and WebSocket traffic to FastAPI.

## 5. Frontend Deploy

The frontend is hosted by Vercel Git integration, not GitHub Actions.

Vercel project settings:

| Setting | Value |
| --- | --- |
| Root directory | `frontend` |
| Install command | `pnpm install --frozen-lockfile` |
| Build command | `pnpm build` |
| Output directory | `build` |

Production Vercel env vars:

```env
PUBLIC_API_URL=https://167.233.100.112
PUBLIC_WS_URL=wss://167.233.100.112/api/v1/ws/notifications
PUBLIC_SUPABASE_URL=<supabase url>
PUBLIC_SUPABASE_ANON_KEY=<supabase anon key>
```

The backend `CORS_ORIGINS` value in `BACKEND_ENV_PRODUCTION` must include the
production Vercel origin. Add any stable preview domains used for QA.

## 6. Migrations

- Local: `make migrate`.
- Production: `infra/backend/deploy.sh` runs `alembic upgrade head` inside the
  runtime image before the full service rollout.
- Migrations must remain backwards-compatible between "migration applied" and
  "new API live". Use two-phase changes for drops and renames.

## 7. Validation

Deployment is healthy when:

- `https://167.233.100.112/health` returns `200`.
- `https://167.233.100.112/health/ready` reports ready.
- `docker compose --env-file .env.production ps` shows Redis, backend, all
  workers, beat, Caddy, and certbot healthy or running.
- Vercel frontend loads and calls `https://167.233.100.112`.
- WebSocket notifications connect through
  `wss://167.233.100.112/api/v1/ws/notifications`.
