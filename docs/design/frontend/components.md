# Frontend Components

**Status**: Active
**Last updated**: 2026-04-22
**Source**: Section 7.2 of [`Kaziro_Design_Document.pdf`](../../../Kaziro_Design_Document.pdf)
**Related**: [`../../architecture/05-frontend-architecture.md`](../../architecture/05-frontend-architecture.md)

Reusable UI components live in `frontend/src/lib/components/`. Each
component is a single `.svelte` file with `<script lang="ts">`.

## Naming & file layout

- PascalCase filenames: `JobCard.svelte`, `EvaluationPanel.svelte`.
- Folder per domain: `components/jobs/`, `components/applications/`,
  `components/ui/` (generic primitives).
- Co-located optional `*.test.ts` for component tests.

## Component contracts

Every component declares its props with Svelte 5 runes:

```svelte
<script lang="ts">
  import type { JobPosting, Classification } from '$lib/types/jobs';

  let {
    job,
    classification,
    onClick,
  }: {
    job: JobPosting;
    classification: Classification;
    onClick?: (id: string) => void;
  } = $props();
</script>
```

Never use `export let` (Svelte 4 syntax). Always destructure `$props()`
with full TypeScript annotation.

## Generic primitives — `lib/components/ui/`

| Component       | Props                                                                              | Notes                                                  |
| --------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------ |
| `Button`        | `variant: 'primary' \| 'secondary' \| 'ghost' \| 'danger'`, `loading?`, `icon?`    | Wraps DaisyUI `btn`; disables on `loading`             |
| `Badge`         | `variant: 'success' \| 'warning' \| 'error' \| 'info'`, `label`                    | Always carries text — colour is never the sole signal  |
| `Modal`         | `open: boolean`, `onClose`, slot `header`, default slot, slot `footer`             | Focus-trapped; ESC closes                              |
| `Toast`         | `type: 'info' \| 'success' \| 'warning' \| 'error'`, `message`, `duration`         | Rendered into root `<ToastContainer>`                  |
| `Skeleton`      | `width`, `height`, `rounded?`                                                      | Loading placeholder                                    |
| `EmptyState`    | `icon`, `title`, `description`, `cta?`                                             | Used on empty lists                                    |
| `FilterPanel`   | `filters: Record<string, FilterDef>`, `onChange`                                   | Generic filter bar                                     |
| `Pagination`    | `cursor`, `nextCursor`, `onLoadMore`                                               | Cursor pagination control                              |
| `FileUpload`    | `accept: string[]`, `maxSizeMb`, `onUpload(file)`                                  | Drag-drop + file picker                                |

## Domain components — jobs (`components/jobs/`)

| Component             | Purpose                                                                        |
| --------------------- | ------------------------------------------------------------------------------ |
| `JobCard`             | Compact list item: title, company, location, fit badge, score                  |
| `FitBadge`            | Classification badge: `GOOD_FIT` (success), `MAYBE` (warning), `REJECT` (error) |
| `EvaluationPanel`     | Renders `pass1_scores`, `pass2_critique`, `final_feedback` with collapsibles  |
| `ScoreRadar`          | 4-axis radar chart (skills/seniority/domain/comp) using Chart.js              |
| `CompanyBrief`        | Renders `company_summaries` row: mission, values, culture, news                |
| `SearchBar`           | Text input wired to `q` query param + debounced TanStack Query                |

## Domain components — applications (`components/applications/`)

| Component             | Purpose                                                                        |
| --------------------- | ------------------------------------------------------------------------------ |
| `ApplicationCard`     | Kanban / list card: job title, company, status pill, last event date           |
| `KanbanBoard`         | Drag-drop columns by `ApplicationStatus`; uses `pragmatic-drag-and-drop`        |
| `StatusPill`          | Badge variant per `ApplicationStatus`                                          |
| `Timeline`            | Vertical chronological view of `application_events`                            |
| `StatusUpdater`       | Dropdown of valid next statuses (validates state machine client-side)          |
| `DocEditor`           | TipTap-based rich text editor with toolbar                                     |
| `PDFPreview`          | Lazy-loaded `pdfjs-dist` viewer of the saved PDF (signed URL)                  |
| `ActionBar`           | Fixed bottom bar on `/jobs/[id]/apply`: Save, Discard, Mark as Sent            |

## Domain components — onboarding (`components/onboarding/`)

| Component             | Purpose                                                                        |
| --------------------- | ------------------------------------------------------------------------------ |
| `ProfileWizard`       | Multi-step form with progress indicator                                        |
| `JobConfigForm`       | Inputs for keywords, location, salary range, schedule cron                     |
| `SchedulePicker`      | Friendly UI on top of cron — daily / 6-hourly / hourly / custom                |

## Dashboard components (`components/dashboard/`)

| Component             | Purpose                                                                        |
| --------------------- | ------------------------------------------------------------------------------ |
| `StatsBar`            | KPI cards (new jobs, good fits, sent, pending review)                          |
| `ActivityFeed`        | Most-recent 20 events from evaluations + applications                           |
| `PipelineStatus`      | Live-updating pipeline progress (count of jobs in each stage)                  |

## Composition rules

- **Single responsibility**: a component should do one thing. If it grows
  past ~150 LOC, extract subcomponents.
- **No business logic in components**: data fetching uses TanStack Query
  hooks; transformations live in `$lib/utils/`.
- **Server state via props or hooks** — never load directly from `fetch`.
- **Local state via runes** (`$state`) — never `writable()`.
- **Derived state via `$derived`** — never `derived()` from
  `svelte/store`.
- **Side effects via `$effect`** — and always clean up in the return
  function.

## Accessibility checklist for every component

- [ ] All interactive elements are `<button>` (actions) or `<a>`
      (navigation), never `<div>` with click handlers.
- [ ] All `<input>` has an associated `<label>` (or `aria-labelledby`).
- [ ] Focus management: modals trap focus; route changes restore focus to
      `<main>`.
- [ ] Colour is never the sole signal — always paired with text or icon.
- [ ] Keyboard navigation works (`Tab`, `Enter`, `ESC`, arrow keys for
      drag-drop fallback).
- [ ] `aria-live="polite"` on the pipeline status pane and toast container.

## Adding a new component — checklist

1. Decide the right folder (`ui/`, `jobs/`, `applications/`, etc.).
2. Create `<Name>.svelte` with `<script lang="ts">` and typed `$props()`.
3. Use Tailwind utility classes only — no `<style>` blocks unless
   absolutely unavoidable.
4. Cover keyboard interaction and a11y (see checklist).
5. Add Storybook story (or screenshot in PR) for the visual review.
6. Add a Vitest unit test if the component carries logic.
7. Update this doc table.
