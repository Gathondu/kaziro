# Kaziro — Root AGENTS.md

> The single entry point for any agent, tool, or human working in this repo.
> Read this first, then read the nearest workspace `AGENTS.md` when editing
> application code.

## Project identity

- **Name**: Kaziro
- **Mission**: AI-powered agentic job recommendation and application system.
  Kaziro fetches job postings, evaluates fit per user, gathers company
  context, and generates a tailored CV plus cover letter for every good fit.
- **Stack**: Python 3.14 · Django · Django Ninja · LangGraph · OpenRouter ·
  PostgreSQL + pgvector · Celery · Redis · Next.js App Router · React ·
  TypeScript · Tailwind CSS · DaisyUI · TanStack Query.

Detailed background: [`docs/architecture/01-system-overview.md`](docs/architecture/01-system-overview.md).

## Monorepo map

```text
kaziro/
├── AGENTS.md
├── README.md
├── backend/                 # Django, Django Ninja, Celery, LangGraph
│   └── AGENTS.md
├── frontend/                # Next.js App Router, React, TypeScript
│   └── AGENTS.md
├── docs/                    # architecture, design, decisions, reference
├── infra/                   # deployment and local infrastructure
├── scripts/                 # repo automation
└── .cursor/rules/           # detailed Cursor-enforced rules
```

ADR for this layout: [`docs/decisions/ADR-0009-monorepo-layout.md`](docs/decisions/ADR-0009-monorepo-layout.md).

## Workspace AGENTS.md files

Apply the nearest `AGENTS.md` plus all ancestor files above it.

| Editing files in...  | Read this AGENTS.md                        |
| -------------------- | ------------------------------------------ |
| Anywhere in the repo | [`AGENTS.md`](AGENTS.md)                   |
| `backend/**`         | [`backend/AGENTS.md`](backend/AGENTS.md)   |
| `frontend/**`        | [`frontend/AGENTS.md`](frontend/AGENTS.md) |

For cross-workspace changes, read every affected workspace file and apply the
most specific rule in each area.

## Where to run what

| You want to...        | Workspace   | Command                                                                                       |
| --------------------- | ----------- | --------------------------------------------------------------------------------------------- |
| Start the backend API | `backend/`  | `uv run python manage.py runserver 0.0.0.0:8000`                                              |
| Start a Celery worker | `backend/`  | `uv run celery -A config.celery:app worker --loglevel=INFO`                                   |
| Start Celery Beat     | `backend/`  | `uv run celery -A config.celery:app beat --loglevel=INFO --schedule=/tmp/celerybeat-schedule` |
| Run backend checks    | `backend/`  | `uv run python manage.py check`                                                               |
| Run backend tests     | `backend/`  | `uv run python manage.py test`                                                                |
| Apply DB migrations   | `backend/`  | `uv run python manage.py migrate`                                                             |
| Start the frontend    | `frontend/` | `pnpm dev`                                                                                    |
| Type-check frontend   | `frontend/` | `pnpm typecheck`                                                                              |
| Build frontend        | `frontend/` | `pnpm build`                                                                                  |
| Run E2E tests         | `frontend/` | `pnpm test:e2e`                                                                               |
| Boot local stack      | repo root   | `docker compose up --build`                                                                   |

If a listed command fails because a prerequisite is missing, stop and report
the missing prerequisite instead of guessing an alternate setup.

## Cardinal rules

1. **No secrets in the repo.** `.env` is ignored; update `.env.example` for
   documented variables.
2. **Update docs in the same PR as code changes.** Update ADRs for
   architectural shifts and reference docs for env vars or dependencies.
3. **Type everything.** Python and TypeScript code must avoid implicit `Any`.
4. **Structured logs only.** No `print()` in Python and no `console.log` in
   committed TypeScript.
5. **Tests for new behavior.** Use focused tests that cover the changed path.
6. **Conventional Commits.** Use `feat(scope): ...`, `fix(scope): ...`, or
   `docs(scope): ...`.
7. **Multi-tenant isolation.** Never bypass repository/service boundaries to
   read another user's data.

## Documentation index

| Task area                | Primary docs                                                                          |
| ------------------------ | ------------------------------------------------------------------------------------- |
| architecture/setup       | `docs/architecture/01-system-overview.md`, `docs/architecture/02-agentic-pipeline.md` |
| API                      | `docs/architecture/04-api-design.md`                                                  |
| UI                       | `docs/architecture/05-frontend-architecture.md`, `docs/design/frontend/`              |
| agents                   | `docs/design/agents/`                                                                 |
| observability            | `docs/architecture/06-observability.md`                                               |
| security review          | `docs/architecture/07-security.md`                                                    |
| deployment               | `docs/architecture/08-deployment.md`                                                  |
| docs/decisions/reference | `docs/decisions/`, `docs/reference/glossary.md`, `docs/reference/env-vars.md`         |

## Cursor rules

Detailed enforcement lives under [`.cursor/rules/`](.cursor/rules/). Cursor
users get them automatically; other agents should consult them when uncertain.

| Rule                    | Scope                        |
| ----------------------- | ---------------------------- |
| `000-master.mdc`        | Global                       |
| `001-agents.mdc`        | agentic pipeline code        |
| `002-backend.mdc`       | `backend/**`                 |
| `003-frontend.mdc`      | `frontend/**`                |
| `004-database.mdc`      | Django models and migrations |
| `005-testing.mdc`       | tests across the repo        |
| `006-observability.mdc` | logging, metrics, tracing    |

## When in doubt

- Do not invent missing architecture. Add or update the appropriate doc.
- Cite docs, ADRs, and rules in PR descriptions when they clarify intent.
- Keep `AGENTS.md` files small; detailed policy belongs in docs and rules.
