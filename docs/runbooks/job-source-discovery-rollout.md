# Job Source Discovery Rollout

This is a future production rollout runbook. Implementing the Django workflow
does not authorize changing the currently deployed legacy Kaziro stack.

## Prerequisites

1. Create the neutral external network once: `docker network create shared_services`.
2. Attach the independently deployed scraper service to `shared_services` with
   the alias `scrapper`; the Kaziro repo must not build or own that service.
3. Set `JOB_SOURCE_DISCOVERY_URL=http://scrapper:3100` and
   `JOB_SOURCE_DISCOVERY_TIMEOUT_SECONDS=120` in Kaziro's production environment.
4. Deploy the Django backend, apply migrations, and start the dedicated
   `worker-discovery` service from `infra/backend/compose.yaml`.
5. Change Caddy so `/scrapper/health` remains public but `/scrapper/discover`
   and `/scrapper/extract-page` are no longer routed.

## Smoke Test

1. Confirm the public health URL returns HTTP 200.
2. From the Kaziro backend container, confirm `http://scrapper:3100/health`
   returns HTTP 200.
3. In Django admin, create a provider and queue discovery from its detail page.
4. Confirm the run succeeds and links to a generated draft.
5. Review or correct the JSON, validate it, and approve it.
6. Confirm the old approved draft is superseded and only the new one is approved.
7. Run one job-search config and confirm raw jobs are stored without duplicate
   `(provider, external_job_id)` records.

## Rollback

Stop `worker-discovery`, restore the prior Kaziro release and its compatible
database state, and restore the previous Caddy configuration. Do not point
Kaziro at the public scraper route as a fallback.
