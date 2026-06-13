from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Final

from django.apps import AppConfig
from django_asgi_lifespan.register import register_lifespan_manager
from django_asgi_lifespan.types import LifespanManager

from config.langsmith import apply_langsmith_from_settings
from config.logging import configure_logging, get_logger
from config.redis import get_redis
from config.settings import get_settings

configure_logging()

log = get_logger(__name__)


@asynccontextmanager
async def _lifespan_manager() -> LifespanManager:
    settings = get_settings()
    apply_langsmith_from_settings(settings)
    log.info(
        "app.startup",
        app_env=str(settings.APP_ENV),
        log_format=str(settings.LOG_FORMAT),
        log_level=settings.LOG_LEVEL,
    )

    shutdown_event = asyncio.Event()

    state: Final[dict[str, Any]] = {
        "shutdown_event": shutdown_event,
    }
    try:
        yield state
    finally:
        log.info("app.shutdown.initiating")
        shutdown_event.set()

        client = get_redis()
        await client.aclose()
        log.info("app.shutdown")


class KaziroAppConfig(AppConfig):
    name = "config"
    label = "config"

    def ready(self) -> None:
        register_lifespan_manager(context_manager=_lifespan_manager)
