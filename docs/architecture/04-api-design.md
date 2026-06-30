# API Design

**Status**: Active
**Last updated**: 2026-06-29

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
