# Frontend Routes

Kaziro uses Next.js App Router route groups under `frontend/src/app/`.

```text
src/app/
├── layout.tsx
├── globals.css
├── (marketing)/
│   └── page.tsx
├── (auth)/
│   ├── login/page.tsx
│   ├── signup/page.tsx
│   └── confirm-email/page.tsx
├── (onboarding)/
│   ├── layout.tsx
│   └── onboarding/
│       ├── page.tsx
│       └── summary/page.tsx
└── (app)/
    └── layout.tsx
```

## Route Groups

| Group | Access | Purpose |
| --- | --- | --- |
| `(marketing)` | Public | Landing and public product pages. |
| `(auth)` | Public | Login, signup, and email confirmation. |
| `(onboarding)` | Authenticated | Profile, CV, and job-preference setup. |
| `(app)` | Authenticated | Dashboard, notifications, jobs, applications, and settings. |

## SEO

- Marketing routes are indexable.
- Auth, onboarding, and app routes should not be indexed.
- Page metadata belongs in the relevant route segment.

## Loading And Errors

- Use route-level loading UI for async page work.
- Use local error states for recoverable API failures.
- Keep protected layouts from rendering query-dependent children until auth
  state is known.
