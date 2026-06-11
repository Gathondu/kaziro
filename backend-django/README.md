# Kaziro Django Backend

Parallel Django + Django Ninja scaffold for the Kaziro stack migration.
The existing FastAPI backend remains the production source of truth until
feature slices are migrated and verified.

## Local commands

```bash
uv sync
uv run python manage.py check
uv run python manage.py test
uv run python manage.py runserver 0.0.0.0:8001
uv run celery -A config.celery:celery_app worker --loglevel=info -Q default,parser,evaluator,research,document,maintenance
uv run celery -A config.celery:celery_app beat --loglevel=info --schedule=/tmp/celerybeat-schedule
```

Health endpoints:

- `GET /health`
- `GET /health/ready`
- `GET /api/v1/meta`
