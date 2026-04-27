# AWS Deployment Runbook (Terraform + GitHub Actions)

**Status**: Active  
**Last updated**: 2026-04-27  
**Source**: AWS deployment implementation for `infra/terraform` and `.github/workflows/deploy-aws.yml`  
**Related ADRs**: [ADR-0003](../decisions/ADR-0003-auth-supabase.md), [ADR-0004](../decisions/ADR-0004-task-queue-celery-redis.md), [ADR-0007](../decisions/ADR-0007-frontend-sveltekit.md)

## 1. Scope

This runbook defines the active AWS deployment path without custom domains:

- `develop` branch auto-deploys to `staging`
- `main` branch auto-deploys to `production`
- Frontend is hosted from S3 behind CloudFront (AWS URL)
- Backend is App Runner behind API Gateway (AWS URL)
- Celery worker and beat run as separate ECS Fargate services
- Valkey is managed via ElastiCache
- Postgres/Auth remain on Supabase

## 2. Required GitHub Secrets per Environment

Configure these in GitHub Environment secrets for both `staging` and `production`:

| Secret name | Purpose |
| --- | --- |
| `AWS_ACCESS_KEY_ID` | IAM user access key for deployment |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret for deployment |
| `PUBLIC_SUPABASE_URL` | Frontend public Supabase URL |
| `PUBLIC_SUPABASE_ANON_KEY` | Frontend public Supabase anon key |

Backend runtime configuration is read from AWS Secrets Manager secrets that must already exist:

- `kaziro/staging/backend/runtime-env-json`
- `kaziro/production/backend/runtime-env-json`

These JSON secrets must include app-required backend env values (DB, Supabase service key, API keys, CORS origins, etc). Redis URL is injected by Terraform at runtime via task/service environment variable.

## 3. Terraform Apply Inputs

From CI, Terraform receives:

- `TF_VAR_image_tag` from `GITHUB_SHA`

The environment stacks are:

- `infra/terraform/environments/staging`
- `infra/terraform/environments/production`

## 4. Runtime Process Commands

- API (App Runner):  
  `uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000`
- Worker (ECS Fargate):  
  `uv run celery -A backend.tasks.celery_app:celery_app worker --loglevel=INFO -Q default,parser,evaluator,research,document,maintenance`
- Beat (ECS Fargate):  
  `uv run celery -A backend.tasks.celery_app:celery_app beat --loglevel=INFO`

## 5. Rollout Sequence

1. Ensure `infra/terraform/bootstrap` state resources exist.
2. Push to `develop`.
3. Pipeline builds and pushes backend image to ECR.
4. Terraform applies staging stack with the new image tag.
5. Frontend builds with staging API URL and uploads to staging S3 bucket.
6. CloudFront invalidation is triggered.
7. Smoke checks verify API and frontend endpoints.
8. Promote by merging to `main` to repeat flow for production.

## 6. Validation Gates

Deployment is considered successful only if all checks pass:

- App Runner service healthy (`/health` responds)
- API Gateway URL reachable
- ECS worker desired tasks are running
- ECS beat desired tasks are running
- Valkey reachable from API and Celery tasks (no Redis connection failures in logs)
- Frontend URL returns `200` through CloudFront
- Backend logs show successful Supabase connection/auth operations

## 7. Rollback

If deploy regresses:

1. Re-run workflow from the last known-good commit.
2. This re-pushes older backend image tag and reapplies Terraform references.
3. Frontend artifacts are re-synced and CloudFront invalidated.
4. Re-run smoke checks.

For infra-only breakage, run `terraform apply` from the previous commit in the affected environment directory.
