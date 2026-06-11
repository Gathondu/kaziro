# ADR-0012: Parallel migration to Django Ninja and Next.js TypeScript

**Status**: Accepted
**Date**: 2026-06-11
**Deciders**: Founding engineering team
**Tags**: backend, frontend, migration

## Context and problem statement

Kaziro is growing beyond the original FastAPI + SvelteKit MVP stack. The
next architecture should use Django for a broader backend foundation and
React for a larger frontend state-management ecosystem, while avoiding a
big-bang rewrite.

## Decision drivers

- Keep the current production path working while the new stack is built.
- Preserve `/api/v1` compatibility during route-by-route migration.
- Preserve UUID user identities for future data migration.
- Move the frontend to React without losing Tailwind + DaisyUI conventions.
- Keep the agentic pipeline on Celery + LangGraph.

## Considered options

1. Parallel Django Ninja + Next.js scaffold.
2. Immediate in-place rewrite of `backend/` and `frontend/`.
3. Branch-only rewrite with a later merge.
4. Django REST Framework instead of Django Ninja.

## Decision outcome

**Chosen option**: parallel Django Ninja + Next.js scaffold.

The repo now contains `backend-django/` and `frontend-next/` beside the
current working stack. Django Ninja is the API layer because its typed route
functions and schema style are closer to the current FastAPI implementation
than DRF. Next.js uses TypeScript, Tailwind, DaisyUI, TanStack Query, and
Zustand.

### Positive consequences

- The existing FastAPI/SvelteKit app remains usable during migration.
- API parity can be tested one resource at a time.
- Future Django auth and storage migration can preserve user UUIDs.
- React route groups can mirror the existing app structure.

### Negative consequences

- Two stacks temporarily increase maintenance overhead.
- Shared API contracts must be carefully tested to avoid drift.
- Supabase Auth and storage removal is deferred to later slices.

## Links

- [`backend-django/AGENTS.md`](../../backend-django/AGENTS.md)
- [`frontend-next/AGENTS.md`](../../frontend-next/AGENTS.md)
- [`docs/architecture/01-system-overview.md`](../architecture/01-system-overview.md)
