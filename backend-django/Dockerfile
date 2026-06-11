FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    DJANGO_SETTINGS_MODULE=config.settings

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY backend-django/pyproject.toml backend-django/uv.lock* ./
RUN uv sync --frozen --no-dev || uv sync --no-dev

COPY backend-django/ .

EXPOSE 8001

CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8001"]
