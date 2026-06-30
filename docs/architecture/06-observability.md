# Observability

**Status**: Active
**Last updated**: 2026-06-29

Kaziro uses structured logs, request IDs, and trace-friendly context fields so
API requests, Celery tasks, and agent workflow runs can be connected.

## Logging

- Backend logs use `structlog`.
- Logs include request ID, user ID when available, task ID, workflow ID, and
  domain identifiers such as job or application IDs.
- Do not log secrets, passwords, API keys, CV body text, or email bodies.

## Metrics

Expose metrics in Prometheus format when metrics collection is enabled. Useful
series include request latency, task duration, task failures, LLM calls, token
usage, queue depth, and external API failures.

## Tracing

Trace context should flow across:

- Django request handling
- service calls
- Celery task dispatch and execution
- LangGraph node execution
- external API calls

## Alerts

Alert on API error rate, worker failures, queue backlog, failed document
generation, and repeated external provider failures.
