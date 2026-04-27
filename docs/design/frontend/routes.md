# Frontend Routes

**Status**: Active
**Last updated**: 2026-04-27
**Source**: Section 7.1 of [`Kaziro_Design_Document.pdf`](../../../Kaziro_Design_Document.pdf)
**Related**: [`../../architecture/05-frontend-architecture.md`](../../architecture/05-frontend-architecture.md)

SvelteKit file-based routing tree under `frontend/src/routes/`.

## Tree

```
src/routes/
├── +layout.svelte                 # Auth gate, top nav, toast container
├── +layout.server.ts              # Root layout load: `appearance` cookie (default `system` → OS preference)
├── +error.svelte                  # Global error fallback
├── (marketing)/                   # `/`, `/privacy`, `/terms` — inherits `<html data-theme>` (same as app); `data-marketing-surface` tweaks light-terracotta text only
│   ├── +layout.svelte
│   ├── +page.server.ts            # `/` SSR redirect if authed; SEO data
│   ├── +page.svelte               # Landing
│   ├── privacy/+page.svelte
│   └── terms/+page.svelte
├── (auth)/                        # `noindex` in `+layout.svelte`
│   ├── +layout.svelte
│   ├── login/+page.svelte
│   ├── signup/+page.svelte
│   └── forgot-password/+page.svelte
├── (onboarding)/                  # `noindex` in `+layout.svelte`
│   ├── +layout.svelte
│   └── onboarding/                # step routes (about-you, cv, config, …)
├── (app)/                         # Auth-gated route group (`noindex` in layout `<svelte:head>`)
│   ├── +layout.svelte             # Sidebar nav, WS subscription mount
│   ├── dashboard/
│   │   └── +page.svelte           # KPIs + activity feed
│   ├── jobs/
│   │   ├── +page.svelte           # Filterable list
│   │   ├── +page.ts               # initial load: list jobs
│   │   └── [id]/
│   │       ├── +page.svelte       # Detail: job + evaluation + company brief
│   │       ├── +page.ts
│   │       └── apply/
│   │           ├── +page.svelte   # Editor for tailored CV + cover letter
│   │           └── +page.ts
│   ├── applications/
│   │   ├── +page.svelte           # Kanban or list view
│   │   └── [id]/+page.svelte      # Detail with status timeline + downloads
│   └── settings/
│       ├── +page.svelte           # Profile + job configs + notifications
│       └── account/+page.svelte   # Subscription, account deletion
└── api/                           # SvelteKit server endpoints (proxy / BFF if needed)
```

Supabase cookie SSR: [`frontend/src/hooks.server.ts`](../../../frontend/src/hooks.server.ts)
(`createServerClient` from `@supabase/ssr`, per-request `event.locals.supabase`).

### `(marketing)` layout

- Wraps **`/`**, **`/privacy`**, **`/terms`** in `data-theme="terracotta"` so public pages always use the
  light brand palette, independent of the user’s appearance cookie / system theme on `<html>`.

## Route specs

### `/` (landing)

- Public marketing page (hero, features, how-it-works, footer with legal links).
- **`index,follow`** in `<svelte:head>` — primary marketing URL; `/privacy` and `/terms` are also indexable public pages.
- If a **verified** Supabase user is present (cookie session), redirect to
  `/dashboard` from [`(marketing)/+page.server.ts`](../../../frontend/src/routes/(marketing)/+page.server.ts)
  (`getUser()`), not from client-only effects.
- SEO: `<title>`, meta description, canonical, Open Graph, Twitter card, JSON-LD
  `WebSite` — canonical base from `PUBLIC_SITE_URL` when set, else request origin.

### `/privacy` & `/terms`

- Public pages (placeholders until full policy/terms ship) linked from the landing footer.
- **`index,follow`** — indexed alongside `/` as public-facing site pages.

### `/login` & `/signup`

- Under `(auth)/+layout.svelte`: **`noindex,nofollow`** (auth is never indexed).
- Forms posting to Supabase Auth via `@supabase/supabase-js`.
- After success, redirect target is `?redirect=...` query param or
  `/dashboard`.

### `/onboarding/*`

- **`noindex,nofollow`** via `(onboarding)/+layout.svelte` (post-auth flow, not public marketing).
- Full-screen **step flow** (no tab strip): linear profile steps
  `/onboarding/about-you` → `summary` → `domain` → `experience` →
  `skills`, then **CV** (`/onboarding/cv`), then **first job search
  config** (`/onboarding/config`). The `(onboarding)` layout shows **Step
  N of 7** and a progress bar; step panels use a short cross-fade.
