# Kaziro - 5-10 Minute Presentation (Screen Version)

## Slide 1 - Title

- **Kaziro**: AI-powered job recommendation and application pipeline
- Presenter: [Your Name]
- Focus: design, key decisions, and end-to-end flow

---

## Slide 2 - Problem and Goal

- Job searching is noisy and repetitive.
- Generic applications reduce fit and response rate.
- Teams need speed **and** control, not black-box automation.
- Kaziro goal: fetch -> evaluate -> tailor -> help user apply faster.

---

## Slide 3 - System Design (High Level)

```mermaid
flowchart LR
  user[User]
  fe[Frontend_SvelteKit]
  api[FastAPI_API]
  ws[WS_Notifications]
  celery[Celery_Workers]
  agents[Agent_Pipeline]
  db[(PostgreSQL_pgvector)]
  redis[(Redis)]
  rapidapi[RapidAPI_Providers]
  firecrawl[Firecrawl]
  openrouter[OpenRouter_Models]
  storage[Supabase_Storage]

  user --> fe
  fe --> api
  fe --> ws
  api --> db
  api --> redis
  api --> celery
  celery --> agents
  agents --> db
  agents --> redis
  agents --> rapidapi
  agents --> firecrawl
  agents --> openrouter
  agents --> storage
  ws --> fe
```

---

## Slide 4 - Why This Design

- **LangGraph + orchestrator** for explicit staged AI flow.
- **Celery + Redis** for retries, scheduling, and async reliability.
- **PostgreSQL + pgvector** for transactional + semantic data in one place.
- **SvelteKit + TanStack Query** for fast, consistent user experience.
- **Structured observability** for traceability and operations.

---

## Slide 5 - Decision Map

```mermaid
flowchart TD
  problem[Need_reliable_agentic_app_flow]
  d1[LangGraph_for_stateful_multi_pass_agents]
  d2[Celery_Redis_for_async_orchestration]
  d3[Postgres_pgvector_for_data_and_similarity]
  d4[SvelteKit_TanStack_for_responsive_UI]
  d5[Structured_logging_and_metrics]
  outcome[Auditable_scalable_user_visible_pipeline]

  problem --> d1
  problem --> d2
  problem --> d3
  problem --> d4
  problem --> d5
  d1 --> outcome
  d2 --> outcome
  d3 --> outcome
  d4 --> outcome
  d5 --> outcome
```

---

## Slide 6 - End-to-End Pipeline

```mermaid
flowchart TD
  start[Pipeline_Start]
  fetch[Fetch_Jobs]
  parse[Parse_and_Persist_Postings]
  eval[Evaluate_Fit]
  classificationGate{"Classification"}
  research[Research_Company_Context]
  docs[Generate_Tailored_Documents]
  maybePath[MAYBE_Research_on_manual_single_job]
  rejectPath[Reject_or_Stop]
  notify[Publish_Notifications]
  userValue[User_Sees_Updates_and_Acts]

  start --> fetch --> parse --> eval --> classificationGate
  classificationGate -->|"GOOD_FIT"| research --> docs --> notify --> userValue
  classificationGate -->|"MAYBE"| maybePath --> notify --> userValue
  classificationGate -->|"REJECT"| rejectPath --> notify --> userValue
```

---

## Slide 7 - Runtime Sequence (Manual Trigger)

```mermaid
sequenceDiagram
  participant User
  participant Frontend
  participant API
  participant Celery
  participant Orchestrator
  participant Agents
  participant Redis
  participant WS

  User->>Frontend: Click "Re-run evaluation"
  Frontend->>API: POST /api/v1/jobs/{id}/trigger-evaluation
  API->>Celery: Enqueue single-job task
  Celery->>Orchestrator: run_pipeline_for_single_job
  Orchestrator->>Agents: evaluator_agent
  Agents-->>Orchestrator: classification + score
  Orchestrator->>Redis: publish evaluation_complete
  Redis->>WS: user:{user_id}:notifications
  WS-->>Frontend: evaluation_complete event
  Frontend-->>User: Toast + refreshed state
```

---

## Slide 8 - Current-State Updates

- CV upload route: `POST /profile/cv`
- Jobs support:
  - `POST /jobs/{id}/mark-not-interested`
  - `POST /jobs/{id}/regenerate-documents`
- Regeneration supports `part = cv | cover_letter | full`
- Single-job runtime branch:
  - `GOOD_FIT`: research + documents
  - `MAYBE`: research only
  - `REJECT`: stop after evaluation
- Notifications route: `WS /api/v1/ws/notifications?token=...`

---

## Slide 9 - Value and Close

- Faster pipeline from discovery to application draft
- Better fit quality through multi-pass evaluation
- Human control preserved at final decision/edit/send steps
- Architecture is production-ready and extensible for next phases

---

## Slide 10 - Q&A

- Scaling and throughput?
- Evaluation quality and calibration?
- Deployment and reliability roadmap?
- Product expansion opportunities?

