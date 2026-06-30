# ADR-0009: Flat monorepo layout — `backend/`, `frontend/`, `docs/` at root

**Status**: Accepted
**Date**: 2026-04-22
**Deciders**: Founding engineering team
**Tags**: repo, infra, dx

## Context and problem statement

Kaziro consists of (at minimum) a Python backend (Django Ninja + LangGraph +
Celery) and a Next.js frontend, plus shared documentation, CI config,
docker-compose, and infra manifests. Two main shapes are common in the
Python+JS ecosystem:

- **Polyrepo** — separate Git repos for backend and frontend.
- **Monorepo** — a single Git repo containing both, with project-wide
  configuration at the root.

Inside a monorepo there are also two common shapes:

- **Flat**: `backend/`, `frontend/`, `docs/`, `infra/` at the root.
- **Wrapped python package**: code lives under e.g. `kaziro/backend/`,
  `kaziro/frontend/`. The early `.cursor/rules` glob patterns hinted at
  this (they referenced `kaziro/agents/`, `kaziro/api/`).

Existing code already lives under `backend/apps/pipeline/` — the `kaziro/`
wrapper was only ever a glob convention.

> "Should Kaziro be one repo with `backend/` and `frontend/` at the root,
> or split, or wrapped under a top-level package directory?"

## Decision drivers

- One small team — coordinated changes across backend + frontend are
  frequent (every API change touches both sides).
- Atomic PRs that touch both backend and frontend are valuable.
- Docs, ADRs, and rules should live next to the code they govern.
- CI and deploy pipelines should be discoverable in one place.
- We may add infra (`infra/`) and shared schemas later — they need
  somewhere obvious to live.

## Considered options

1. **Flat monorepo** — `backend/`, `frontend/`, `docs/`, `infra/` at
   the root.
2. **Wrapped monorepo** — `kaziro/backend/`, `kaziro/frontend/`.
3. **Polyrepo** — separate `kaziro-backend` and `kaziro-frontend` repos.

## Decision outcome

**Chosen option**: Flat monorepo.

`backend/`, `frontend/`, `docs/`, and (later) `infra/` sit directly under
the repo root. Project-wide configuration (`README.md`, `AGENTS.md`,
`.gitignore`, `docker-compose.yml`, `Makefile`, top-level CI workflows)
lives at the root.

### Positive consequences

- Atomic PRs that change an API endpoint and its frontend caller — a
  single commit, single review, single CI run.
- Docs and ADRs live next to code; `AGENTS.md` files in each workspace
  give agents (Cursor, Claude Code, humans) the right context for the
  files they're editing (see [ADR-0010](ADR-0010-agents-md-hierarchy.md)).
- One CI pipeline configures linting and testing for both stacks.
- Easy local dev — one `git clone` gives you everything.
- No `kaziro/` wrapper directory adds nothing — the repo name already
  *is* `kaziro`.

### Negative consequences

- Single repo can grow large; mitigated by per-workspace tooling
  (`backend/pyproject.toml`, `frontend/package.json`).
- CI must be smart enough to skip frontend jobs on backend-only PRs
  (path filters in GitHub Actions).
- Single `pre-commit` config has to handle both Python and JS — solvable
  with `lefthook` or per-folder hooks.

## Pros and cons of the options

### Option 1 — Flat monorepo

- **Pros**: Atomic cross-stack changes; one CI; docs co-located.
- **Cons**: Path-filtered CI required to keep CI fast.

### Option 2 — Wrapped monorepo (`kaziro/backend/`, `kaziro/frontend/`)

- **Pros**: Imports could be `from kaziro.backend...`.
- **Cons**: Adds a meaningless layer (the repo is already named
  `kaziro`); doesn't match existing code layout; requires rewriting all
  imports.

### Option 3 — Polyrepo

- **Pros**: Each stack is independently versionable.
- **Cons**: Cross-stack changes require two PRs and version coordination;
  duplicated CI tooling; harder onboarding; unnecessary friction for a
  small team.

## Links

- [ADR-0010: AGENTS.md hierarchy](ADR-0010-agents-md-hierarchy.md)
- [`AGENTS.md`](../../AGENTS.md)
- [`backend/AGENTS.md`](../../backend/AGENTS.md)
- [`frontend/AGENTS.md`](../../frontend/AGENTS.md)
