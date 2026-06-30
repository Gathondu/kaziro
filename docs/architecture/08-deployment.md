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

The GitHub Actions deploy workflow copies the package to the server, writes
the production env file from secrets, and runs the server deploy script.

## Frontend Production

Deploy `frontend/` to Vercel. Required public variables are documented in
[`../reference/env-vars.md`](../reference/env-vars.md).

## Database

Run Django migrations with:

```bash
cd backend
uv run python manage.py migrate
```

Migrations should be reviewed before deployment and kept compatible with the
currently deployed application code.
