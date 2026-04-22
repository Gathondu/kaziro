# frontend — AGENTS.md

> Scope: everything under `frontend/`. Inherits from the
> [root AGENTS.md](../AGENTS.md). Detailed rules in
> [`.cursor/rules/003-frontend.mdc`](../.cursor/rules/003-frontend.mdc).

## What lives here

```
frontend/
├── AGENTS.md                    ← you are here
├── package.json
├── pnpm-lock.yaml
├── svelte.config.js
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── playwright.config.ts
├── src/
│   ├── app.html
│   ├── app.d.ts
│   ├── app.css                  ← Tailwind directives + base layer
│   ├── routes/                  ← SvelteKit pages (file-based routing)
│   ├── lib/
│   │   ├── components/          ← reusable UI (jobs/, applications/, ui/)
│   │   ├── api/                 ← fetch wrappers (one file per resource)
│   │   ├── stores/              ← runes-based stores (auth, notifications, toast)
│   │   ├── types/               ← TS interfaces mirroring backend Pydantic
│   │   ├── hooks/               ← TanStack Query hooks per resource
│   │   ├── server/              ← server-only code (load fns, server actions)
│   │   └── utils/               ← pure helpers
│   └── params/                  ← SvelteKit route param matchers
├── static/                      ← favicon, og images
└── tests/
    ├── unit/                    ← vitest + @testing-library/svelte
    └── e2e/                     ← Playwright
```

Detail: [`docs/architecture/05-frontend-architecture.md`](../docs/architecture/05-frontend-architecture.md)

- [`docs/design/frontend/`](../docs/design/frontend/).

## Stack reminders

- **Svelte 5 with runes** (`$state`, `$derived`, `$effect`, `$props`).
  Never `$:` reactive statements, never legacy `writable()` stores.
- **SvelteKit 2** for routing, SSR, and the `+layout`/`+page`/`+server`
  conventions.
- **TypeScript strict mode** — `<script lang="ts">` everywhere; no
  `any`.
- **TailwindCSS + DaisyUI** for styling. No inline styles, no per-file
  CSS.
- **TanStack Query** (`@tanstack/svelte-query`) for all server state.
- **Supabase JS** for auth and storage.
- **Native WebSocket** with a thin reconnect wrapper for real-time.

Full deps: [`docs/reference/dependencies.md`](../docs/reference/dependencies.md).

## Cardinal rules summary

These mirror [`.cursor/rules/003-frontend.mdc`](../.cursor/rules/003-frontend.mdc).
Read the rule itself for full detail.

### Reactivity

- `$state()` for local mutable state.
- `$derived()` for computed values (replaces `$:`).
- `$effect()` for side effects (replaces `onMount` for data-driven
  effects).
- `$props()` for component props — always typed.
- Event handlers: `onclick={handler}` (not `on:click`).

### Components

- One component per file. Filename = component name (PascalCase).
- Props typed inline:
  `const { job }: { job: JobPosting } = $props()`.
- Components must not call `fetch()` directly — they receive data via
  props or via a TanStack Query hook from `lib/hooks/`.
- Extract any logic block > 10 lines into a `lib/utils/` helper.
- Never `document.querySelector` or DOM manipulation — bind via Svelte.
- Async work: explicit `loading` and `error` states.

### API client (`lib/api/`)

- Every request goes through `lib/api/client.ts`. The client:
  - Attaches the Supabase JWT.
  - Redirects to `/login` on 401.
  - Throws typed errors `{ code, message }`.
- One file per resource: `jobs.ts`, `applications.ts`, `profile.ts`,
  `configs.ts`.
- API functions are plain async functions, not classes.
- All consumers go through TanStack Query hooks in `lib/hooks/` —
  components don't import from `lib/api/` directly.

### Server state (TanStack Query)

- Query keys are tuples: `['jobs', { status, page }]` — see
  [`docs/design/frontend/state-and-realtime.md`](../docs/design/frontend/state-and-realtime.md).
