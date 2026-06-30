# ADR-0010: Layered AGENTS.md hierarchy across the monorepo

**Status**: Accepted
**Date**: 2026-04-22
**Deciders**: Founding engineering team
**Tags**: dx, docs, agents

## Context and problem statement

Kaziro will be edited by a mix of humans and AI coding agents (Cursor,
Claude Code, Codex CLI, others). Each agent benefits from a small,
authoritative file at the working-directory root that says:

- What this codebase is.
- Where things live.
- What conventions / rules to follow when editing files here.
- Where to look for deeper context.

The community-emerging convention for this is `AGENTS.md`. The question
is **how many** AGENTS.md files we should ship and **where**.

> "Should we have a single root AGENTS.md, or layered AGENTS.md files
> per workspace and per domain?"

## Decision drivers

- Different stacks need different rules; backend conventions do not apply
  to frontend files and vice versa.
- Agent workflow modules have stack-on-top-of-stack conventions around
  state classes, prompt rules, and model selection.
- A single mega-AGENTS.md becomes a wall of text; agents (and humans)
  scan less of it.
- Most agent tools (Cursor, Claude Code) honour the **nearest**
  AGENTS.md as authoritative — layering naturally narrows scope as you
  descend into the tree.
- We already maintain detailed [`.cursor/rules/`](../../.cursor/rules/);
  AGENTS.md should be a thin pointer into rules + docs, not duplicate
  them.

## Considered options

1. **Layered AGENTS.md** — root + per-workspace + per-domain.
2. **Single root AGENTS.md** — one file at the root that covers
   everything.
3. **No AGENTS.md** — rely entirely on `.cursor/rules` (Cursor-specific
   tool).

## Decision outcome

**Chosen option**: Layered AGENTS.md.

The hierarchy:

| Path                          | Scope                                              |
| ----------------------------- | -------------------------------------------------- |
| `AGENTS.md`                   | Project identity, monorepo map, where to run what. |
| `backend/AGENTS.md`           | Django, Django Ninja, Celery, DB, observability rules.  |
| `frontend/AGENTS.md`          | Next.js, React, Tailwind, TanStack Query, a11y.   |

Each AGENTS.md:

- Is short (< 200 lines) and links into the matching `.cursor/rules` and
  `docs/` files.
- Points up to its parent AGENTS.md so inherited context is reachable.
- Is the **nearest** AGENTS.md for any file under it, so editing-tools
  pick it up automatically.

### Positive consequences

- Agents always get scoped guidance for the files they're editing.
- New contributors find the right rules without grep'ing the whole repo.
- AGENTS.md stays small and skim-able — easy to keep current.
- Tool-agnostic: works with Cursor, Claude Code, Codex CLI, GitHub
  Copilot, plain humans.
- `.cursor/rules` remain the source of truth for detailed enforcement;
  AGENTS.md is the human-readable "front door".

### Negative consequences

- More files to keep in sync — drift between AGENTS.md and
  `.cursor/rules` is the failure mode. We mitigate by linking every
  AGENTS.md to the rules it summarises and reviewing both in the same
  PRs.
- A new contributor has to understand *which* AGENTS.md applies to their
  current edit. The nearest-wins convention is well-understood, but we
  call it out explicitly in the root AGENTS.md.

## Pros and cons of the options

### Option 1 — Layered AGENTS.md

- **Pros**: Scoped; small; tool-agnostic; explicit hierarchy.
- **Cons**: More files; drift risk.

### Option 2 — Single root AGENTS.md

- **Pros**: Single source of truth; no drift.
- **Cons**: Becomes huge; agents skim less; backend rules pollute
  frontend context and vice versa.

### Option 3 — No AGENTS.md, only `.cursor/rules`

- **Pros**: Zero duplication.
- **Cons**: Cursor-specific; other agents (Claude Code, Codex CLI) don't
  read those by default. We lose the universal "where do I start?" file.

## Links

- [`AGENTS.md`](../../AGENTS.md) (root)
- [`backend/AGENTS.md`](../../backend/AGENTS.md)
- [`frontend/AGENTS.md`](../../frontend/AGENTS.md)
- [`.cursor/rules/`](../../.cursor/rules/)
- [ADR-0009: Monorepo layout](ADR-0009-monorepo-layout.md)
