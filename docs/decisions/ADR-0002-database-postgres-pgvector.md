# ADR-0002: PostgreSQL + pgvector as the unified data store

**Status**: Accepted
**Date**: 2026-04-22
**Deciders**: Founding engineering team
**Tags**: backend, data

## Context and problem statement

Kaziro stores both structured relational data (users, jobs, evaluations,
applications, audit events) and unstructured/semi-structured data (job
embeddings for similarity search, parsed JSON blobs). We need:

- Strong relational guarantees (FKs, transactions) for the multi-tenant
  domain.
- Vector similarity search for "find similar jobs" and de-duplication.
- Row-Level Security (RLS) for multi-tenant isolation.
- Mature tooling for migrations, backups, monitoring.

> "Should we use one store, or split structured + vector data across two?"

## Decision drivers

- Operational simplicity — one DB to run, monitor, back up, and migrate.
- Strong consistency between structured and vector data (a `job_postings`
  row and its `embedding` should be transactionally written together).
- Multi-tenant isolation enforceable at the DB layer.
- Acceptable similarity-search performance at MVP scale (≤ 100k vectors).
- Team SQL fluency.

## Considered options

1. **PostgreSQL + pgvector (single store)**.
2. **PostgreSQL for relational + Pinecone (or Weaviate) for vectors**.
3. **MongoDB Atlas with Vector Search** (single store).
4. **PostgreSQL + Qdrant** (separate vector DB).

## Decision outcome

**Chosen option**: PostgreSQL + pgvector.

Postgres covers the relational domain natively. The `pgvector` extension
adds a `VECTOR(dim)` type and HNSW / IVFFlat indexes — sufficient for
MVP-scale similarity search. Supabase ([ADR-0003](ADR-0003-auth-supabase.md))
exposes both as a managed service, so we get TLS, backups, RLS, and
auth-integration for free.

### Positive consequences

- Single source of truth — one DB, one migration story (Alembic).
- Transactional writes across structured rows and vectors.
- RLS policies enforce per-user isolation at the DB layer (no app-level
  bug can leak another user's data).
- Free with Supabase tier; trivial to host elsewhere if we leave.

### Negative consequences

- pgvector throughput tops out before dedicated vector DBs (Pinecone, Qdrant)
  at very large scale.
- The current 2048-dimensional embedding model exceeds pgvector's ANN index
  limit for the `vector` type, so MVP semantic search uses exact scans until
  we adopt half-precision expression indexes, reduced dimensions, or a
  dedicated vector store.
- Index build time is non-trivial for ANN indexes on large tables — needs care
  during migrations.

## Pros and cons of the options

### Option 1 — Postgres + pgvector

- **Pros**: One store, transactional, RLS, mature ops, Supabase-managed.
- **Cons**: Vector throughput ceiling at very large scale.

### Option 2 — Postgres + Pinecone

- **Pros**: Best-in-class vector search performance.
- **Cons**: Two systems to keep in sync; cross-store transactions are
  impossible; extra cost; vendor lock-in on the vector side.

### Option 3 — MongoDB Atlas + Vector Search

- **Pros**: Single store; managed.
- **Cons**: We lose strict relational guarantees; team SQL fluency is
  stronger; RLS-equivalent is weaker.

### Option 4 — Postgres + Qdrant

- **Pros**: Open-source vector DB; strong filtering.
- **Cons**: Same two-system overhead as Pinecone, without managed-service
  upside.

## Links

- [`docs/architecture/03-data-model.md`](../architecture/03-data-model.md)
- [ADR-0003: Supabase](ADR-0003-auth-supabase.md)
- [pgvector](https://github.com/pgvector/pgvector)
