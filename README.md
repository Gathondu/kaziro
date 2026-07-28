# Kaziro

AI-powered agentic job recommendation and application system. Kaziro fetches
job postings, evaluates fit per user, gathers company context, and generates a
tailored CV plus cover letter for every good fit.

Start with [`AGENTS.md`](AGENTS.md) for contributor instructions. Detailed
architecture and design docs live under [`docs/`](docs/).

## Stack

- **Backend**: Python 3.14, Django, Django Ninja, LangGraph, Celery, Redis.
- **Database**: PostgreSQL 16 with pgvector.
- **Frontend**: Next.js App Router, React, TypeScript, Tailwind CSS, DaisyUI,
  TanStack Query.
- **Infra**: Docker Compose, Caddy, Vercel, GitHub Actions.

## Repo Layout

```text
kaziro/
├── AGENTS.md
├── README.md
├── backend/           # Django API, Celery workers, agent orchestration
├── frontend/          # Next.js application
├── docs/              # architecture, design, decisions, reference
├── infra/             # deployment and local infrastructure
└── scripts/           # repository automation
```

## Quick Start

Prerequisites:

- Python 3.14 and `uv`
- Node 22 and `pnpm`
- Docker Compose
- PostgreSQL, Redis, and API keys documented in `.env.example`

```bash
cp .env.example .env
docker compose up -d postgres redis
```

Backend:

```bash
cd backend
uv sync
uv run python manage.py migrate
uv run uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --reload --timeout-graceful-shutdown 2
```

Frontend:

```bash
cd frontend
pnpm install
pnpm dev
```

Full local stack:

```bash
docker compose up --build
```

## Common Commands

```bash
make install
make dev
make lint
make test
make build-frontend
```

Backend checks:

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run python manage.py check
uv run python manage.py test
```

Frontend checks:

```bash
cd frontend
pnpm lint
pnpm typecheck
pnpm build
pnpm test:e2e
```

## Documentation

- Architecture: [`docs/architecture/01-system-overview.md`](docs/architecture/01-system-overview.md)
- API design: [`docs/architecture/04-api-design.md`](docs/architecture/04-api-design.md)
- Frontend architecture: [`docs/architecture/05-frontend-architecture.md`](docs/architecture/05-frontend-architecture.md)
- Deployment: [`docs/architecture/08-deployment.md`](docs/architecture/08-deployment.md)
- Environment variables: [`docs/reference/env-vars.md`](docs/reference/env-vars.md)
- Dependencies: [`docs/reference/dependencies.md`](docs/reference/dependencies.md)

## Contribution Rules

- Keep secrets out of the repo.
- Preserve the `{ data, meta, error }` API envelope.
- Use structured logging.
- Add tests for new behavior.
- Update docs when workflows, env vars, dependencies, or architecture change.
