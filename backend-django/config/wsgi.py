"""WSGI config for the parallel Kaziro Django backend."""

from __future__ import annotations

import os

from django.core.wsgi import get_wsgi_application

from apps.core.logging_config import configure_logging

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

configure_logging()
application = get_wsgi_application()
