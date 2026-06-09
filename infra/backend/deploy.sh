#!/bin/sh
set -eu

APP_DIR="${APP_DIR:-/opt/kaziro}"

cd "$APP_DIR"

compose() {
  docker compose --env-file .env.production "$@"
}

for required_var in APP_ENV CORS_ORIGINS DATABASE_URL DATABASE_URL_SYNC SUPABASE_URL SUPABASE_ANON_KEY SUPABASE_SERVICE_KEY SUPABASE_JWT_SECRET REDIS_URL OPENROUTER_API_KEY RAPIDAPI_KEY RAPIDAPI_HOST FIRECRAWL_API_KEY; do
  if ! grep -Eq "^${required_var}=.+" .env.production; then
    printf '%s\n' "Missing required value in .env.production: ${required_var}" >&2
    exit 1
  fi
done

compose up -d --build --remove-orphans redis backend
compose run --rm backend sh -c "cd backend && alembic upgrade head"
compose up -d --build --remove-orphans