- Mutations use `createMutation()` with `onSuccess` /
  `onError`; invalidate the affected queries on success.
- Stale times configured per resource — defaults documented in the
  state doc.
- Optimistic updates only when the backend mutation is idempotent.

### Local UI state

- Use runes for local-only UI state (modals open, hover, form values).
- Cross-component state (auth user, notifications) lives in a
  `lib/stores/` module that exports rune-backed singletons.

### Real-time (WebSocket)

- One connection app-wide, managed in `lib/stores/notifications.ts`.
- Components subscribe via the store — never open their own WebSocket.
- The store handles reconnection with exponential backoff and a
  client-side heartbeat.
- Disconnect on app shutdown — connection cleanup is in the root layout
  via `$effect`.
- Surface toasts for `evaluation_complete` and `documents_ready`.

### Styling

- Tailwind utility classes only.
- DaisyUI for form elements, modals, alerts.
- Semantic theme tokens (`primary`, `secondary`, `success`, `warning`,
  `error`) — defined in `tailwind.config.ts`.
- Classification badges: `GOOD_FIT` → `badge-success`, `MAYBE` →
  `badge-warning`, `REJECT` → `badge-error`.
- Never arbitrary values (`w-[347px]`) — use the spacing scale.

### Forms

- Native `<form>` with SvelteKit `use:enhance`.
- Client validation via Zod schemas mirroring backend Pydantic.
- Field-level error display, not just a global banner.
- Disable submit buttons during mutation.
- Reset state via TanStack Query invalidation, not `form.reset()`.

### TypeScript types

- Every API response shape has an interface in `lib/types/`.
- Types mirror backend Pydantic schemas — keep in sync per PR.
- Shared enums in `lib/types/enums.ts` (`Classification`,
  `ApplicationStatus`, etc.).
- `unknown` over `any`. Narrow with type guards.

### Performance

- Initial page data via `+page.ts` `load` — not client-side-only fetch.
- Lazy-load heavy components (PDF viewer, TipTap editor) with dynamic
  `import()`.
- Paginated lists > 100 items use virtual scrolling.
- Images: always `width`, `height`, `alt`.

### Accessibility

- Semantic HTML: `<button>` for actions, `<a>` for navigation.
- Every form input has an associated `<label>`.
- All interactive elements keyboard-accessible.
- Pipeline status regions use `aria-live="polite"`.

## Cardinal rules — anti-patterns

- ❌ `console.log` in committed code (use `lib/utils/logger.ts`).
- ❌ Direct `fetch` outside `lib/api/`.
- ❌ Components opening their own WebSockets.
- ❌ Per-component `<style>` blocks unless unavoidable.
- ❌ Arbitrary Tailwind values.
- ❌ Legacy Svelte 4 patterns (`writable()`, `$:`, `on:click`).
- ❌ `any` in `.ts` / `.svelte` files.

## When you add…

- **A new route** → see the checklist in
  [`docs/design/frontend/routes.md`](../docs/design/frontend/routes.md).
- **A new component** →
  [`docs/design/frontend/components.md`](../docs/design/frontend/components.md).
- **A new API hook** →
  [`docs/design/frontend/state-and-realtime.md`](../docs/design/frontend/state-and-realtime.md).
- **A new env var** → add to `frontend/.env.example` and
  [`docs/reference/env-vars.md`](../docs/reference/env-vars.md).
- **A new dep** → add a row to
  [`docs/reference/dependencies.md`](../docs/reference/dependencies.md).
- **A new real-time event** → checklist in the state doc.

## Local commands

```bash
pnpm install
pnpm dev          # vite dev server with HMR
pnpm build        # production build
pnpm preview      # serve the production build locally
pnpm test         # vitest unit tests
pnpm e2e          # Playwright E2E (assumes backend up)
pnpm lint         # eslint + svelte-check
pnpm format       # prettier
```
