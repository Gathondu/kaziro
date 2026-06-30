"""ASGI config for the Kaziro Django backend."""

from __future__ import annotations

import os

from django_asgi_lifespan.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


application = get_asgi_application()
