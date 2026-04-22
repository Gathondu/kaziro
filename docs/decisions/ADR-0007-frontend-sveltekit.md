# ADR-0007: SvelteKit for the frontend

**Status**: Accepted
**Date**: 2026-04-22
**Deciders**: Founding engineering team
**Tags**: frontend

## Context and problem statement

Kaziro's frontend is a content-heavy SaaS dashboard with:

- File-based routing across ~10 routes.
- Real-time job/application notifications via WebSocket.
- A small team (1-2 engineers), so DX matters.
- A backend that owns all data via REST + WebSocket — we don't need a
  full-stack framework that does its own DB.

> "What frontend framework do we use?"

## Decision drivers

- Small bundle size + fast TTI (signed-in dashboards must feel snappy).
- Minimal boilerplate; one obvious way to do things.
- First-class TypeScript.
- File-based routing.
- Native server-side rendering (SEO + faster first paint on landing
  pages).
- Strong components story — we render PDFs, WYSIWYG editors, charts.
- Reactive primitives that don't require a state-management library for
  simple cases.

## Considered options

1. **SvelteKit** with **Svelte 5 (runes)**.
2. **Next.js** (React + App Router).
3. **Nuxt** (Vue 3 + Nitro).
4. **Remix**.

## Decision outcome

**Chosen option**: SvelteKit + Svelte 5.

Svelte's compiled output is tiny (no runtime VDOM), the runes-based
reactivity is the most ergonomic in the field, and SvelteKit gives us
file-based routing + SSR + API routes (which we use sparingly — backend
owns most data). Tailwind + DaisyUI + TanStack Query round out the stack
with proven primitives.

### Positive consequences

- Smaller bundles → faster pages, especially on mobile.
- Runes (`$state`, `$derived`, `$effect`) cover most local-state needs
  without a separate state-management library.
- File-based routing keeps onboarding low.
- SSR for landing/marketing pages is one config flag.
- TanStack Query handles server state — clean separation from runes-driven
  UI state.

### Negative consequences

- Smaller ecosystem than React — some niche libraries don't have Svelte
  ports (we wrap them, or we choose differently).
- Hiring pool for Svelte is smaller than React. Mitigated by Svelte's
  short ramp-up time.
- Svelte 5 runes are recent; some community examples still use Svelte 4
  patterns. We standardise on runes per
  [`.cursor/rules/003-frontend.mdc`](../../.cursor/rules/003-frontend.mdc).

## Pros and cons of the options

### Option 1 — SvelteKit + Svelte 5

- **Pros**: Tiny bundles; runes; SSR; great DX.
- **Cons**: Smaller ecosystem; smaller hiring pool.

### Option 2 — Next.js + React

- **Pros**: Industry standard; massive ecosystem; biggest hiring pool.
- **Cons**: Bigger bundles; React's state-management story is more
  fragmented; App Router learning curve.

### Option 3 — Nuxt + Vue 3

- **Pros**: Strong DX; SSR; reactive primitives.
- **Cons**: We don't have Vue expertise; smaller community than React.

### Option 4 — Remix

- **Pros**: Excellent forms + nested-routing story.
- **Cons**: React-based bundle weight; we don't need its full-stack data
  model since the backend owns everything.

## Links

- [`docs/architecture/05-frontend-architecture.md`](../architecture/05-frontend-architecture.md)
- [`docs/design/frontend/`](../design/frontend/)
- [`.cursor/rules/003-frontend.mdc`](../../.cursor/rules/003-frontend.mdc)
- [SvelteKit](https://kit.svelte.dev/)
