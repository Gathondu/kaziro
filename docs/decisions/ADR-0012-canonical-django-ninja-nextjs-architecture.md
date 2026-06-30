# ADR-0012: Django Ninja And Next.js As The Canonical Application Architecture

**Status**: Accepted
**Date**: 2026-06-29
**Tags**: backend, frontend, architecture

## Context

Kaziro's primary application folders are `backend/` and `frontend/`. The
backend owns API, auth, persistence, workers, and agent orchestration. The
frontend owns the user-facing web application.

## Decision

Use Django with Django Ninja for the backend and Next.js App Router with React
for the frontend.

The canonical folder layout is:

```text
kaziro/
├── backend/
├── frontend/
├── docs/
├── infra/
└── scripts/
```

## Consequences

- Backend APIs are mounted under `/api/v1`.
- API responses preserve the `{ data, meta, error }` envelope.
- Celery workers use `config.celery:app`.
- Frontend API clients live under `frontend/src/lib/api/`.
- Documentation and automation should refer only to `backend/` and `frontend/`.
