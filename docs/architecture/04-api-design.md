# API Design

**Status**: Active
**Last updated**: 2026-07-27

Kaziro exposes a Django Ninja API under `/api/v1`.

## Envelope

All API responses use one top-level envelope:

```json
{
  "data": {},
  "meta": {},
  "error": null
}
```

On errors, `data` is `null` and `error` contains a stable code plus a
user-safe message.

```json
{
  "data": null,
  "meta": { "request_id": "..." },
  "error": {
    "code": "not_found",
    "message": "The requested resource was not found."
  }
}
```

## Status Codes

| Code | Meaning |
| --- | --- |
| 200 | Successful read or command |
| 201 | Resource created |
| 204 | Successful command with no body |
| 400 | Invalid request semantics |
| 401 | Missing or invalid authentication |
| 403 | Authenticated but not allowed |
| 404 | Resource not found |
| 409 | Conflict |
| 422 | Schema validation error |
| 500 | Internal server error |

## Resource Shape

- Route functions stay thin.
- Request and response schemas are typed.
- Services own business logic.
- Repositories/query helpers own database access.
- List endpoints return pagination metadata in `meta`.

## OpenAPI

Django Ninja publishes OpenAPI metadata for the mounted API. Keep schema names
stable because the frontend API client and tests depend on predictable payloads.

## Restored Resources

- `/jobs`: cursor-filtered listing, URL import, detail, evaluation,
  not-interested, regeneration, direct generated-document edits, and
  authenticated PDF downloads.
- `/applications`: board listing, detail, notes, document edits, transitions,
  mark-sent, deletion, history, and PDFs.
- `/job-configs`: CRUD, soft disable, schedule presets, and immediate runs.
- `/profile`: candidate profile, PDF CV, CV URL, and account disabling.
- `/auth/forgot-password` and `/auth/reset-password`: recovery lifecycle.

Long-running commands return a task ID and optional duplicate marker.
All lookups are constrained to the authenticated owner.

`PUT /jobs/{job_id}/documents` persists user edits to the generated CV and
cover letter and rebuilds both PDFs. `POST /applications` adds that document
set to the board and is idempotent for a user and job posting.
Document regeneration accepts `cv`, `cover_letter`, or `all`; partial scopes
generate and replace only the requested document while preserving the other
document text and PDF.

## Server-Sent Notifications

`GET /api/v1/notifications/stream` returns `text/event-stream`. Authentication
uses the ordinary `Authorization: Bearer` header. Each notification event has
an SSE `id` plus `event`, `title`, `body`, `payload`, and `created_at` data.
Heartbeat comments keep intermediaries from closing idle connections.
`Last-Event-ID` replays missed notification-table rows before live Redis
pub/sub delivery. Proxies must disable response buffering for this route.
