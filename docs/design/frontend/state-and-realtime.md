# Frontend State And Realtime

Kaziro separates server state, local UI state, and realtime notifications.

| State type | Tool | Examples |
| --- | --- | --- |
| Server state | TanStack Query | profile, job configs, notifications |
| Local UI state | React state | modal open state, selected tab, draft values |
| Cross-route UI state | Zustand | auth/session cache, onboarding progress, toasts |
| Realtime events | EventSource/WebSocket helper | notification updates, pipeline progress |

## API State

Server state should flow through `src/lib/api/` and TanStack Query. Mutations
invalidate or update the relevant query keys after success.

## Realtime

Realtime connections should be created once per authenticated app shell and
cleaned up when the shell unmounts or auth changes. Components consume updates
through stores or query invalidation rather than opening their own connections.

## Toasts

Toasts are transient UI state. They should be short, actionable, and not used
as the only place an important failure is shown.
