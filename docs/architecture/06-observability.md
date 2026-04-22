# Observability

**Status**: Active
**Last updated**: 2026-04-22
**Source**: Section 8 of [`Kaziro_Design_Document.pdf`](../../Kaziro_Design_Document.pdf) and [`.cursor/rules/006-observability.mdc`](../../.cursor/rules/006-observability.mdc)
**Code (target)**: `backend/logging_config.py`, `backend/metrics.py`, `backend/api/routes/health.py`, `infra/monitoring/`

The Kaziro observability story has three pillars: **structured logs**
(everything for debugging), **metrics** (everything for SLOs and alerting),
and **distributed traces** (everything for cross-service correlation).

## 1. Structured logging — `structlog`

### 1.1 Setup

Configured once in `backend/main.py` startup hook via
`backend/logging_config.py`:

- `JSONRenderer` in production.
- `ConsoleRenderer` (coloured) in `ENVIRONMENT=development`.
- Every module gets its logger via `logger = structlog.get_logger(__name__)`.
- `logging.getLogger(...)` from the stdlib is **forbidden** — always
  `structlog`.

### 1.2 Log levels

| Level     | When                                                                              | Examples                                              |
| --------- | --------------------------------------------------------------------------------- | ----------------------------------------------------- |
| DEBUG     | Dev only — **never in production**                                                | Raw API payloads, LLM prompt/response pairs, SQL queries |
| INFO      | Always on                                                                         | Pipeline stage start/complete, user actions, external API calls |
| WARNING   | Degraded but functional                                                           | Retries, cache misses, fallback to pass-1 scores      |
| ERROR     | Caught exception that affected the user or pipeline progression                   | Parser failed after retries, evaluator pass-1 failed  |
| CRITICAL  | System-level failure                                                              | DB unreachable, Redis down, OpenAI key invalid        |

### 1.3 Mandatory context fields

Every log call includes ALL relevant context for the operation. Bind once at
the start of a function, then use the bound logger for the rest of the
scope.

| Context field        | Include when…                          |
| -------------------- | -------------------------------------- |
| `user_id`            | Any user-scoped operation              |
| `job_posting_id`     | Any job-related operation              |
| `job_evaluation_id`  | Any evaluation-related operation       |
| `agent_name`         | Any agent node log                     |
| `node`               | Inside every agent node function       |
| `stage`              | Inside the pipeline orchestrator       |
| `task_id`            | Inside every Celery task               |
| `duration_ms`        | At completion of any timed operation   |
| `error`              | On every ERROR / WARNING log           |
| `trace_id`           | Always (set by middleware/OTel)        |

### 1.4 Pattern

```python
log = logger.bind(
    user_id=user_id,
    job_posting_id=job_id,
    agent_name="evaluator",
    node="pass1_draft",
)
log.info("evaluator_agent.pass1_start")

start = time.monotonic()
# ... work ...
log.info("evaluator_agent.pass1_complete", duration_ms=int((time.monotonic() - start) * 1000))
```

Event names are `<agent_or_module>.<event>` snake-case. They are stable
identifiers — log aggregation queries depend on them, so don't rename
casually.

### 1.5 What NEVER to log

- API keys, secrets, JWTs (partial or full).
- Full CV text or cover letter content.
- User email addresses in DEBUG / INFO (only in CRITICAL when needed, and
  even then prefer hashed identifiers).
- Full LLM prompts in production (large; may contain PII).
- Full scraped website content.

## 2. Metrics — Prometheus

### 2.1 File layout

All metrics defined in `backend/metrics.py` and imported where needed —
**single source of truth**.

```python
from prometheus_client import Counter, Histogram, Gauge

pipeline_jobs_total = Counter(
    "kaziro_pipeline_jobs_total",
    "Total jobs processed by the pipeline",
    ["stage", "status"],
)

agent_duration_seconds = Histogram(
    "kaziro_agent_duration_seconds",
    "Agent execution duration",
    ["agent_name"],
    buckets=[1, 5, 15, 30, 60, 120, 300],
)

active_pipeline_tasks = Gauge(
    "kaziro_active_pipeline_tasks",
    "Currently running pipeline tasks",
)
```

### 2.2 Instrumentation rules

- Wrap every agent entry point with the duration histogram:

  ```python
  with agent_duration_seconds.labels(agent_name="evaluator").time():
      result = await evaluator_graph.ainvoke(initial)
  ```

- Increment `pipeline_jobs_total{stage, status}` at every stage with
  `status="success"` or `status="error"`.
- Use `active_pipeline_tasks.inc()` / `.dec()` around Celery task execution
  (use `try/finally` for the decrement).
- Expose at `/metrics` via FastAPI route + `prometheus_client.generate_latest`
  (or `prometheus-fastapi-instrumentator` for auto-HTTP metrics).

### 2.3 Metric catalog

