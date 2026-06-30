# ADR-0007: Next.js And React For The Frontend

**Status**: Accepted
**Date**: 2026-06-29
**Tags**: frontend, nextjs, react

## Context

Kaziro needs a frontend that supports public marketing pages, authentication,
onboarding, authenticated dashboards, API-driven workflows, and deployment on
Vercel.

## Decision

Use Next.js App Router with React, TypeScript, Tailwind CSS, DaisyUI, TanStack
Query, and Zustand.

## Consequences

- Route groups separate public, auth, onboarding, and app surfaces.
- Server Components are the default rendering model.
- Interactive leaves use client components.
- API access stays behind `src/lib/api/`.
- Frontend checks are `pnpm lint`, `pnpm typecheck`, and `pnpm build`.

## Alternatives Considered

- Plain React with Vite: simpler, but less aligned with Vercel routing and
  deployment features.
- A custom server-rendered frontend: more operational work for little product
  benefit.
