"""Celery task surface.

Phase 0 only ships the :mod:`backend.tasks.celery_app` factory so the
worker / beat containers can boot. Real task modules land in Phase 3
(T3.1+). When you add a new task module, register it in
:func:`backend.tasks.celery_app.create_celery_app` so autodiscovery
picks it up.
"""

from __future__ import annotations

__all__: list[str] = []