| Metric                                     | Type      | Labels                            | Notes                                       |
| ------------------------------------------ | --------- | --------------------------------- | ------------------------------------------- |
| `kaziro_pipeline_jobs_total`               | Counter   | `stage`, `status`                 | `stage` ∈ {fetch, parse, evaluate, research, document}; `status` ∈ {success, error} |
| `kaziro_agent_duration_seconds`            | Histogram | `agent_name`                      | Buckets tuned for LLM latencies             |
| `kaziro_evaluation_classification_total`   | Counter   | `classification`                  | `GOOD_FIT`, `MAYBE`, `REJECT`               |
| `kaziro_llm_tokens_used_total`             | Counter   | `agent_name`, `model`, `type`     | `type` ∈ {input, output}                    |
| `kaziro_api_request_duration_seconds`      | Histogram | `method`, `endpoint`, `status`    | Auto-emitted by instrumentator              |
| `kaziro_celery_queue_depth`                | Gauge     | `queue_name`                      | Sampled every 30 s by a sidecar             |
| `kaziro_external_api_calls_total`          | Counter   | `service`, `status`               | `service` ∈ {rapidapi, firecrawl, openai}   |
| `kaziro_active_pipeline_tasks`             | Gauge     | —                                 |                                             |
| `kaziro_db_connection_pool_in_use`         | Gauge     | —                                 | From SQLAlchemy engine events               |

### 2.4 Dashboards

Grafana dashboards live in `infra/monitoring/dashboards/`:

- **Pipeline Throughput** — fetch/parse/evaluate/research/document rates,
  classification breakdown.
- **Agent Latency** — p50/p95/p99 by `agent_name`.
- **API Performance** — request rate, error rate, p95 latency by endpoint.
- **Queue Health** — Celery queue depth, worker concurrency, retry rate.
- **Cost Tracking** — LLM tokens × model × agent (× cost coefficient
  derived from a static lookup table).

## 3. Distributed tracing — OpenTelemetry

- All FastAPI requests traced via `opentelemetry-instrumentation-fastapi`.
- Celery task spans via `opentelemetry-instrumentation-celery`.
- `trace_id` is propagated through Celery task headers and into structlog
  context — every log line carries it for cross-service correlation.
- Traces exported to **Grafana Tempo** in production, **Jaeger** locally.
- LLM calls produce a child span per agent node (manual instrumentation
  inside each node).

## 4. Alerting rules

Defined in `infra/monitoring/alerts.yaml` and applied via Alertmanager.

| Alert name                          | Condition                                     | Severity  | Action                                          |
| ----------------------------------- | --------------------------------------------- | --------- | ----------------------------------------------- |
| `KaziroPipelineErrorRateHigh`       | `rate(pipeline_jobs_total{status="error"}[15m]) / rate(pipeline_jobs_total[15m]) > 0.05` | CRITICAL | Page on-call, halt new pipeline tasks |
| `KaziroCeleryQueueBacklog`          | `kaziro_celery_queue_depth > 500` for 10 m   | WARNING   | Scale workers, Slack alert                      |
| `KaziroOpenAIErrorRateHigh`         | `rate(kaziro_external_api_calls_total{service="openai",status="error"}[10m]) > 0.10` | CRITICAL | Pause pipeline, banner notify users |
| `KaziroJobFetchEmpty`               | 3 consecutive fetches return 0 results        | WARNING   | Log alert, check RapidAPI quota                 |
| `KaziroDbPoolExhausted`             | `kaziro_db_connection_pool_in_use` ≥ pool_max | CRITICAL  | Auto-restart pods, page on-call                 |
| `KaziroAgentLatencyHigh`            | p95 of `kaziro_agent_duration_seconds` > 120 s | WARNING  | Investigate LLM latency, Slack alert            |
| `KaziroFirecrawlErrorRateHigh`      | `rate(kaziro_external_api_calls_total{service="firecrawl",status="error"}[10m]) > 0.20` | WARNING | Slack alert                                    |

Every alert must include: `summary`, `description`, `severity`,
`runbook_url`. Runbooks live in `docs/runbooks/<alert_name>.md` (created
when each alert ships).

## 5. Health checks

| Endpoint              | Purpose                                                                  |
| --------------------- | ------------------------------------------------------------------------ |
| `GET /health`         | Liveness — returns 200 if process is alive                               |
| `GET /health/ready`   | Readiness — checks DB connection, Redis connection                       |
| `GET /health/detailed` | Per-component status JSON (DB, Redis, OpenAI, Firecrawl, Supabase)      |

Celery worker health is exposed via Flower (`celery flower`) in dev and via
the Prometheus `celery-exporter` in production.

## 6. Sampling & retention

| Signal   | Retention                       | Sampling                                     |
| -------- | ------------------------------- | -------------------------------------------- |
| Logs     | 30 days hot, 1 year cold        | All ERROR/CRITICAL; INFO sampled at 100%; DEBUG only in dev |
| Metrics  | 15 days raw, 6 months 5-min     | No sampling — all metrics scraped every 15 s |
| Traces   | 7 days                          | 10% head sampling + 100% of traces with errors |

## 7. Adding a new metric — checklist

1. Define it in `backend/metrics.py` (with `kaziro_` prefix and a clear
   help string).
2. Increment / observe at the right place; for histograms always use a
   `with metric.time():` block.
3. Add an alert rule in `infra/monitoring/alerts.yaml` if the metric
   represents a failure mode.
4. Add a panel to the relevant Grafana dashboard JSON in
   `infra/monitoring/dashboards/`.
5. Document the metric in [section 2.3](#23-metric-catalog) of this file.

## 8. Adding a new log event — checklist

1. Bind the right context fields at the top of the function.
2. Use a stable snake-case event name `<module>.<event>`.
3. Include `duration_ms` for any timed operation.
4. Sanitise — never log secrets, full prompts, or full document text.
5. If this is a new failure mode, also add a metric for it.
