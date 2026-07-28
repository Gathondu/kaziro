# ADR-0006: Three-pass evaluator pipeline (draft / critic / judge)

**Status**: Accepted
**Date**: 2026-04-22
**Deciders**: Founding engineering team
**Tags**: backend, agents, llm

## Context and problem statement

The Evaluator agent decides whether a job is `GOOD_FIT`, `MAYBE`, or
`REJECT` for a user. This single decision triggers expensive downstream
work (research + document generation) for `GOOD_FIT` jobs. False positives
cost real money (LLM calls + Scrapper research) and false negatives cost the user
opportunities. Calibration matters.

Single-pass evaluation with one LLM call has known weaknesses:

- LLMs are over-confident on edge cases.
- Single-pass output can miss nuanced misalignment (e.g., right title,
  wrong location).
- No mechanism to challenge or correct the initial judgement.

> "How do we make the GOOD_FIT decision robust enough to gate downstream
> spend?"

## Decision drivers

- Reduce false positives that trigger costly research + doc generation.
- Reduce false negatives that hide good jobs from the user.
- Stay under a per-evaluation cost budget (≤ $0.05 / job).
- Provide an auditable rationale per decision (for the user, for debugging).
- Support a future "calibration" test set we can replay.

## Considered options

1. **Single-pass evaluator** — one LLM call returns scores + classification.
2. **Three-pass: draft / critic / judge** — chain-of-thought with explicit
   self-critique.
3. **N-of-M voting** — run the single-pass evaluator N times, majority vote.
4. **Tool-augmented single pass** — give the evaluator tools to look up
   user history before deciding.

## Decision outcome

**Chosen option**: Three-pass — Draft, Critic, Judge.

- **Draft (`gpt-4o`)** scores each dimension and produces an initial
  classification + reasoning.
- **Critic (`gpt-4o`)** reviews the Draft, flagging weak rationale,
  missed signals, or over/under-confidence.
- **Judge (`gpt-4o`)** sees both Draft and Critic outputs and renders
  the final score + classification.

The Critic node is non-fatal: if it fails, the Judge falls back to the
Draft directly (see [`tasks.py`](../../backend/apps/pipeline/tasks.py)).

### Positive consequences

- Calibration in early testing showed materially fewer false positives vs.
  single-pass — the Critic catches "title matches, location mismatch" and
  similar mistakes.
- The Judge produces a final, structured rationale we surface in the UI
  ("Why was this job marked GOOD_FIT?").
- Each pass is independently testable.
- The 3-pass cost (≈ $0.03–$0.05 per job) is within budget; downstream
  work (research + docs) is the dominant cost so this is well-spent.

### Negative consequences

- 3× the LLM calls vs. single-pass — higher latency (~10-15s per job).
- More complex graph; more code to maintain.
- More tokens to log and trace.

## Pros and cons of the options

### Option 1 — Single-pass

- **Pros**: Cheapest; lowest latency.
- **Cons**: Higher false-positive rate; no internal challenge.

### Option 2 — Three-pass (Draft / Critic / Judge)

- **Pros**: Self-correcting; auditable; matches our calibration target.
- **Cons**: 3× LLM cost / latency.

### Option 3 — N-of-M voting

- **Pros**: Reduces variance through repetition.
- **Cons**: Does not surface a useful Critic rationale; same variance, just
  averaged; harder to explain in the UI.

### Option 4 — Tool-augmented single pass

- **Pros**: Could ground decisions in user history.
- **Cons**: Tool latency adds variance; doesn't address LLM over-confidence
  on the core scoring.

## Links

- [`docs/design/agents/evaluator-agent.md`](../design/agents/evaluator-agent.md)
- [`backend/apps/pipeline/tasks.py`](../../backend/apps/pipeline/tasks.py)
