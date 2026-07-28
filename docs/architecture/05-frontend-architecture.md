# Frontend Architecture

**Status**: Active
**Last updated**: 2026-06-29
**Related ADRs**: [ADR-0007](../decisions/ADR-0007-nextjs-react-frontend.md)

## Tech Stack

| Layer | Choice |
| --- | --- |
| Framework | Next.js App Router |
| UI | React, TypeScript |
| Styling | Tailwind CSS, DaisyUI |
| Server state | TanStack Query |
| Client state | Zustand |
| Validation | Zod |
| Icons | lucide-react |
| Testing | Playwright for end-to-end flows |

## Folder Structure

```text
frontend/src/
├── app/
│   ├── (marketing)/
│   ├── (auth)/
│   ├── (onboarding)/
│   └── (app)/
├── components/
│   ├── auth/
│   ├── forms/
│   ├── notifications/
│   ├── onboarding/
│   ├── providers/
│   └── ui/
└── lib/
    ├── api/
    ├── forms/
    └── stores/
```

## Rendering

- Use Server Components by default.
- Use `"use client"` only for browser APIs, local interactivity, stores, or
  TanStack Query hooks.
- Keep protected layouts gated on authenticated state before loading
  dashboard data.

## Data Access

All API calls go through `src/lib/api/`. The frontend expects the backend
envelope shape `{ data, meta, error }` and should surface errors through
domain-specific UI states rather than raw exceptions.

## UX Rules

- Marketing routes are public and indexable.
- Auth and onboarding routes are not indexable.
- Application routes are authenticated.
- Forms should provide field-level errors, pending states, and recovery paths.
- Reusable controls belong in `src/components/ui/`.
- Generated CV and cover-letter review uses one shared editable documents
  modal from job and application details. Jobs with documents are added
  directly to the application board; the board detail focuses on status,
  private notes, timeline, and reopening the documents modal.
