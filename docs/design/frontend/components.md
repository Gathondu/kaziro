# Frontend Components

Components live under `frontend/src/components/` and use React with
TypeScript.

## Conventions

- Use PascalCase filenames for components.
- Keep components focused on rendering and interaction.
- Keep API calls in `src/lib/api/`.
- Keep reusable form helpers in `src/lib/forms/`.
- Use `lucide-react` icons where available.
- Avoid `any`; type props and event handlers.

## Component Areas

| Directory | Purpose |
| --- | --- |
| `auth/` | Login, signup, and confirmation UI. |
| `forms/` | Shared field controls and form helpers. |
| `notifications/` | Notification surfaces and controls. |
| `onboarding/` | Onboarding flow components. |
| `providers/` | App-level providers such as TanStack Query. |
| `ui/` | Reusable primitives. |

## State And Effects

- Use props for parent-owned state.
- Use local React state for component-only interaction.
- Use Zustand for small cross-route UI state.
- Use TanStack Query for server state and mutations.
- Use effects only for synchronization with browser APIs or subscriptions.

## Accessibility

- Prefer semantic HTML.
- Every form input needs a label.
- Buttons must have clear accessible names.
- Loading and error states must be visible and understandable.
