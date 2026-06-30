# AWS Resource Teardown Runbook

**Status**: Reference
**Last updated**: 2026-06-29

Use this runbook when Kaziro AWS resources need to be removed after server and
Vercel deployment are verified.

## Preconditions

- Confirm the backend, workers, and Beat are healthy on the server.
- Confirm the frontend deployment is serving the expected production app.
- Confirm there are no active DNS, storage, queue, or database dependencies in
  the AWS account for Kaziro.

## Teardown Steps

1. Export the target AWS profile and region.
2. Review Terraform state and planned destroys.
3. Empty versioned buckets before destroying them.
4. Delete container images and log groups that block teardown.
5. Destroy Terraform-managed resources.
6. Run an AWS resource sweep for names and tags containing `kaziro`.

## Verification

The teardown is complete when the AWS sweep returns no Kaziro-named resources
and production traffic is still served by the current server/Vercel topology.
