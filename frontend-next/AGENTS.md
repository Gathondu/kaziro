# frontend-next — AGENTS.md

> Scope: everything under `frontend-next/`. Inherits from the root
> [`AGENTS.md`](../AGENTS.md).

## What lives here

This is the parallel Next.js migration frontend. It must not replace the
existing SvelteKit frontend until a later cutover milestone.

## Stack

- Next.js App Router with TypeScript.
- Tailwind CSS + DaisyUI for styling.
- TanStack Query for server state.
- Zustand for small cross-route UI state.
- `lucide-react` for icons.

## Rules

- Use route groups: `(marketing)`, `(auth)`, `(onboarding)`, `(app)`.
- Keep API calls behind `src/lib/api/`.
- Preserve the current backend envelope shape: `{ data, meta, error }`.
- Use Server Components by default and push `"use client"` to interactive leaves.
- Use DaisyUI classes and semantic Tailwind tokens before custom styling.
- No `console.log` in committed code.
