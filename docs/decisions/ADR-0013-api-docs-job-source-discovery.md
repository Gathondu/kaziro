# ADR-0013: API Documentation Driven Job Source Discovery

**Status**: Accepted
**Date**: 2026-06-30

## Context

Kaziro originally treated RapidAPI job endpoints as the primary fetch source.
That made the ingestion pipeline brittle because upstream API contracts and
hosts can change independently of Kaziro releases.

## Decision

Kaziro will use approved provider configs as the fetch-source abstraction. A
separately deployed discovery service loads public API documentation, then
proposes config drafts. Django stores those drafts, validates them with smoke
requests, and requires admin approval before a provider can be used by scheduled
ingestion.

The discovery service is not managed by the Kaziro repo and is not the system of
record. Kaziro only stores the service URL used for discovery requests. Django
owns provider state, approval, validation history, and raw job persistence.
Only one approved config is consumable per provider. Approving a replacement
keeps the previous draft as superseded history.

## Consequences

- RapidAPI/JSearch becomes one provider option, not the pipeline identity.
- Generated configs never store API secrets; configs reference environment
  variable names for provider credentials.
- Provider-specific non-secret request headers are stored in `request_headers`.
  This supports values such as RapidAPI's per-provider `X-RapidAPI-Host`
  without hardcoding RapidAPI behavior in the fetcher. Sensitive headers must
  reference environment variables instead of storing literal values.
- Discovery drafts include provider-native `smoke_test_params` inferred from
  documentation evidence. Validation persists the executed URL, redacted
  headers, status, response headers, and complete parsed response body so staff
  can diagnose provider-specific failures in Django admin.
- Provider configs may declare a dot-separated `response_list_path`, such as
  `data.jobs`, for APIs whose job array is nested inside response envelopes.
- Discovery is limited to public API documentation pages in v1.
- The fetch pipeline can add or repair sources without changing core parser,
  evaluator, research, or document-agent behavior.

## Alternatives Considered

1. **Keep hardcoded API clients** — simpler, but each upstream change requires
   code edits and releases.
2. **Let an agent call docs dynamically at runtime** — flexible, but too risky
   for production ingestion because bad extraction could silently alter calls.
3. **Scrape job pages directly first** — broader coverage, but higher
   fragility and terms-of-service risk than using documented APIs.
