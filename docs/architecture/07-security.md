# Security

**Status**: Active
**Last updated**: 2026-04-22
**Source**: Section 10 of [`Kaziro_Design_Document.pdf`](../../Kaziro_Design_Document.pdf)
**Related ADRs**: [ADR-0003](../decisions/ADR-0003-auth-supabase.md)

## 1. Authentication & authorisation

### 1.1 Authentication

- All API endpoints (except `/auth/*` and `/health*`) are protected by JWT
  bearer auth.
- Tokens are issued by **Supabase Auth** (RS256, 1-hour TTL by default).
- Validation happens in `get_current_user` dependency:
  - Verify signature against Supabase JWKS (cached).
  - Verify `aud` claim matches `authenticated`.
  - Verify `exp` not in the past.
  - Load the corresponding `users` row.
- Refresh tokens are managed entirely by the Supabase JS client on the
  frontend.

### 1.2 Authorisation

- **Tenant isolation**: every user-scoped repository call **must** filter by
  `user_id`. The repository layer enforces this; routes pass
  `current_user.id` rather than trusting a body parameter.
- **Admin routes**: depend on `require_admin_role` which inspects the JWT
  `role` claim. Admin role is set in Supabase, never derivable from API
  input.
- **No user-supplied `user_id`**: routes ignore any `user_id` field in the
  request body and always use `current_user.id`.

### 1.3 Row-Level Security (RLS)

RLS is enabled on every Supabase table. The application-layer scoping is the
**second layer** of defence — even if a route forgets to scope, RLS prevents
cross-tenant reads.

```sql
ALTER TABLE applications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users read own applications"
  ON applications FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "users write own applications"
  ON applications FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);
```

- Application connections use the **anon key + JWT** — RLS applies.
- Migrations and Celery workers use the **service-role key** — RLS bypassed
  (necessary for fan-out across tenants).
- **Never disable RLS** on any table, including for debugging. Use the
  service-role key when you legitimately need to bypass it.

## 2. Secrets management

- All API keys (`OPENROUTER_API_KEY`, `RAPIDAPI_KEY`, `FIRECRAWL_API_KEY`,
  `SUPABASE_SERVICE_KEY`, `SECRET_KEY`) live in environment variables only.
- **Never** stored in the database, source code, or commit history.
- Local dev: `.env` files (git-ignored). Templated by `.env.example`.
- Production: Kubernetes `Secret` objects mounted as env vars; rotated via
  the secrets manager (e.g., Vault / AWS Secrets Manager) — see
  [`08-deployment.md`](08-deployment.md#secrets-management).
- Pre-commit hook (`detect-secrets`) scans every commit for accidental
  inclusions.

## 3. Data privacy

- **Encryption at rest**: PostgreSQL data encrypted at rest by Supabase.
  Supabase Storage objects are encrypted by the storage provider.
- **Encryption in transit**: TLS 1.2+ everywhere — between browser and
  API, between API and DB, between API and external services.
- **Minimal data in prompts**: agents construct LLM prompts from the
  smallest profile slice required (no email, no full address, no DOB).
- **Storage access**: Supabase Storage buckets are **private by default**.
  Files are accessed via short-lived signed URLs (TTL: 1 hour), generated on
  demand by the API for the owning user only.
- **Right to erasure**: `DELETE /api/v1/profile/account` cascades:
  - Soft-delete `users.is_active = false`.
  - Hard-delete or anonymise associated rows in `user_profiles`,
    `job_evaluations`, `applications`, `application_docs`,
    `application_events`.
  - Delete all Storage objects under `cv/{user_id}/` and
    `documents/{user_id}/`.
  - The deletion task runs asynchronously via Celery and emits a
    `data_deletion_complete` event when done.

## 4. Input validation & injection prevention

- **Pydantic v2** validates every request body, query parameter, and
  external payload (RapidAPI, Firecrawl, scraped content) before any
  processing.
- **SQL injection**: ORM only — `select()` with bound parameters. **Never**
  hand-construct SQL strings. The rule is enforced both by code review and
  by the `S608` ruff check.
- **HTML sanitisation**: scraped web content is stripped of HTML, length-
  capped (8 KB per source), and never rendered as HTML in the UI — only as
  plain text.
- **LLM prompt injection mitigation**:
  - Scraped content is wrapped in clearly-fenced sections (`=== COMPANY
    WEBSITE ===`) so the model treats it as data not instructions.
  - System prompts include "IMPORTANT RULES" sections forbidding
    instruction-following from quoted content.
  - Outputs are JSON-schema validated before being persisted.
- **File upload validation**: CV uploads are restricted by:
  - `Content-Type ∈ {application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document}`
  - Size cap: 5 MB.
  - Server-side content sniff via `python-magic` to confirm declared type.
  - Filename sanitisation (UUID rename) before storage.

## 5. Network security

- API and frontend served over HTTPS only. HSTS preload enabled in
  production.
- CORS allowlist explicit per environment (`https://app.kaziro.io` only in
  prod). No wildcard origins.
- WebSocket connections require token-in-query auth and are rate-limited
  per IP.
- Internal services (Celery workers, Redis) reachable only inside the
  cluster network — Kubernetes `NetworkPolicy` restricts ingress.
- `/metrics` is reachable only from the Prometheus scrape pod via a
  dedicated `NetworkPolicy`.

## 6. Rate limiting & abuse prevention

- 100 requests/min per user via Redis sliding window middleware.
- Login endpoint: stricter — 10 attempts/5 min per IP and per email.
- Account creation: 3/hour per IP (CAPTCHA after 1 in production).
- Pipeline trigger endpoints (`POST /jobs/{id}/trigger-evaluation`) capped
  at 10/hour per user to prevent LLM cost runaway.
- Celery task queues use per-user task counters; a user's pipeline tasks are
  rate-limited if they exceed concurrency thresholds.

## 7. Auditing

- Every state change to `applications.status` writes an `application_events`
  row — immutable history.
- Admin-only routes log `event_type=admin_action` to the central log store
  with the admin user's email and the affected resource.
- All authentication failures (bad password, expired JWT, role mismatch)
  log at WARNING with `user_id` (when known) and request IP.

## 8. Dependency security

- `pip-audit` (Python) and `pnpm audit` (frontend) run in CI. Critical
  vulnerabilities fail the build.
- Renovate / Dependabot opens weekly PRs for minor/patch upgrades.
- Major upgrades reviewed manually with a changelog scan and a one-off
  smoke test.
- LLM-generated code is **never** auto-merged — every PR requires a human
  reviewer.

## 9. Incident response

- Pager rotation owns CRITICAL alerts (see
  [`06-observability.md`](06-observability.md#4-alerting-rules)).
- The runbook for each alert lives in `docs/runbooks/<alert>.md` and
  includes: symptoms, immediate mitigations, root-cause investigation
  pointers, and rollback steps.
- Post-incident review within 5 working days, written up in
  `docs/incidents/YYYY-MM-DD-<slug>.md`.

## 10. Security checklist for a new endpoint

- [ ] Has `Depends(get_current_user)` (and `require_admin_role` if needed).
- [ ] Uses `current_user.id` — never trusts body `user_id`.
- [ ] Repository call scopes by `user_id`.
- [ ] Pydantic schema validates every input field.
- [ ] No raw SQL.
- [ ] No secrets logged.
- [ ] Pagination capped (`limit ≤ 100`).
- [ ] Rate-limit reasonable for the cost (e.g., LLM-triggering routes
      capped tighter).
- [ ] Returns structured `{ data, error }` envelope.
- [ ] Tests cover 401, 403, 404, 422 paths.
