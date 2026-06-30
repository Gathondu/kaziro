# frontend — AGENTS.md

> Scope: everything under `frontend/`. Inherits from the root
> [`AGENTS.md`](../AGENTS.md).

## Stack

- Next.js App Router with TypeScript.
- React Server Components by default.
- Tailwind CSS + DaisyUI for styling.
- TanStack Query for server state.
- Zustand for small cross-route UI state.
- `lucide-react` for icons.

## Rules

- Use route groups: `(marketing)`, `(auth)`, `(onboarding)`, `(app)`.
- Keep API calls behind `src/lib/api/`.
- Preserve the backend envelope shape: `{ data, meta, error }`.
- Push `"use client"` to interactive leaves.
- Use DaisyUI classes and semantic Tailwind tokens before custom styling.
- Use accessible form labels, focus states, and loading/error states.
- No `console.log` in committed code.

## Commands

```bash
pnpm install
pnpm dev
pnpm lint
pnpm typecheck
pnpm build
pnpm test:e2e
```
