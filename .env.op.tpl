# =============================================================================
# Kaziro — 1Password environment template
# =============================================================================
# Render the real .env with `make env` (op inject). Requires
# OP_SERVICE_ACCOUNT_TOKEN — the zsh init exports it from
# ~/.config/op/token (see README, "Development container").
#
# Secrets resolve from the 1Password item "kaziro" in the "Development"
# vault — create that item with these field labels:
#   SECRET_KEY, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY, SUPABASE_JWT_SECRET,
#   OPENROUTER_API_KEY, SCRAPPER_API_KEY, RESEND_API_KEY, LANGSMITH_API_KEY
# Non-secret values stay inline; adjust them to your real project values.

# -----------------------------------------------------------------------------
# Application
# -----------------------------------------------------------------------------
APP_ENV=development
APP_NAME=kaziro
APP_VERSION=1.0.0
API_NAMESPACE=api-v1
LOG_LEVEL=INFO
LOG_FORMAT=console
DEBUG=false
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Django backend
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
DJANGO_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
DJANGO_FRONTEND_URL=http://localhost:3000
DJANGO_DATABASE_URL=postgresql://kaziro:kaziro@postgres:5432/kaziro
DJANGO_JWT_ISSUER=kaziro
DJANGO_JWT_AUDIENCE=kaziro-web
SECRET_KEY=op://Development/kaziro-dev/SECRET_KEY
AUTH_ACCESS_TOKEN_MINUTES=60
AUTH_REFRESH_TOKEN_DAYS=30
EMAIL_CONFIRMATION_TTL_HOURS=24

# -----------------------------------------------------------------------------
# Redis
# -----------------------------------------------------------------------------
REDIS_URL=redis://redis:6379/0
REDIS_CACHE_DB=0
REDIS_BROKER_DB=1
REDIS_RESULT_DB=2
REDIS_PUBSUB_DB=3

# -----------------------------------------------------------------------------
# Celery
# -----------------------------------------------------------------------------
CELERY_TASK_ALWAYS_EAGER=false
CELERY_WORKER_CONCURRENCY=4
CELERY_TASK_TIME_LIMIT=1800
CELERY_TASK_SOFT_TIME_LIMIT=1500

# -----------------------------------------------------------------------------
# OpenRouter / LLM
# -----------------------------------------------------------------------------
OPENROUTER_API_KEY=op://Development/kaziro-dev/OPENROUTER_API_KEY
OPENROUTER_TIMEOUT_SECONDS=300
OPENROUTER_MAX_RETRIES=3
LLM_MODEL_PARSER=nvidia/nemotron-3-super-120b-a12b:free
LLM_MODEL_EVALUATOR=nvidia/nemotron-3-super-120b-a12b:free
LLM_MODEL_RESEARCH=nvidia/nemotron-3-super-120b-a12b:free
LLM_MODEL_DOCUMENT=nvidia/nemotron-3-super-120b-a12b:free
LLM_EMBEDDING_MODEL=nvidia/llama-nemotron-embed-vl-1b-v2:free
LLM_EMBEDDING_DIM=2048

# -----------------------------------------------------------------------------
# External integrations
# -----------------------------------------------------------------------------
JOB_SOURCE_DISCOVERY_URL=http://host.docker.internal:3100
JOB_SOURCE_DISCOVERY_TIMEOUT_SECONDS=600
SCRAPPER_COMPANY_RESEARCH_URL=http://host.docker.internal:3100
SCRAPPER_COMPANY_RESEARCH_TIMEOUT_SECONDS=600
SCRAPPER_API_KEY=op://Development/scrapper-dev/SCRAPPER_API_KEY
RAPIDAPI_KEY=op://Development/kaziro-dev/RAPIDAPI_KEY
RESEND_API_KEY=op://Development/kaziro-dev/RESEND_API_KEY
RESEND_FROM_EMAIL=Kaziro <denis@gathondu.com>
RESEND_TIMEOUT_SECONDS=10

# -----------------------------------------------------------------------------
# Observability
# -----------------------------------------------------------------------------
OTEL_SAMPLE_RATE=0.1
PROMETHEUS_METRICS_PATH=/metrics
SENTRY_TRACES_SAMPLE_RATE=0.05

# -----------------------------------------------------------------------------
# Local-dev only
# -----------------------------------------------------------------------------
RELOAD=true
MOCK_LLM=false

# Next.js frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_ENV=development

# -----------------------------------------------------------------------------
# LangSmith tracing
# -----------------------------------------------------------------------------
LANGSMITH_TRACING=false
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=op://Development/kaziro-dev/LANGSMITH_API_KEY
LANGSMITH_PROJECT=kaziro-dev
