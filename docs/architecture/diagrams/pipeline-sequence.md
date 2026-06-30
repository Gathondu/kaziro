# Pipeline Sequence Diagram

**Status**: Active
**Last updated**: 2026-04-22
**Source**: Section 6.2 of [`Kaziro_Design_Document.pdf`](../../../Kaziro_Design_Document.pdf)
**Referenced from**: [`../02-agentic-pipeline.md`](../02-agentic-pipeline.md)

End-to-end sequence: from a scheduler tick to the moment a user sees a
ready-to-edit job application in their dashboard.

```mermaid
sequenceDiagram
  participant Sched as APScheduler / Celery beat
  participant API as Django Ninja
  participant Cel as Celery worker
  participant Fetch as Job Fetch Service
  participant Parse as Parser Agent
  participant Eval as Evaluator Agent (3-pass)
  participant Res as Research Agent
  participant Doc as Document Agent
  participant DB as PostgreSQL + pgvector
  participant WS as WebSocket hub
  participant Browser

  Sched->>Cel: cron tick (per user config)
  Cel->>Fetch: fetch_jobs_for_config(config_id)
  Fetch->>Fetch: call RapidAPI (JSearch)
  Fetch->>DB: insert raw_jobs (deduped on external_job_id)
  Fetch-->>Cel: list of new raw_job_ids

  loop for each raw_job
    Cel->>Parse: run_parser_agent(raw_job_id, payload)
    Parse->>Parse: parse → embed → persist
    Parse->>DB: insert job_postings
    Parse-->>Cel: ParserState (job_posting_id)
  end

  loop for each new job_posting
    Cel->>Eval: run_evaluator_agent(job_posting_id, user_id)
    Eval->>DB: load job + profile
    Eval->>Eval: pass1 draft (LLM_MODEL_EVALUATOR)
    Eval->>Eval: pass2 critic (LLM_MODEL_EVALUATOR)
    Eval->>Eval: pass3 judge (LLM_MODEL_EVALUATOR)
    Eval->>DB: insert job_evaluations
    Eval-->>Cel: classification + score
    Cel->>WS: publish evaluation_complete
    WS-->>Browser: toast (classification + score)

    alt classification is GOOD_FIT
      Cel->>Res: run_research_agent(job_posting_id)
      Res->>DB: check_cache (≤ 30 days?)

      alt cache miss
        Res->>Res: scrape company website (Firecrawl)
        Res->>Res: scrape job page (Firecrawl)
        Res->>Res: generate brief (LLM_MODEL_RESEARCH)
        Res->>DB: insert company_summaries
      end

      Res-->>Cel: done
      Cel->>Doc: run_document_agent(evaluation_id, user_id)
      Doc->>DB: load job + company brief + full profile + master CV
      Doc->>Doc: cv_tailor (LLM_MODEL_DOCUMENT)
      Doc->>Doc: cover_letter (LLM_MODEL_DOCUMENT)
      Doc->>Doc: quality_check (LLM_MODEL_DOCUMENT)
      Doc->>Doc: render PDFs
      Doc->>DB: insert application_docs
      Doc-->>Cel: done
      Cel->>WS: publish documents_ready
      WS-->>Browser: toast ("Open editor")
    else MAYBE or REJECT
      Note over Cel,Doc: Scheduled batch skips research and documents
    end
  end
```

## Key timing characteristics

| Stage             | Typical p50 latency       | Bounded by                              |
| ----------------- | ------------------------- | --------------------------------------- |
| Fetch (one user)  | 2 – 5 s                   | RapidAPI response                       |
| Parse (one job)   | 3 – 8 s                   | OpenRouter `LLM_MODEL_PARSER` call      |
| Evaluate (one job × one user) | 25 – 60 s     | 3 sequential `LLM_MODEL_EVALUATOR` calls |
| Research (one job)| 10 – 30 s (cache miss)    | 2 parallel Firecrawl scrapes + `LLM_MODEL_RESEARCH` |
| Document          | 30 – 60 s                 | 2 generative `LLM_MODEL_DOCUMENT` calls + quality check |
| **Full pipeline per job** | **~70 – 160 s**   | Dominated by evaluator + document       |

The orchestrator runs evaluator stage with `asyncio.Semaphore(3)` to cap LLM
concurrency. Research and document stages run sequentially per job to
preserve context.
