"""WSGI config for the parallel Kaziro Django backend."""

from __future__ import annotations

import os

from django.core.wsgi import get_wsgi_application

from config.langsmith import apply_langsmith_from_settings
from config.logging import configure_logging
from config.settings import get_settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

configure_logging()

settings = get_settings()
apply_langsmith_from_settings(settings)

application = get_wsgi_application()
