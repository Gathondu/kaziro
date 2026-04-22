# Frontend State & Real-time

**Status**: Active
**Last updated**: 2026-04-22
**Source**: Sections 7.3 and 7.4 of [`Kaziro_Design_Document.pdf`](../../../Kaziro_Design_Document.pdf)
**Related**: [`../../architecture/05-frontend-architecture.md`](../../architecture/05-frontend-architecture.md), [`../../architecture/04-api-design.md`](../../architecture/04-api-design.md)

## 1. State categories

| Category         | Tool                                          | Examples                                              |
| ---------------- | --------------------------------------------- | ----------------------------------------------------- |
| Server state     | **TanStack Query**                            | Job list, evaluation, application docs               |
| Local UI state   | **Svelte 5 runes** (`$state`)                 | Modal open, filter values, selected tab              |
| Derived state    | **`$derived`**                                | Filtered list, computed score breakdown              |
| Side effects     | **`$effect`** with cleanup                    | Subscribe to WS, set up timers, scroll into view     |
| Auth state       | **Supabase JS** + a thin store wrapper        | Current user, JWT, session refresh                   |
| Real-time events | **WebSocket** managed by `lib/stores/notifications.ts` | Pipeline events, toast triggers           |

Svelte 4 stores (`writable`, `readable`, `derived`) are **forbidden** for
new code — see [`.cursor/rules/003-frontend.mdc`](../../../.cursor/rules/003-frontend.mdc).

## 2. TanStack Query patterns

### 2.1 Query keys

Always use stable, structured keys: `['<resource>', ...filters]`.

```typescript
const jobs = createQuery({
  queryKey: ['jobs', { classification, minScore, cursor }],
  queryFn: () => listJobs({ classification, minScore, cursor }),
});
```

### 2.2 Mutations + invalidation

```typescript
const markSent = createMutation({
  mutationFn: (id: string) => applicationsApi.markSent(id),
  onSuccess: (_, id) => {
    queryClient.invalidateQueries({ queryKey: ['applications'] });
    queryClient.invalidateQueries({ queryKey: ['application', id] });
    toast.success('Marked as sent');
  },
});
```

Never mutate the cache by hand. Always invalidate or `setQueryData` with
typed data shaped from the server response.

### 2.3 Optimistic updates

Used sparingly — only for low-stakes UI like toggling a notification
preference. For status transitions (which can be rejected by the backend
state machine), prefer pessimistic updates so the UI never shows an
illegal state.

### 2.4 Stale time defaults

Configured in `lib/api/queryClient.ts`:

| Resource group        | `staleTime`  | Reason                                      |
| --------------------- | ------------ | ------------------------------------------- |
| Job list / detail     | 60 s         | Pipeline events trigger explicit invalidate |
| Evaluation            | 5 min        | Rarely changes once persisted               |
| Application list      | 30 s         | User-driven changes refetch on focus        |
| Application detail    | 60 s         |                                             |
| Profile               | 5 min        |                                             |
| Company brief         | 24 h         | Cached up to 30 days server-side anyway     |

## 3. Auth store (sketch)

```typescript
// lib/stores/auth.ts
import { createClient, type Session } from '@supabase/supabase-js';

export const supabase = createClient(env.VITE_SUPABASE_URL, env.VITE_SUPABASE_ANON_KEY);

let session = $state<Session | null>(null);

export function getSession() { return session; }
export function getJwt(): string | undefined { return session?.access_token; }

supabase.auth.onAuthStateChange((_event, newSession) => {
  session = newSession;
});
```

The API client reads `getJwt()` on every request. On 401, it clears the
session and pushes `/login?redirect=...`.

## 4. Real-time WebSocket store

### 4.1 Endpoint contract

Server: `WS /api/v1/ws/notifications?token=<JWT>`
Direction: server → client only.

Message shapes:

```typescript
type NotificationMessage =
  | { type: 'fetch_complete';      config_id: string;        new_jobs: number }
  | { type: 'evaluation_complete'; job_posting_id: string;   classification: Classification; score: number }
  | { type: 'research_complete';   job_posting_id: string }
  | { type: 'documents_ready';     job_evaluation_id: string; quality_passed: boolean };
```

### 4.2 Connection lifecycle

A single WebSocket per session, owned by `lib/stores/notifications.ts`.

