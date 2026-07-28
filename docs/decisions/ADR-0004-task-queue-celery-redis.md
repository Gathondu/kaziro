# ADR-0004: Celery + Redis for the asynchronous task queue

**Status**: Accepted
**Date**: 2026-04-22
**Deciders**: Founding engineering team
**Tags**: backend, infra

## Context and problem statement

The Kaziro pipeline runs long-lived, fan-out work that must not block the
HTTP request cycle:

- Cron-triggered job-search runs (per user, hourly).
- Per-job pipeline execution (parser → evaluator → research → document).
- Scheduled retries and dead-letter handling.
- Periodic cleanups (cache expiry, audit-log compaction).

We need a battle-tested task-queue with: retries, scheduling, prioritised
queues, observability, and Python integration.

> "What background-task system do we use to drive the pipeline?"

## Decision drivers

- Mature, production-proven Python task queue.
- Native scheduling (Celery Beat) — replaces cron at the app layer.
- Retries with exponential backoff out of the box.
- Distinct queues for different SLOs (parser fast lane vs. document slow
  lane).
- Observability via Flower + Prometheus exporters.
- Plays well with Django, Django Ninja, and the ORM.

## Considered options

1. **Celery + Redis** — broker + result backend on Redis.
2. **Celery + RabbitMQ** — broker on RabbitMQ.
3. **RQ (Redis Queue)** — minimal Python task queue.
4. **Dramatiq** — modern Python task queue.
5. **Cloud-native** (AWS SQS + Lambda or Google Cloud Tasks).

## Decision outcome

**Chosen option**: Celery + Redis.

Celery is the de-facto Python task queue. Redis (which we already need for
caching and Pub/Sub for SSE fan-out) doubles as the broker, so we
add zero additional infra at MVP. Celery Beat handles cron scheduling.

### Positive consequences

- One Redis instance covers cache + broker + Pub/Sub.
- Celery Beat replaces system cron — versioned with the codebase.
- Per-queue worker concurrency lets us tune cost/latency by stage.
- Flower + `celery-prometheus-exporter` give us observability for free.
- Mature retry / dead-letter semantics — no custom retry harness.

### Negative consequences

- Celery is heavyweight; the API is large and easy to mis-configure.
- Redis as a broker has weaker durability guarantees than RabbitMQ
  (acceptable trade for ops simplicity at MVP scale).
- Celery + asyncio integration is awkward — we run async code inside
  sync tasks via `asyncio.run()` per task.

## Pros and cons of the options

### Option 1 — Celery + Redis

- **Pros**: Mature; Beat scheduler; one Redis covers everything; great
  observability story.
- **Cons**: Heavy API; sync-first; Redis broker is "good enough" not
  "best".

### Option 2 — Celery + RabbitMQ

- **Pros**: Industry-standard durable broker; better routing.
- **Cons**: Adds another stateful service to host and monitor.

### Option 3 — RQ

- **Pros**: Minimal API; easy onboarding.
- **Cons**: Weaker scheduling story; smaller ecosystem; less observability.

### Option 4 — Dramatiq

- **Pros**: Modern API; nice ergonomics.
- **Cons**: Smaller community; fewer hosted observability options.

### Option 5 — Cloud-native (SQS + Lambda)

- **Pros**: Zero infra to host.
- **Cons**: Couples us to one cloud; cold-start latency for short tasks;
  scheduling is awkward; harder local dev.

## Links

- [`docs/architecture/02-agentic-pipeline.md`](../architecture/02-agentic-pipeline.md)
- [`docs/design/agents/pipeline-orchestrator.md`](../design/agents/pipeline-orchestrator.md)
- [Celery docs](https://docs.celeryq.dev/)
