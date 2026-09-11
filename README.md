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

## Development Container (DevPod)

The repo ships a devcontainer (`.devcontainer/`) replicating the omarchy
terminal environment on an Arch base: zsh + antidote, starship, nvim, atuin,
lazygit, btop, fastfetch, mise-managed tools, herdr, and docker-in-docker.
Personal configs and opencode skills come from the private
[Gathondu/dotfiles](https://github.com/Gathondu/dotfiles) repo, installed by
`post-create.sh`.

```bash
devpod up kaziro --recreate   # (re)build the workspace
devpod ssh kaziro             # zsh shell; docker compose up --build works inside
```

Environment secrets resolve from 1Password. Drop the service-account token
(scoped to the "Development" vault) at `~/.config/op/token` inside the
workspace once, then generate `.env`:

```bash
scp <token-file> kaziro.devpod:/home/dng/.config/op/token
devpod ssh kaziro -- 'chmod 600 ~/.config/op/token'
devpod ssh kaziro -- 'make env'   # op inject -i .env.op.tpl -o .env
```

Skill or config changes made locally sync into the workspace with:

```bash
make sync-dotfiles
```

Notes:

- Commit signing is forwarded to the host's 1Password via DevPod's Git SSH
  signature forwarding (`GIT_SSH_SIGNATURE_FORWARDING=true`).
- The docker daemon runs inside the workspace container; `host.docker.internal`
  points at the workspace, not your laptop — override the scrapper URLs in
  `.env` if it runs on your machine.
- One-time inside the workspace: `opencode auth login`.

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