```typescript
let socket = $state<WebSocket | null>(null);
let connected = $state(false);
let backoffMs = $state(1000);

const handlers = new Set<(msg: NotificationMessage) => void>();

export function connect(token: string) {
  if (socket && socket.readyState !== WebSocket.CLOSED) return;
  socket = new WebSocket(`${env.VITE_API_URL}/ws/notifications?token=${token}`);

  socket.addEventListener('open', () => {
    connected = true;
    backoffMs = 1000;
  });

  socket.addEventListener('message', (e) => {
    const msg = JSON.parse(e.data) as NotificationMessage;
    handlers.forEach((h) => h(msg));
  });

  socket.addEventListener('close', () => {
    connected = false;
    setTimeout(() => connect(token), backoffMs);
    backoffMs = Math.min(backoffMs * 2, 30_000);
  });
}

export function disconnect() {
  socket?.close();
  socket = null;
  connected = false;
}

export function subscribe(handler: (msg: NotificationMessage) => void) {
  handlers.add(handler);
  return () => handlers.delete(handler);
}
```

### 4.3 Component usage

Components subscribe via `$effect` with cleanup — they never open their
own WebSocket.

```svelte
<script lang="ts">
  import { subscribe } from '$lib/stores/notifications';
  import { toast } from '$lib/stores/toast';

  $effect(() => {
    const unsub = subscribe((msg) => {
      if (msg.type === 'evaluation_complete') {
        toast.info(`New evaluation: ${msg.classification} (${msg.score}/10)`);
        queryClient.invalidateQueries({ queryKey: ['jobs'] });
      } else if (msg.type === 'documents_ready') {
        toast.success('Documents ready', {
          action: { label: 'Open editor', href: `/applications/${msg.job_evaluation_id}` },
        });
        queryClient.invalidateQueries({ queryKey: ['applications'] });
      }
    });

    return unsub;
  });
</script>
```

### 4.4 Reconnection strategy

- Exponential backoff starting at 1 s, capped at 30 s.
- Reset on successful `open`.
- On `401`-equivalent (token expired): refresh the session via Supabase
  client, re-call `connect(newToken)`.

### 4.5 Heartbeat

Server may send pings every 30 s; the browser's WebSocket implementation
auto-replies with pongs. No client-side action required. If no message for
>60 s, force a `socket.close()` to trigger reconnection.

## 5. Toast store

A small singleton consumed by both manual user actions (mutation success)
and the WS handlers above.

```typescript
type Toast = { id: string; type: 'info' | 'success' | 'warning' | 'error';
               message: string; action?: { label: string; href: string }; duration?: number };

let toasts = $state<Toast[]>([]);

export const toast = {
  info(message: string, opts?: Partial<Toast>) { push({ type: 'info', message, ...opts }); },
  success(message: string, opts?: Partial<Toast>) { push({ type: 'success', message, ...opts }); },
  warning(message: string, opts?: Partial<Toast>) { push({ type: 'warning', message, ...opts }); },
  error(message: string, opts?: Partial<Toast>) { push({ type: 'error', message, ...opts }); },
};
```

`<ToastContainer>` is mounted in the root `+layout.svelte` and renders the
list with `aria-live="polite"`.

## 6. Form state

- Native `<form>` + `use:enhance` from SvelteKit.
- Client validation via Zod schemas mirroring backend Pydantic schemas.
- Field-level errors via local `$state<Record<string, string>>`.
- On submit: disable submit button (`mutation.isPending`), show inline
  spinner, surface server validation errors per field.

## 7. URL as state

Filters, search query, and pagination cursor live in URL search params via
SvelteKit's `$page.url.searchParams`. This makes shareable links and
back-button-friendly navigation work for free.

```typescript
let classification = $derived($page.url.searchParams.get('classification') ?? 'GOOD_FIT');
```

## 8. Adding a new real-time event — checklist

1. Add the message shape to the `NotificationMessage` union.
2. Backend: emit via `services/notifications.notify_user(...)` from the
   right agent / orchestrator stage.
3. Document the new event in
   [`../../architecture/04-api-design.md`](../../architecture/04-api-design.md#36-notifications-websocket).
4. Frontend: in the relevant page or layout, add a `$effect` that
   `subscribe`s to the new event and updates UI / invalidates queries.
5. Add a Vitest unit test for the handler.
