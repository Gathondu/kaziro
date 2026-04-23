# Kaziro

AI-powered agentic job recommendation and application system. Kaziro
fetches job postings, evaluates fit per user, gathers company context, and
generates a tailored CV + cover letter for every good fit.

> **Where to start**: [`AGENTS.md`](AGENTS.md) is the entry point for any
> contributor (human or AI). Detailed docs live under [`docs/`](docs/).
>
> **Current build status**: see [`PLAN.md`](PLAN.md) for the
> task-by-task MVP plan and what's done / next up.

## Stack

- **Backend**: Python 3.12 · FastAPI · LangGraph · OpenRouter · Celery · Redis
- **Database**: PostgreSQL 16 + pgvector (via Supabase)
- **Frontend**: SvelteKit · Svelte 5 (runes) · TailwindCSS · DaisyUI · TanStack Query
- **Infra**: Docker · Kubernetes · Vercel · GitHub Actions · ArgoCD

Full architecture: [`docs/architecture/01-system-overview.md`](docs/architecture/01-system-overview.md).

## Repo layout

```
kaziro/
├── AGENTS.md          ← read this first
├── README.md          ← you are here
├── backend/           ← FastAPI + LangGraph + Celery
├── frontend/          ← SvelteKit
├── docs/              ← architecture, design, decisions, reference
├── infra/             ← (future) docker-compose, k8s, monitoring
└── .cursor/rules/     ← detailed coding rules
```

ADR for the layout: [`docs/decisions/ADR-0009-monorepo-layout.md`](docs/decisions/ADR-0009-monorepo-layout.md).

## Quick start

### Prerequisites

- Python 3.12+ and [`uv`](https://docs.astral.sh/uv/)
- Node 20+ and [`pnpm`](https://pnpm.io/)
- Docker + docker-compose
- A Supabase project (free tier is fine)
- An OpenRouter API key

### 1. Clone and configure

```bash
git clone https://github.com/<org>/kaziro.git
cd kaziro
cp .env.example .env
# fill in SUPABASE_*, OPENROUTER_API_KEY, RAPIDAPI_KEY, FIRECRAWL_API_KEY, ...
```

Full env-var reference: [`docs/reference/env-vars.md`](docs/reference/env-vars.md).

### 2. Bring up infra (Postgres + Redis)

```bash
docker compose up -d postgres redis
```

### 3. Backend

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn main:app --reload
# in a second terminal:
uv run celery -A celery_app worker --loglevel=INFO
# (optional) cron scheduler:
uv run celery -A celery_app beat --loglevel=INFO
```

API now serves at <http://localhost:8000> · OpenAPI at `/docs`.

### 4. Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

App now serves at <http://localhost:5173>.

### 5. Run tests

```bash
# backend
cd backend && uv run pytest --cov=backend

# frontend unit
cd frontend && pnpm test

# end-to-end (requires backend + frontend running)
cd frontend && pnpm e2e
```

Detail: [`docs/design/testing-strategy.md`](docs/design/testing-strategy.md).

## Documentation

| Topic                     | Where                                                                                |
| ------------------------- | ------------------------------------------------------------------------------------ |
| System overview           | [`docs/architecture/01-system-overview.md`](docs/architecture/01-system-overview.md) |
| Agentic pipeline          | [`docs/architecture/02-agentic-pipeline.md`](docs/architecture/02-agentic-pipeline.md) |
| Data model & ERD          | [`docs/architecture/03-data-model.md`](docs/architecture/03-data-model.md)           |
| API reference             | [`docs/architecture/04-api-design.md`](docs/architecture/04-api-design.md)           |
| Frontend architecture     | [`docs/architecture/05-frontend-architecture.md`](docs/architecture/05-frontend-architecture.md) |
| Observability             | [`docs/architecture/06-observability.md`](docs/architecture/06-observability.md)     |
| Security                  | [`docs/architecture/07-security.md`](docs/architecture/07-security.md)               |
| Deployment                | [`docs/architecture/08-deployment.md`](docs/architecture/08-deployment.md)           |
| Per-agent design specs    | [`docs/design/agents/`](docs/design/agents/)                                          |
| Frontend design specs     | [`docs/design/frontend/`](docs/design/frontend/)                                      |
| Roadmap                   | [`docs/design/roadmap.md`](docs/design/roadmap.md)                                   |
| Architecture decisions    | [`docs/decisions/`](docs/decisions/)                                                  |
| Env-var reference         | [`docs/reference/env-vars.md`](docs/reference/env-vars.md)                           |
| Dependency reference      | [`docs/reference/dependencies.md`](docs/reference/dependencies.md)                   |
| Glossary                  | [`docs/reference/glossary.md`](docs/reference/glossary.md)                           |

Doc index: [`docs/README.md`](docs/README.md).

## For agents and contributors

Read the [`AGENTS.md`](AGENTS.md) file in the directory you're editing.
The hierarchy:

| Editing files in…    | Read this AGENTS.md                                    |
| -------------------- | ------------------------------------------------------ |
| Anywhere             | [`AGENTS.md`](AGENTS.md) (root)                        |
| `backend/**`         | [`backend/AGENTS.md`](backend/AGENTS.md)               |
| `backend/agents/**`  | [`backend/agents/AGENTS.md`](backend/agents/AGENTS.md) |
| `frontend/**`        | [`frontend/AGENTS.md`](frontend/AGENTS.md)             |

Detailed enforcement rules live under [`.cursor/rules/`](.cursor/rules/).
ADR for this hierarchy: [`docs/decisions/ADR-0010-agents-md-hierarchy.md`](docs/decisions/ADR-0010-agents-md-hierarchy.md).

## Contributing

- Branches: `feat/<id>-<short>`, `fix/<id>-<short>`.
- Commits: [Conventional Commits](https://www.conventionalcommits.org/) —
  `feat(evaluator): add critic node`.
- PRs must pass `ruff`, `mypy`, `pytest`, `eslint`, `svelte-check`,
  `vitest`.
- Update docs in the same PR as the change. ADR for any architectural
  shift.
- See [`AGENTS.md`](AGENTS.md) "Cardinal rules".

## License

Proprietary — © Kaziro. All rights reserved.