- Progress is tracked in `sessionStorage` via `kaziro.onboarding.v1`
  (`saveOnboardingDraft` / `loadOnboardingDraft` in
  `frontend/src/lib/utils/onboarding.ts`). `/onboarding` redirects to
  the correct step from that draft. Profile fields through **skills**
  are held in the draft only; a **single** `PUT /api/v1/profile` runs at
  the end of the skills step (before CV upload).
- **New users** land on `/onboarding/about-you` immediately after
  successful signup. Returning users are not auto-routed into onboarding
  from login; the sidebar **Onboarding** link (`/onboarding`) is kept for
  manual testing.
- Final step submits the first `job_search_config` and redirects to
  `/dashboard`.

### `/(app)/dashboard`

- Stats bar: `New jobs`, `Good fits`, `Applications sent`, `Pending review`.
- Activity feed: last 20 events from `application_events` + recent
  evaluations (server-rendered via `+page.ts` `load`).
- Live counter updates via WebSocket `evaluation_complete` events.

### `/(app)/jobs`

- Filter chips: classification, remote-only, score range.
- Search bar: full-text + semantic (calls `GET /jobs?q=...`).
- Cursor-paginated infinite scroll.
- Job card click → `/(app)/jobs/[id]`.

### `/(app)/jobs/[id]`

- Tabs:
  - **Overview** — title, company, location, salary, full description.
  - **Why this match** — `pass1_scores`, `pass2_critique`,
    `final_feedback` from `job_evaluations`.
  - **About the company** — content from `company_summaries`.
- CTA: "Generate documents" (if not yet generated) or "Open editor".

### `/(app)/jobs/[id]/apply`

- Two-column editor: tailored CV (TipTap) on the left, cover letter
  (TipTap) on the right.
- Right rail: PDF preview (lazy-loaded `pdfjs-dist`).
- Save button persists changes via `PUT /applications/{id}/docs`.
- "Mark as sent" button transitions to `SENT` and redirects to the
  application detail page.

### `/(app)/applications`

- Toggle between **Kanban** (columns by status) and **List** view.
- Kanban columns: DRAFT, SENT, INTERVIEWING, OFFERED, REJECTED.
- Drag-and-drop status changes hit `PUT /applications/{id}/status` —
  invalid transitions surface a toast on 409.

### `/(app)/applications/[id]`

- Status timeline (chronological `application_events`).
- Downloads: tailored CV PDF, cover letter PDF (signed-URL redirect).
- Notes editor.
- Status updater (validates transitions client-side first).

### `/(app)/settings`

- Profile editor (full name, summary, skills, experience, domain, values).
- Job-search-config CRUD (keywords, location, schedule, salary range).
- Notification preferences (toggle email, in-app toasts).

### `/(app)/settings/account`

- Subscription tier display.
- Account deletion (double-confirm + email confirmation).

## Layout responsibilities

| Layout                | Loads / wires up                                                          |
| --------------------- | ------------------------------------------------------------------------- |
| Root `+layout`        | Supabase client, auth state, global toast container, light/dark theme    |
| `(app)/+layout`       | Sidebar nav, WebSocket connect (`notifications.connect(token)`), TanStack QueryProvider |

## Loading & error UX

- `+page.ts` `load` returns a streamed `Promise` for any data over 200 ms;
  `+page.svelte` shows a skeleton placeholder.
- Errors during `load` render `+error.svelte` with a `Retry` button that
  invokes SvelteKit's `invalidate()`.

## SEO & meta

- `<svelte:head>` per page sets `title`, `description`, and (where relevant) `og:image`.
- **Indexable:** **`/`** (full SEO on [`(marketing)/+page.svelte`](../../../frontend/src/routes/(marketing)/+page.svelte)), **`/privacy`**, **`/terms`**
  (`index,follow` + title/description on each page).
- **Not indexable:** `(app)/*`, `(auth)/*`, `(onboarding)/*` — group layouts use `meta name="robots" content="noindex,nofollow"`.

## Adding a new route — checklist

1. Create the file under `src/routes/(app)/<resource>/...`.
2. Add a `+page.ts` `load` if the page needs server data — keep server
   logic minimal, prefer TanStack Query hooks in the component.
3. If the route is auth-required, place under `(app)/` so the layout's
   guard catches it.
4. Add a sidebar entry if user-facing.
5. Update this doc.
