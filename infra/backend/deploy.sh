#!/bin/sh
set -eu

APP_DIR="${APP_DIR:-/opt/kaziro}"

cd "$APP_DIR"

compose() {
  docker compose --env-file .env.production "$@"
}

for required_var in APP_ENV SECRET_KEY DJANGO_DATABASE_URL REDIS_URL OPENROUTER_API_KEY SCRAPPER_API_KEY JOB_SOURCE_DISCOVERY_URL; do
  if ! grep -Eq "^${required_var}=.+" .env.production; then
    printf '%s\n' "Missing required value in .env.production: ${required_var}" >&2
    exit 1
  fi
done

compose up -d --build --remove-orphans redis backend
compose run --rm backend uv run python manage.py migrate --noinput
compose up -d --build --remove-orphans
