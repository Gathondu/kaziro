# Frontend State And Realtime

Kaziro separates server state, local UI state, and realtime notifications.

| State type | Tool | Examples |
| --- | --- | --- |
| Server state | TanStack Query | profile, job configs, notifications |
| Local UI state | React state | modal open state, selected tab, draft values |
| Cross-route UI state | Zustand | auth/session cache, onboarding progress, toasts |
| Realtime events | Fetch-based SSE client | notification updates, pipeline progress |

## API State

Server state should flow through `src/lib/api/` and TanStack Query. Mutations
invalidate or update the relevant query keys after success.

## Realtime

The authenticated app shell opens `GET /api/v1/notifications/stream` with the
normal bearer header. The server replays durable notifications after
`Last-Event-ID`, then switches to the user's Redis pub/sub channel. Event IDs
deduplicate replay and live delivery. The client reconnects with bounded
backoff, updates the bell and toast surface, and invalidates affected TanStack
Query keys. The connection is aborted when the shell unmounts or auth changes.

## Toasts

Toasts are transient UI state. They should be short, actionable, and not used
as the only place an important failure is shown.
