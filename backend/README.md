# Kaziro Backend

Django and Django Ninja backend for Kaziro.

## Commands

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run python manage.py check
uv run python manage.py migrate
uv run python manage.py test
uv run python manage.py runserver 0.0.0.0:8000
```

Celery:

```bash
uv run celery -A config.celery:app worker --loglevel=INFO
uv run celery -A config.celery:app beat --loglevel=INFO --schedule=/tmp/celerybeat-schedule
```

## Layout

```text
backend/
├── config/
├── apps/
│   ├── accounts/
│   ├── core/
│   ├── profiles/
│   ├── jobs/
│   ├── applications/
│   ├── documents/
│   ├── pipeline/
│   └── notifications/
└── tests/
```
