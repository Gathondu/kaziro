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
  participant API as FastAPI
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
    Eval->>Eval: pass1 draft (gpt-4o)
    Eval->>Eval: pass2 critic (gpt-4o)
    Eval->>Eval: pass3 judge (gpt-4o)
    Eval->>DB: insert job_evaluations
    Eval-->>Cel: classification + score
    Cel->>WS: publish evaluation_complete
    WS-->>Browser: toast (classification + score)

    alt classification in (GOOD_FIT, MAYBE)
      Cel->>Res: run_research_agent(job_posting_id)
      Res->>DB: check_cache (≤ 30 days?)

      alt cache miss
        Res->>Res: scrape company website (Firecrawl)
        Res->>Res: scrape job page (Firecrawl)
        Res->>Res: generate brief (gpt-4o)
        Res->>DB: insert company_summaries
      end

      Res-->>Cel: done
      Cel->>Doc: run_document_agent(evaluation_id, user_id)
      Doc->>DB: load job + company brief + profile + raw CV
      Doc->>Doc: cv_tailor (gpt-4o)
      Doc->>Doc: cover_letter (gpt-4o)
      Doc->>Doc: quality_check (gpt-4o)
      Doc->>Doc: render PDFs
      Doc->>DB: insert application_docs
      Doc-->>Cel: done
      Cel->>WS: publish documents_ready
      WS-->>Browser: toast ("Open editor")
    end
  end
```

## Key timing characteristics

| Stage             | Typical p50 latency       | Bounded by                              |
| ----------------- | ------------------------- | --------------------------------------- |
| Fetch (one user)  | 2 – 5 s                   | RapidAPI response                       |
| Parse (one job)   | 3 – 8 s                   | OpenRouter `openai/gpt-4o-mini` call    |
| Evaluate (one job × one user) | 25 – 60 s     | 3 sequential gpt-4o calls               |
| Research (one job)| 10 – 30 s (cache miss)    | 2 parallel Firecrawl scrapes + gpt-4o   |
| Document          | 30 – 60 s                 | 2 generative gpt-4o calls + quality check |
| **Full pipeline per job** | **~70 – 160 s**   | Dominated by evaluator + document       |

The orchestrator runs evaluator stage with `asyncio.Semaphore(3)` to cap LLM
concurrency. Research and document stages run sequentially per job to
preserve context.
