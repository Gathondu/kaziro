FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    DJANGO_SETTINGS_MODULE=config.settings \
    UV_PROJECT_ENVIRONMENT=/venv

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY backend/pyproject.toml backend/uv.lock* ./
RUN uv sync --frozen || uv sync

COPY backend/ .

# The venv lives outside /app so dev bind mounts of ./backend cannot shadow it.
ENV PATH="/venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "config.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--timeout-graceful-shutdown", "10"]
