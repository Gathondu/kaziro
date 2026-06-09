# Kaziro AWS Terraform (legacy teardown only)

Kaziro no longer deploys to AWS. This Terraform stack is retained temporarily
only to destroy legacy Kaziro AWS resources. The active deployment is the
server/Vercel split documented in `docs/architecture/08-deployment.md`.

The legacy stack created:

- Frontend static hosting: S3 + CloudFront
- Backend API: App Runner, fronted by API Gateway HTTP API
- Async workers: ECS Fargate (worker + beat services)
- Queue/cache: ElastiCache Valkey
- Secrets: AWS Secrets Manager

Before removing this directory, follow
`docs/architecture/09-aws-deployment-runbook.md` and confirm both staging and
production AWS environments plus bootstrap state have been destroyed.

## Layout

- `modules/`: reusable AWS building blocks
- `environments/staging`: staging stack
- `environments/production`: production stack

Each environment passes `environment` and image tags into shared modules.

## Remote state

Terraform state backend is expected to be:

- S3 bucket (state files)
- DynamoDB table (state locking)

Configure backend settings in each environment folder before first apply.

## Deploy variables

Required runtime variables are provided via one JSON secret:

- `kaziro/<env>/backend/runtime-env-json`

The backend image entrypoint loads this JSON and exports process env vars
before starting API/worker/beat processes.
