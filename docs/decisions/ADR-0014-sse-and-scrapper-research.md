# ADR-0014: SSE Notifications And Scrapper-Owned Research

**Status**: Accepted  
**Date**: 2026-07-27

## Context

Kaziro only sends notification events from the server to the browser, so a
bidirectional WebSocket service added unnecessary infrastructure. Company
research also needs a reusable, security-bounded browser and extraction layer
whose raw evidence remains independent from model synthesis.

## Decision

- Use authenticated Server-Sent Events at
  `GET /api/v1/notifications/stream`.
- Authenticate with the normal bearer header through a fetch-based client.
- Keep notification rows as the durable source of truth and Redis user
  channels as the live transport. Replay from `Last-Event-ID`.
- Make Scrapper responsible for official-site selection, browser rendering,
  crawling, extraction, SSRF controls, limits, and evidence provenance.
- Keep OpenRouter out of Scrapper's company endpoint. Kaziro may synthesize
  only returned evidence and must attach source URLs to populated fields.
- Stop document generation after a total research failure.

## Consequences

The standalone WebSocket API, connection table, browser WebSocket origin, and
Firecrawl runtime configuration are removed. The reverse proxy must preserve
long-lived streaming responses and disable buffering for the SSE route.
Scrapper and Kaziro share a service credential stored only in runtime secrets.

This decision supersedes ADR-0005 for company research.
