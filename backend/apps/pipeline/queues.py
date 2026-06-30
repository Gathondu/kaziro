from __future__ import annotations

from typing import Final

QUEUE_DEFAULT: Final[str] = "default"
QUEUE_PARSER: Final[str] = "parser"
QUEUE_EVALUATOR: Final[str] = "evaluator"
QUEUE_RESEARCH: Final[str] = "research"
QUEUE_DOCUMENT: Final[str] = "document"
QUEUE_MAINTENANCE: Final[str] = "maintenance"

ALL_QUEUES: Final[tuple[str, ...]] = (
    QUEUE_DEFAULT,
    QUEUE_PARSER,
    QUEUE_EVALUATOR,
    QUEUE_RESEARCH,
    QUEUE_DOCUMENT,
    QUEUE_MAINTENANCE,
)
