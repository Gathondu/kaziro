# Kaziro — Root AGENTS.md

> The single entry point for any agent (Cursor, Claude Code, Codex CLI,
> humans) working in this repo. Read this first, then descend into the
> nearest workspace [`AGENTS.md`](#workspace-agentsmd-files).

## Project identity

- **Name**: Kaziro
- **Mission**: AI-powered agentic job recommendation and application
  system. Kaziro fetches job postings, evaluates fit per user, gathers
  company context, and generates a tailored CV + cover letter for every
  good fit.
- **Stack**: Python 3.12 · FastAPI · LangGraph · OpenRouter · PostgreSQL +
  pgvector · Supabase · Celery · Redis · SvelteKit · Svelte 5 · Tailwind ·
  TanStack Query.

Detailed background: [`docs/architecture/01-system-overview.md`](docs/architecture/01-system-overview.md).

## Monorepo map

```
kaziro/
├── AGENTS.md                  ← you are here
├── README.md                  ← human quick-start
├── backend/                   ← Python (FastAPI + LangGraph + Celery)
│   ├── AGENTS.md              ← backend-wide rules
│   └── agents/
│       ├── AGENTS.md          ← LangGraph-specific rules
│       ├── parser_agent.py
│       ├── evaluator_agent.py
│       ├── research_agent.py
│       ├── document_agent.py
│       └── pipeline_orchestrator.py
├── frontend/                  ← SvelteKit + Svelte 5 + Tailwind
│   └── AGENTS.md              ← frontend-wide rules
├── docs/                      ← architecture, design, decisions, reference
│   ├── README.md
│   ├── architecture/
│   ├── design/
│   ├── decisions/
│   └── reference/
├── infra/                     ← (future) docker-compose, k8s, monitoring
└── .cursor/rules/             ← detailed Cursor-enforced rules
```

ADR for this layout: [`docs/decisions/ADR-0009-monorepo-layout.md`](docs/decisions/ADR-0009-monorepo-layout.md).

## Workspace AGENTS.md files

Edit a file? Read the **nearest** AGENTS.md as authoritative — it
inherits the rules above it.

| Editing files in…             | Read this AGENTS.md                                                      |
| ----------------------------- | ------------------------------------------------------------------------ |
| Anywhere in the repo          | [`AGENTS.md`](AGENTS.md) (this file)                                     |
| `backend/**`                  | [`backend/AGENTS.md`](backend/AGENTS.md)                                 |
| `backend/agents/**`           | [`backend/agents/AGENTS.md`](backend/agents/AGENTS.md)                   |
| `frontend/**`                 | [`frontend/AGENTS.md`](frontend/AGENTS.md)                               |

ADR for this hierarchy: [`docs/decisions/ADR-0010-agents-md-hierarchy.md`](docs/decisions/ADR-0010-agents-md-hierarchy.md).

## Where to run what

| You want to…                                  | Workspace        | Command                                                  |
| --------------------------------------------- | ---------------- | -------------------------------------------------------- |
| Start the backend API (dev)                   | `backend/`       | `uv run uvicorn main:app --reload`                       |
| Start a Celery worker                         | `backend/`       | `uv run celery -A celery_app worker --loglevel=INFO`     |
| Start Celery Beat (scheduler)                 | `backend/`       | `uv run celery -A celery_app beat --loglevel=INFO`       |
| Run backend tests                             | `backend/`       | `uv run pytest --cov=backend`                            |
| Apply DB migrations                           | `backend/`       | `uv run alembic upgrade head`                            |
| Start the frontend (dev)                      | `frontend/`      | `pnpm dev`                                               |
| Run frontend unit tests                       | `frontend/`      | `pnpm test`                                              |
| Run E2E (Playwright) tests                    | repo root        | `pnpm e2e`                                               |
| Boot the whole stack locally                  | repo root        | `docker compose up`                                      |

If `infra/` and root `Makefile` are present they expose convenience
targets — see [`docs/architecture/08-deployment.md`](docs/architecture/08-deployment.md).

## Cardinal rules (apply everywhere)

1. **No secrets in the repo.** `.env` is git-ignored; commit
   `.env.example` instead. See
   [`docs/reference/env-vars.md`](docs/reference/env-vars.md).
2. **Update docs in the same PR as code changes.** Especially:
   ADRs for architectural shifts, env-vars / dependencies for new deps,
   and the relevant AGENTS.md if a workflow changes.
3. **Type everything.** Python and TypeScript both — no implicit `Any`.
4. **Structured logs only.** Never `print()` (Python) and never
   `console.log` in committed code (TS).
5. **Tests for new behaviour.** See
   [`docs/design/testing-strategy.md`](docs/design/testing-strategy.md).
6. **Conventional Commits.** `feat(scope): …`, `fix(scope): …`,
   `docs(scope): …`. Branch names: `feat/<id>-<short>`.
7. **Multi-tenant isolation.** Never bypass the repository / RLS layer
   to query another user's data. See
   [`docs/architecture/07-security.md`](docs/architecture/07-security.md).

## Documentation index

Start with the doc that matches your task:

- New here? Read in order: [`docs/architecture/01-system-overview.md`](docs/architecture/01-system-overview.md)
  → [`docs/architecture/02-agentic-pipeline.md`](docs/architecture/02-agentic-pipeline.md)
  → [`docs/architecture/03-data-model.md`](docs/architecture/03-data-model.md).
- Building an agent? [`docs/design/agents/`](docs/design/agents/) +
  [`backend/agents/AGENTS.md`](backend/agents/AGENTS.md).
- Building an API endpoint?
  [`docs/architecture/04-api-design.md`](docs/architecture/04-api-design.md).
- Building a UI? [`docs/architecture/05-frontend-architecture.md`](docs/architecture/05-frontend-architecture.md)
  + [`docs/design/frontend/`](docs/design/frontend/).
- Adding a metric / log / alert? [`docs/architecture/06-observability.md`](docs/architecture/06-observability.md).
- Security review? [`docs/architecture/07-security.md`](docs/architecture/07-security.md).
- Deploying? [`docs/architecture/08-deployment.md`](docs/architecture/08-deployment.md).
- Why was X chosen? [`docs/decisions/`](docs/decisions/).
- What does X mean? [`docs/reference/glossary.md`](docs/reference/glossary.md).
- What does X env var do? [`docs/reference/env-vars.md`](docs/reference/env-vars.md).
- What's coming next? [`docs/design/roadmap.md`](docs/design/roadmap.md)
  (high-level phases) and [`PLAN.md`](PLAN.md) (task-by-task build
  tracker — pick the next unblocked `[ ]` task).

## Cursor rules

Detailed enforcement lives under [`.cursor/rules/`](.cursor/rules/). The
AGENTS.md files in this repo summarise the rules for human / agent
quick-reference but do not replace them. Cursor users get them
automatically; other agents should consult them when uncertain.

| Rule                                                      | Scope                          |
| --------------------------------------------------------- | ------------------------------ |
| [`000-master.mdc`](.cursor/rules/000-master.mdc)          | Global (always applies)        |
| [`001-agents.mdc`](.cursor/rules/001-agents.mdc)          | `backend/agents/**`            |
| [`002-backend.mdc`](.cursor/rules/002-backend.mdc)        | `backend/**`                   |
| [`003-frontend.mdc`](.cursor/rules/003-frontend.mdc)      | `frontend/**`                  |
| [`004-database.mdc`](.cursor/rules/004-database.mdc)      | `backend/db/**`, migrations    |
| [`005-testing.mdc`](.cursor/rules/005-testing.mdc)        | tests across the repo          |
| [`006-observability.mdc`](.cursor/rules/006-observability.mdc) | logging, metrics, tracing |

## When in doubt

- **Don't invent.** If a doc is missing, write it. If a rule conflicts,
  raise it in the PR.
- **Cite your sources.** Reference docs, ADRs, and rules in PR
  descriptions and code comments where it clarifies intent.
- **Keep AGENTS.md files small** (≤ 200 lines). Detail belongs in
  `docs/` and `.cursor/rules/`.
