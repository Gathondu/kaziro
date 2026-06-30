# Environment Variables

**Status**: Living
**Last updated**: 2026-06-29

Secrets belong in `.env` or platform secret stores. Commit only safe examples
to `.env.example`.

## Backend

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `APP_ENV` | No | `development` | Runtime environment label. |
| `SECRET_KEY` | Yes | - | Django signing secret. |
| `DJANGO_DEBUG` / `DEBUG` | No | `false` | Django debug mode. Keep false in production. |
| `DJANGO_ALLOWED_HOSTS` / `ALLOWED_HOSTS` | No | `localhost,127.0.0.1,0.0.0.0` | Comma-separated allowed hosts. |
| `DJANGO_CORS_ORIGINS` / `CORS_ORIGINS` | No | local frontend origins | Browser origins allowed to call the API. |
| `DJANGO_DATABASE_URL` | Yes outside local sqlite use | - | Database URL for Django. |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis cache/pubsub URL. |
| `CELERY_BROKER_URL` | No | `redis://localhost:6379/1` | Celery broker URL. |
| `CELERY_RESULT_BACKEND` | No | `redis://localhost:6379/2` | Celery result backend URL. |
| `DJANGO_FRONTEND_URL` | No | `http://localhost:3000` | Frontend origin used in generated links. |
| `DJANGO_JWT_ISSUER` | No | `kaziro` | JWT issuer. |
| `DJANGO_JWT_AUDIENCE` | No | `kaziro-web` | JWT audience. |
| `AUTH_ACCESS_TOKEN_MINUTES` | No | `60` | Access token lifetime. |
| `AUTH_REFRESH_TOKEN_DAYS` | No | `30` | Refresh token lifetime. |
| `EMAIL_CONFIRMATION_TTL_HOURS` | No | `24` | Email confirmation token lifetime. |
| `RESEND_API_KEY` | Yes in production | - | Resend API key. |
| `RESEND_FROM_EMAIL` | No | local sender | Confirmation email sender. |
| `RESEND_REPLY_TO` | No | - | Optional reply-to address. |
| `RESEND_TIMEOUT_SECONDS` | No | `10` | Resend API timeout. |
| `OPENROUTER_API_KEY` | Yes for LLM calls | - | OpenRouter API key. |
| `FIRECRAWL_API_KEY` | Yes for company research | - | Firecrawl API key. |
| `RAPIDAPI_KEY` | Yes for job fetches | - | RapidAPI key. |
| `RAPIDAPI_HOST` | No | provider-specific | RapidAPI host. |
| `LLM_MODEL_PARSER` | No | configured default | Parser agent model. |
| `LLM_MODEL_EVALUATOR` | No | configured default | Evaluator agent model. |
| `LLM_MODEL_RESEARCH` | No | configured default | Research agent model. |
| `LLM_MODEL_DOCUMENT` | No | configured default | Document agent model. |
| `LLM_EMBEDDING_MODEL` | No | configured default | Embedding model. |
| `LLM_EMBEDDING_DIM` | No | configured default | Embedding vector dimension. |

## Frontend

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | No | `http://localhost:8000` | Browser-visible API origin. |
| `NEXT_PUBLIC_WS_URL` | No | `ws://localhost:8000/ws` | Browser-visible realtime origin. |
| `NEXT_PUBLIC_SITE_URL` | No | `http://localhost:3000` | Public site origin. |

## Production

Production secrets are managed by the deployment platform:

- backend/server secrets through GitHub Actions and server `.env.production`
- frontend public variables through Vercel project settings

Never commit real values.
