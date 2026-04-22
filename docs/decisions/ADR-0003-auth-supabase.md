# ADR-0003: Supabase for Auth, managed Postgres, and Storage

**Status**: Accepted
**Date**: 2026-04-22
**Deciders**: Founding engineering team
**Tags**: backend, infra, security

## Context and problem statement

Kaziro is a multi-tenant SaaS that needs:

- User authentication (email + password, social login, magic links).
- A managed PostgreSQL database (with pgvector — see
  [ADR-0002](ADR-0002-database-postgres-pgvector.md)).
- Object storage for user CV uploads, generated PDFs, profile photos.
- Multi-tenant data isolation enforced at the data layer.

Building any of these from scratch is weeks of work and ongoing
maintenance. The MVP team is small (1-2 engineers).

> "How do we get auth + Postgres + storage with the smallest operational
> burden, while keeping the door open to migrate later?"

## Decision drivers

- Minimise time-to-MVP.
- One vendor for auth + DB + storage to keep the surface area small.
- DB-layer multi-tenant isolation (RLS).
- Open-source / portable so we can self-host if needed.
- Free / cheap at MVP traffic.

## Considered options

1. **Supabase** — managed Postgres + GoTrue auth + S3-compatible storage.
2. **AWS** (Cognito + RDS Postgres + S3).
3. **Firebase** (Firebase Auth + Firestore + Cloud Storage).
4. **Self-hosted** Postgres + Keycloak + MinIO.

## Decision outcome

**Chosen option**: Supabase.

It bundles Postgres (with pgvector), GoTrue (JWT-based auth), and an
S3-compatible storage API behind a single managed service. RLS is
first-class and integrates with the auth-issued JWT (`auth.uid()` in SQL
policies). The DB is plain Postgres — if we leave Supabase, we can take
the dump anywhere.

### Positive consequences

- Auth, DB, and storage in days instead of months.
- RLS policies enforce multi-tenant isolation at the DB layer; even an
  app bug cannot leak data across users.
- JWT verification on the API is a one-line dependency.
- Generous free tier; predictable pricing as we grow.
- 100% portable — Postgres dump + S3-compatible blob copy + JWT verify
  function = drop-in replacement on AWS/Fly/Render.

### Negative consequences

- Supabase outages directly degrade Kaziro (mitigated by status-page
  alerting and the portability noted above).
- Some advanced Postgres tuning is gated behind paid tiers.
- GoTrue email-template customisation is limited compared to dedicated
  email providers (Resend / Postmark) — we can hybridise if needed.

## Pros and cons of the options

### Option 1 — Supabase

- **Pros**: All-in-one; pgvector available; RLS first-class; portable.
- **Cons**: Single vendor risk; advanced tuning gated.

### Option 2 — AWS (Cognito + RDS + S3)

- **Pros**: Industry standard; mature; granular control.
- **Cons**: Three services to wire; Cognito is notoriously developer-hostile;
  weeks of setup work.

### Option 3 — Firebase

- **Pros**: Excellent DX for mobile/web; auth is great.
- **Cons**: Firestore is NoSQL — incompatible with our relational + vector
  design; vendor lock-in is real (no easy export).

### Option 4 — Self-hosted (Postgres + Keycloak + MinIO)

- **Pros**: Maximum control; zero vendor cost.
- **Cons**: 100% of the ops burden falls on a 1-2 person team. Not viable
  for MVP.

## Links

- [ADR-0002: Postgres + pgvector](ADR-0002-database-postgres-pgvector.md)
- [`docs/architecture/07-security.md`](../architecture/07-security.md)
- [Supabase docs](https://supabase.com/docs)
