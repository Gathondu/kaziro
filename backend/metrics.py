"""Prometheus metric registry — single source of truth.

Every metric exported by Kaziro is declared here so the catalog is
trivial to inspect in code review and documentation. Refer to
``docs/architecture/06-observability.md`` for the canonical catalog and
alert mapping.
"""

from __future__ import annotations

from typing import Final

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

# A dedicated registry keeps Kaziro metrics isolated from any third-party
# default-registry collisions (notably useful in tests where modules can be
# re-imported).
registry: Final[CollectorRegistry] = CollectorRegistry(auto_describe=True)


# ---------------------------------------------------------------------------
# Pipeline volume + outcome
# ---------------------------------------------------------------------------
pipeline_jobs_total: Final[Counter] = Counter(
    "kaziro_pipeline_jobs_total",
    "Total jobs processed by the pipeline, broken down by stage and outcome.",
    labelnames=("stage", "status"),
    registry=registry,
)

# ---------------------------------------------------------------------------
# Per-agent latency
# ---------------------------------------------------------------------------
agent_duration_seconds: Final[Histogram] = Histogram(
    "kaziro_agent_duration_seconds",
    "Wall-clock duration of an agent invocation.",
    labelnames=("agent_name",),
    buckets=(1, 5, 15, 30, 60, 120, 300),
    registry=registry,
)

# ---------------------------------------------------------------------------
# Evaluator outcomes
# ---------------------------------------------------------------------------
evaluation_classification_total: Final[Counter] = Counter(
    "kaziro_evaluation_classification_total",
    "Final classification produced by the evaluator agent.",
    labelnames=("classification",),
    registry=registry,
)

# ---------------------------------------------------------------------------
# LLM token spend (cost tracking)
# ---------------------------------------------------------------------------
llm_tokens_used_total: Final[Counter] = Counter(
    "kaziro_llm_tokens_used_total",
    "LLM tokens consumed, labelled by agent, model, and direction.",
    labelnames=("agent_name", "model", "type"),  # type ∈ {input, output}
    registry=registry,
)

# ---------------------------------------------------------------------------
# HTTP request latency (FastAPI middleware also fills this)
# ---------------------------------------------------------------------------
api_request_duration_seconds: Final[Histogram] = Histogram(
    "kaziro_api_request_duration_seconds",
    "HTTP request latency at the API edge.",
    labelnames=("method", "endpoint", "status"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
    registry=registry,
)

# ---------------------------------------------------------------------------
# Celery queue depth (sampled by sidecar)
# ---------------------------------------------------------------------------
celery_queue_depth: Final[Gauge] = Gauge(
    "kaziro_celery_queue_depth",
    "Number of pending tasks in a Celery queue.",
    labelnames=("queue_name",),
    registry=registry,
)

# ---------------------------------------------------------------------------
# External API call accounting
# ---------------------------------------------------------------------------
external_api_calls_total: Final[Counter] = Counter(
    "kaziro_external_api_calls_total",
    "Calls to upstream services, labelled by service and outcome.",
    labelnames=("service", "status"),  # service ∈ {rapidapi, firecrawl, openai}
    registry=registry,
)

# ---------------------------------------------------------------------------
# Active pipeline tasks (live concurrency)
# ---------------------------------------------------------------------------
active_pipeline_tasks: Final[Gauge] = Gauge(
    "kaziro_active_pipeline_tasks",
    "Pipeline tasks currently executing across all workers.",
    registry=registry,
)


__all__ = [
    "active_pipeline_tasks",
    "agent_duration_seconds",
    "api_request_duration_seconds",
    "celery_queue_depth",
    "evaluation_classification_total",
    "external_api_calls_total",
    "llm_tokens_used_total",
    "pipeline_jobs_total",
    "registry",
]
