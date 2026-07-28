# Deployment

**Status**: Active
**Last updated**: 2026-06-29

Kaziro deploys the backend and workers as Docker services. The frontend is a
Next.js app intended for Vercel.

## Local

```bash
docker compose up --build
```

Services:

- `postgres`
- `redis`
- `backend`
- `worker`
- `beat`
- `frontend`

Host commands are available through the root `Makefile`.

## Backend Production

The backend deployment package includes:

- `backend/`
- `infra/backend/compose.yaml`
- `infra/backend/deploy.sh`
- `infra/backend/env.production.example`

The backend must run as ASGI for long-lived SSE responses. The container uses
Uvicorn with `config.asgi:application`; WSGI development servers are not a
supported notification-stream runtime.

Uvicorn must use a finite graceful-shutdown timeout because SSE connections
are intentionally long-lived. Development uses two seconds for responsive
reloads, while the container allows ten seconds for Redis subscription
cleanup before Uvicorn cancels remaining connection tasks.

The GitHub Actions deploy workflow copies the package to the server, writes
the production env file from secrets, and runs the server deploy script.

The production proxy must route
`/api/v1/notifications/stream` directly to Django ASGI without response
buffering or a short upstream timeout. The Caddy reference configuration at
`infra/backend/Caddyfile.example` uses `flush_interval -1` for immediate SSE
delivery. Health checks remain ordinary short HTTP requests.

## Frontend Production

Deploy `frontend/` to Vercel. Required public variables are documented in
[`../reference/env-vars.md`](../reference/env-vars.md).

## Database

PostgreSQL must have the `vector` extension installed before the first
migration. The Django migrations run `CREATE EXTENSION IF NOT EXISTS vector`
and create 2048-dimension profile and posting vectors.

Run Django migrations with:

```bash
cd backend
uv run python manage.py migrate
```

Migrations should be reviewed before deployment and kept compatible with the
currently deployed application code.
