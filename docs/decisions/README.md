# Architecture Decision Records (ADRs)

**Format**: [MADR](https://adr.github.io/madr/) (Markdown Architecture Decision Records)
**Template**: [`_template.md`](_template.md)

ADRs capture architecturally significant decisions — the **why** behind a
choice — so future contributors can understand what trade-offs were
weighed, what alternatives were considered, and what consequences accepted.

## Index

| ID                                                     | Status   | Title                                                            |
| ------------------------------------------------------ | -------- | ---------------------------------------------------------------- |
| [ADR-0001](ADR-0001-agentic-framework-langgraph.md)    | Accepted | Use LangGraph as the agentic framework                           |
| [ADR-0002](ADR-0002-database-postgres-pgvector.md)     | Accepted | PostgreSQL + pgvector as the unified data store                  |
| [ADR-0003](ADR-0003-auth-supabase.md)                  | Accepted | Supabase for Auth, managed Postgres, and Storage                 |
| [ADR-0004](ADR-0004-task-queue-celery-redis.md)        | Accepted | Celery + Redis for the asynchronous task queue                   |
| [ADR-0005](ADR-0005-web-scraping-firecrawl.md)         | Accepted | Firecrawl for company-website scraping                           |
| [ADR-0006](ADR-0006-evaluator-three-pass.md)           | Accepted | Three-pass evaluator pipeline (draft / critic / judge)           |
| [ADR-0007](ADR-0007-frontend-sveltekit.md)             | Accepted | SvelteKit for the frontend                                       |
| [ADR-0008](ADR-0008-email-sending-mvp-draft-only.md)   | Accepted | MVP generates documents only — no automatic email sending        |
| [ADR-0009](ADR-0009-monorepo-layout.md)                | Accepted | Flat monorepo layout: `backend/`, `frontend/`, `docs/` at root   |
| [ADR-0010](ADR-0010-agents-md-hierarchy.md)            | Accepted | Layered AGENTS.md hierarchy across the monorepo                  |

## Adding a new ADR

1. Pick the next number (`ADR-NNNN`).
2. Copy [`_template.md`](_template.md) to `ADR-NNNN-short-kebab-title.md`.
3. Fill in every section. Keep ≤ 2 pages — link to detailed docs for
   anything longer.
4. Add a row to the Index above.
5. Cross-link from the relevant architecture / design docs to the new ADR.
6. Commit alongside the change it documents (or in the PR that introduces
   the change).

## ADR statuses

- **Proposed** — under discussion.
- **Accepted** — agreed and in effect.
- **Superseded by ADR-NNNN** — historical, replaced by a later decision.
- **Deprecated** — no longer in effect; not yet replaced.

Never delete or rewrite an accepted ADR — supersede it with a new one.
