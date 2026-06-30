# Architecture Decision Records

ADRs capture architecturally significant decisions and their trade-offs.

| ID | Status | Title |
| --- | --- | --- |
| [ADR-0001](ADR-0001-agentic-framework-langgraph.md) | Accepted | Use LangGraph as the agentic framework |
| [ADR-0002](ADR-0002-database-postgres-pgvector.md) | Accepted | PostgreSQL + pgvector as the unified data store |
| [ADR-0003](ADR-0003-auth-supabase.md) | Accepted | Managed identity and storage services |
| [ADR-0004](ADR-0004-task-queue-celery-redis.md) | Accepted | Celery + Redis for asynchronous work |
| [ADR-0005](ADR-0005-web-scraping-firecrawl.md) | Accepted | Firecrawl for company website scraping |
| [ADR-0006](ADR-0006-evaluator-three-pass.md) | Accepted | Three-pass evaluator pipeline |
| [ADR-0007](ADR-0007-nextjs-react-frontend.md) | Accepted | Next.js and React for the frontend |
| [ADR-0008](ADR-0008-email-sending-mvp-draft-only.md) | Accepted | MVP generates documents only |
| [ADR-0009](ADR-0009-monorepo-layout.md) | Accepted | Flat monorepo layout |
| [ADR-0010](ADR-0010-agents-md-hierarchy.md) | Accepted | Layered AGENTS.md hierarchy |
| [ADR-0011](ADR-0011-default-open-models-nemotron.md) | Accepted | Use Nemotron as the default OpenRouter model family |
| [ADR-0012](ADR-0012-canonical-django-ninja-nextjs-architecture.md) | Accepted | Django Ninja and Next.js as the canonical architecture |

## Adding A New ADR

1. Pick the next number.
2. Copy `_template.md`.
3. Fill in the decision, context, consequences, and alternatives.
4. Add the new ADR to this index.
5. Link related architecture or reference docs.
