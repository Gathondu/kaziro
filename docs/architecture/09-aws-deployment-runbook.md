# AWS Teardown Runbook

**Status**: Active until AWS teardown is complete  
**Last updated**: 2026-06-09  
**Scope**: Destroy legacy Kaziro AWS resources after the server and Vercel deployment is verified.

Kaziro no longer deploys to AWS. This runbook exists only to safely remove the
old Terraform-managed AWS stack.

## 1. Hard Gates

Do not destroy AWS resources until all of these are true:

- `https://167.233.100.112/health` returns `200`.
- `https://167.233.100.112/health/ready` reports ready.
- The Vercel production frontend is live and calls `https://167.233.100.112`.
- WebSocket notifications connect through
  `wss://167.233.100.112/api/v1/ws/notifications`.
- Supabase project details are confirmed external to AWS and must not be
  deleted.

## 2. Inventory Current State

Run from a local machine with AWS and Terraform credentials:

```bash
mkdir -p ../kaziro-aws-teardown-audit

cd infra/terraform/environments/staging
terraform init
terraform state list > ../../../../../kaziro-aws-teardown-audit/staging-state.txt
terraform plan -destroy -out=staging-destroy.tfplan

cd ../production
terraform init
terraform state list > ../../../../../kaziro-aws-teardown-audit/production-state.txt
terraform plan -destroy -out=production-destroy.tfplan
```

Keep the audit files outside the repo so they are not committed.

## 3. Destroy Application Environments

Destroy staging first, then production:

```bash
cd infra/terraform/environments/staging
terraform destroy

cd ../production
terraform destroy
```

If destroy is blocked:

- Empty versioned S3 buckets created for frontend hosting.
- Delete images from Kaziro ECR repositories.
- Wait for CloudFront distributions, App Runner services, API Gateway APIs, and
  ElastiCache resources to finish deleting.
- Re-run `terraform destroy`.

Resource families expected from the old stack:

- ECR repositories and lifecycle policies
- App Runner service and VPC connector
- API Gateway HTTP and WebSocket APIs
- Lambda realtime handlers
- ECS cluster, services, task definitions, and task roles
- CloudWatch log groups
- IAM roles and inline/attached policies
- ElastiCache Valkey replication groups and subnet groups
- VPC, subnets, route tables, NAT gateway, EIP, and security groups
- S3 frontend buckets, policies, and CloudFront distributions
- DynamoDB WebSocket connection tables
- Secrets Manager references or owned runtime secrets

## 4. Destroy Bootstrap State

After both environments are gone and no Terraform state is needed:

```bash
cd infra/terraform/bootstrap
terraform destroy
```

This removes the legacy state bucket and lock table:

- `kaziro-terraform-state`
- `kaziro-terraform-locks`

If the state bucket still contains versions, empty all versions and delete
markers before retrying.

## 5. Final AWS Sweep

Search the AWS account and region for names or tags containing:

- `kaziro`
- `kaziro-staging`
- `kaziro-production`

Confirm no Kaziro App Runner, ECS, ECR, API Gateway, Lambda, CloudFront, S3,
ElastiCache, DynamoDB, VPC, NAT gateway, EIP, CloudWatch log group, Secrets
Manager secret, or IAM role/policy resources remain.

After verification, delete AWS-only GitHub secrets such as
`AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`.
