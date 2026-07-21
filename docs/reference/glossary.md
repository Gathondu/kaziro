# Glossary

**Status**: Living
**Last updated**: 2026-04-22

Domain terms and codes used across Kaziro. When in doubt, use the wording
defined here in code, docs, and UI copy.

## Domain entities

- **Job** — a single posting we ingest from an approved job-source provider.
  Stored in `raw_jobs` (raw payload) and `job_postings`
  (normalised, parsed schema with embedding).
- **Job posting** — the parsed, normalised representation of a job (title,
  company, location, description, requirements, embedding).
- **Job evaluation** — the per-user assessment of a job, produced by the
  Evaluator agent. Carries dimension scores, weighted total, classification,
  and rationale. Stored in `job_evaluations`.
- **Company summary** — the LLM-generated brief for a company (mission,
  values, recent news, tech stack), produced by the Research agent. Cached
  in `company_summaries` for 30 days.
- **Application** — the user-facing record of a single attempt to apply to
  a job. Wraps the generated documents and tracks status.
- **Application doc** — a single artefact (CV, cover letter) generated for
  an application. Stored in `application_docs`.
- **Application event** — an immutable audit record of state transitions
  for an application. Stored in `application_events`.
- **User profile** — the user-supplied profile data (target roles, skills,
  preferences) and the parsed master CV. Stored in `user_profiles`.
- **Job search config** — a user's saved search criteria (keywords,
  location, filters) used by the cron-driven fetch loop. Stored in
  `job_search_configs`.

## Pipeline stages

- **Fetch** — ingest jobs from approved provider configs based on a
  `job_search_config`.
- **Job source provider** — an external API source with public documentation,
  a generated config draft, smoke-test validation, and admin approval before
  activation.
- **Parser** — LLM-driven extraction of structured `JobPostingSchema`
  + embedding. See [`docs/design/agents/parser-agent.md`](../design/agents/parser-agent.md).
- **Evaluator** — three-pass scoring (Draft / Critic / Judge) producing a
  classification. See [`docs/design/agents/evaluator-agent.md`](../design/agents/evaluator-agent.md).
- **Research** — company-context gathering via Firecrawl + LLM brief.
  See [`docs/design/agents/research-agent.md`](../design/agents/research-agent.md).
- **Document** — CV + cover-letter generation per application.
  See [`docs/design/agents/document-agent.md`](../design/agents/document-agent.md).

## Classifications

The Evaluator returns one of:

- **`GOOD_FIT`** — strong match across required dimensions; pipeline
  proceeds to Research + Document. Threshold: weighted score ≥ 0.75
  with no dealbreakers.
- **`MAYBE`** — borderline; surfaced to the user but no documents
  generated. Threshold: 0.50 ≤ weighted score < 0.75 *or* a single
  dealbreaker that the user can override.
- **`REJECT`** — clear miss. Stored for audit; not surfaced by default.
  Threshold: weighted score < 0.50 *or* multiple dealbreakers.

## Application lifecycle

States in the `applications.status` enum (see
[`docs/architecture/diagrams/application-state-machine.md`](../architecture/diagrams/application-state-machine.md)):

- **`PENDING`** — created; pipeline working on it.
- **`READY`** — documents generated; awaiting user action.
- **`SENT`** — user marked as submitted.
- **`RESPONDED`** — employer reply recorded.
- **`REJECTED_BY_USER`** — user dismissed the application.
- **`REJECTED_BY_EMPLOYER`** — employer rejection recorded.
- **`OFFER`** — offer received.
- **`HIRED`** — closed-won.
- **`FAILED`** — pipeline error; user can retry or discard.

## Evaluation dimensions

The Evaluator scores each job along weighted dimensions
(see [`docs/design/agents/evaluator-agent.md`](../design/agents/evaluator-agent.md)):

| Dimension              | Default weight | Description                                                  |
| ---------------------- | -------------- | ------------------------------------------------------------ |
| `title_match`          | 0.20           | How closely the title matches the user's target roles.       |
| `skill_overlap`        | 0.25           | Required skills present in the user's master CV.             |
| `seniority_alignment`  | 0.15           | Match between job seniority and user's experience level.     |
| `location_compat`      | 0.15           | Location / remote-policy compatibility with user prefs.      |
| `company_signal`       | 0.10           | Company size, stage, or domain match (if user has prefs).    |
| `salary_signal`        | 0.10           | Salary band vs. user's stated minimum (when both present).   |
| `language_compat`      | 0.05           | Job-listing language matches a user-supported language.      |

## Roles and access tiers

- **User** — authenticated end user (job seeker).
- **Admin** — Kaziro staff with elevated access (audit, dashboards).
  Identified by `users.is_admin = true`.
- **Service** — backend / worker process, authenticated to Supabase via
  `SUPABASE_SERVICE_KEY`.

## Acronyms

- **ADR** — Architecture Decision Record. See [`../decisions/`](../decisions/).
- **ASGI** — Asynchronous Server Gateway Interface (Python web standard).
- **CV** — Curriculum Vitae. Used interchangeably with "résumé" in this
  codebase; UI copy says "CV".
- **DLQ** — Dead-Letter Queue.
- **ERD** — Entity-Relationship Diagram.
- **HITL** — Human-In-The-Loop.
- **HNSW** — Hierarchical Navigable Small World (pgvector index type).
- **IVFFlat** — Inverted File with Flat compression (pgvector index type).
- **JTBD** — Jobs To Be Done (product framing).
- **LLM** — Large Language Model.
- **MADR** — Markdown Architecture Decision Record (template format).
- **OTel** — OpenTelemetry.
- **PII** — Personally Identifiable Information.
- **RLS** — Row-Level Security (Postgres feature).
- **RPS** — Requests Per Second.
- **SLA** — Service-Level Agreement.
- **SLO** — Service-Level Objective.
- **TTI** — Time To Interactive (web perf metric).
- **TTL** — Time To Live (cache).
- **VCR** — `vcrpy` — HTTP record/replay library used for LLM tests.
- **WS** — WebSocket.

## Internal jargon

- **Agent (Kaziro)** — a LangGraph workflow under
  [`backend/apps/pipeline/`](../../backend/apps/pipeline/). Not to be confused with
  "AI agents" generically.
- **Pipeline** — the chain `Fetch → Parser → Evaluator → Research →
  Document` orchestrated by `tasks.py`.
- **Pipeline summary** — the structured contract returned by the
  orchestrator, recording per-stage outcomes for logging and the UI.
  See [`docs/design/agents/pipeline-orchestrator.md`](../design/agents/pipeline-orchestrator.md).
- **Master CV** — the canonical, user-uploaded CV used as ground truth
  for tailoring. The Document agent must never invent facts not present
  in the master CV.
- **Tailored CV** — the per-job derivative of the master CV produced by
  the Document agent.
- **Cassette** — a recorded HTTP interaction file used by VCR.py in
  tests.
