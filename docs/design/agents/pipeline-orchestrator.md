# Pipeline Orchestrator

**Status**: Active
**Last updated**: 2026-04-22
**Source**: Sections 3.1 and 6.2 of [`Kaziro_Design_Document.pdf`](../../../Kaziro_Design_Document.pdf)
**Code**: [`backend/apps/pipeline/tasks.py`](../../../backend/apps/pipeline/tasks.py)
**Related ADR**: [ADR-0004](../../decisions/ADR-0004-task-queue-celery-redis.md)

## Purpose

The orchestrator chains the four LangGraph agents into the end-to-end
pipeline. **It is the only layer allowed to call multiple agents** —
individual agents must never invoke each other.

```
fetch → parse → evaluate (per user) → research → document
```

## Public entry points

| Function                                                | Caller                                                                 |
| ------------------------------------------------------- | ---------------------------------------------------------------------- |
| `run_full_pipeline_for_config(config_id, user_id)`      | Celery beat — periodic per-user pipeline run                           |
| `run_pipeline_for_single_job(job_posting_id, user_id)`  | API trigger / admin tool — single-job re-run from `/jobs/{id}/trigger-evaluation` |

## Stage functions (private)

| Function                                                  | Stage     | Returns                                                  |
| --------------------------------------------------------- | --------- | -------------------------------------------------------- |
| `run_fetch_and_parse(config_id, user_id)`                 | 0–1       | List of newly parsed `job_posting_id`s                  |
| `run_evaluation_for_user(job_posting_id, user_id)`        | 2         | `job_evaluation_id` if `GOOD_FIT`/`MAYBE`, else `None`   |
| `run_research_stage(job_posting_id, user_id)`             | 3         | `bool` (success/failure)                                 |
| `run_document_stage(job_evaluation_id, user_id)`          | 4         | `bool` (success/failure)                                 |

## Concurrency

Stage 2 (evaluation) is the only fan-out point per pipeline run. It uses
`asyncio.Semaphore(3)` to cap concurrent LLM calls per pipeline:

```python
semaphore = asyncio.Semaphore(3)

async def evaluate_with_sem(job_id: str) -> tuple[str, str | None]:
    async with semaphore:
        ev_id = await run_evaluation_for_user(job_id, user_id)
        return job_id, ev_id

eval_results = await asyncio.gather(*[evaluate_with_sem(jid) for jid in parsed_ids])
```

Stages 3 and 4 run **sequentially per job** to keep agent context clean
and avoid Firecrawl / LLM rate limits across many parallel scrapes.

## Error isolation

- Each user's pipeline runs in its own Celery task. Per-user exceptions
  cannot propagate to other tenants.
- Inside a pipeline, every stage call is wrapped in `try/except`. The
  exception is logged with full context (`stage`, `user_id`,
  `job_posting_id`, etc.) and the pipeline continues to the next item or
  the next stage.
- Downstream stages run only if the upstream returned a usable result
  (e.g., research only runs for jobs whose evaluation actually completed).

## Notifications

After Stage 2 (evaluation) and Stage 4 (document generation), the
orchestrator publishes a notification to the user's Redis pub/sub channel
via `services/notifications.notify_user`:

```python
await notify_user(user_id, {
    "type": "evaluation_complete",
    "job_posting_id": job_posting_id,
    "classification": "GOOD_FIT",
    "score": 7.8,
})

await notify_user(user_id, {
    "type": "documents_ready",
    "job_posting_id": job_posting_id,
    "job_evaluation_id": evaluation_id,
    "application_doc_id": application_doc_id,
    "quality_passed": True,
})
```

The WebSocket hub forwards these to the connected browser, which renders
toasts and updates the dashboard counters. Future events
(`fetch_complete`, `research_complete`) are emitted similarly when added.

## Pipeline summary contract

`run_full_pipeline_for_config` returns:

```python
{
    "config_id": str,
    "user_id": str,
    "started_at": ISO-8601,
    "completed_at": ISO-8601,
    "jobs_fetched": int,
    "jobs_parsed": int,
    "evaluations_good_fit": int,
    "evaluations_maybe": int,
    "evaluations_rejected": int,
    "documents_generated": int,
    "errors": list[str],
}
```

This payload is logged at INFO and exposed by `GET /admin/pipeline-status`
for the operator dashboard.

## Where it sits in the call stack

```
backend/tasks/pipeline_tasks.py
└─ Celery task: run_pipeline_for_user_config(config_id, user_id)
   └─ pipeline_orchestrator.run_full_pipeline_for_config(...)
      ├─ run_fetch_and_parse(...) → services/job_fetcher.fetch_jobs_for_config(...)
      │                            → parser_agent.run_parser_agent(...)
      ├─ run_evaluation_for_user(...) → evaluator_agent.run_evaluator_agent(...)
      │                                → services/notifications.notify_user(...)
      ├─ run_research_stage(...) → research_agent.run_research_agent(...)
      └─ run_document_stage(...) → document_agent.run_document_agent(...)
                                  → services/notifications.notify_user(...)
```

## Logging — orchestrator-specific events

| Event                                  | Fields                                                  |
| -------------------------------------- | ------------------------------------------------------- |
| `pipeline.fetch_start`                 | `config_id`, `user_id`                                  |
| `pipeline.fetched`                     | `count`                                                 |
| `pipeline.no_jobs_fetched`             |                                                         |
| `pipeline.duplicate_skipped`           | `external_job_id`                                       |
| `pipeline.parser_exception`            | `error`, `raw_job_id`                                   |
| `pipeline.parse_complete`              | `parsed_count`                                          |
| `pipeline.evaluation_start`            | `job_posting_id`, `user_id`                             |
| `pipeline.evaluation_complete`         | `classification`, `score`                               |
| `pipeline.evaluation_error`            | `error`                                                 |
| `pipeline.evaluation_exception`        | `error`                                                 |
| `pipeline.research_start`              | `job_posting_id`                                        |
| `pipeline.research_complete`           | `skipped`                                               |
| `pipeline.research_error`              | `error`                                                 |
| `pipeline.research_exception`          | `error`                                                 |
| `pipeline.document_start`              | `job_evaluation_id`                                     |
| `pipeline.document_complete`           | `quality_passed`                                        |
| `pipeline.document_error`              | `error`                                                 |
| `pipeline.document_exception`          | `error`                                                 |
| `pipeline.full_start`                  | `config_id`, `user_id`                                  |
| `pipeline.full_complete`               | full summary except `errors`                            |
| `pipeline.no_new_jobs`                 |                                                         |

Every log call binds at minimum `user_id` and `stage`, plus the relevant
ID for the stage.

## Where to extend

| Extension                              | Touch                                                                          |
| -------------------------------------- | ------------------------------------------------------------------------------ |
| Add a new pipeline stage               | New stage function in this file; chain it from `run_full_pipeline_for_config`  |
| Skip stages based on user preferences  | Read flags from `user_profiles` or `job_search_configs` at orchestrator level  |
| Increase parallelism                   | Bump `asyncio.Semaphore` value; watch OpenRouter quota / cost                |
| Add per-stage notifications            | Add `notify_user(...)` calls in the relevant stage function                    |
| Expose metrics per stage               | Add Prometheus histograms in a domain-owned metrics module; wrap stage with `.time()` |
