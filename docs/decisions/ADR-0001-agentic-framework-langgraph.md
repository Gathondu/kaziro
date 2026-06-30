# ADR-0001: Use LangGraph as the agentic framework

**Status**: Accepted
**Date**: 2026-04-22
**Deciders**: Founding engineering team
**Tags**: backend, agents

## Context and problem statement

Kaziro's value proposition is the agentic pipeline: parse → evaluate →
research → document. Each agent is non-trivial — the evaluator alone is a
3-pass stateful workflow with conditional branching and error fallbacks.
We need a framework that:

- Manages stateful, multi-node agent workflows.
- Supports conditional branching (retry on parse failure; skip research on
  REJECT classification).
- Integrates with OpenRouter (LLM + embeddings) and external HTTP tools.
- Allows future human-in-the-loop pauses (e.g., user-in-the-loop doc
  edits).
- Is well-supported, observable, and testable.

> "What framework do we use to build and orchestrate the LangGraph
> agents?"

## Decision drivers

- Stateful multi-node graphs with first-class conditional edges.
- Native checkpointing for resume/retry.
- Existing LangChain / LangGraph ecosystem familiarity in the team.
- Active maintenance and community support.
- Observable: easy to bind structured logs and metrics around node
  execution.
- Avoid heavy custom orchestration code.

## Considered options

1. **LangGraph** — graph-based state machine for LLM agents.
2. **CrewAI** — role-based multi-agent collaboration framework.
3. **Raw LLM vendor SDK + custom orchestrator** — no framework; build the
   graph ourselves.
4. **Microsoft Autogen** — multi-agent conversation framework.

## Decision outcome

**Chosen option**: LangGraph.

It models each agent as a `StateGraph` with explicit nodes and conditional
edges. State is a Pydantic model — fully typed and serializable. The
existing parser/evaluator/research/document agents already use LangGraph
in [`backend/apps/pipeline/`](../../backend/apps/pipeline/) and the pattern has proven to
fit the problem cleanly.

### Positive consequences

- Conditional branching (parser retry, evaluator error sink, research
  cache short-circuit) is one line of code per route.
- Pydantic state is testable — we can unit-test individual nodes by
  passing a hand-crafted state.
- Native LangChain integration means `ChatOpenRouter` (via
  `langchain-openrouter`), `OpenAIEmbeddings` against OpenRouter's
  OpenAI-compatible embeddings API, structured-output binders, and tool nodes
  are available out of the box.
- Future human-in-the-loop is supported with `interrupt()` + breakpoints
  — useful for the doc-editor flow in V2.

### Negative consequences

- Requires LangChain ecosystem dependencies (heavier install footprint).
- LangGraph API is still evolving; we accept periodic upgrade churn.
- Debugging graph execution requires familiarity with the LangGraph
  runtime — onboarding cost for new contributors.

## Pros and cons of the options

### Option 1 — LangGraph

- **Pros**: Stateful, conditional, checkpointable; integrates with
  LangChain; matches the agent-design vocabulary in our docs; supports
  HITL.
- **Cons**: LangChain dep; evolving API.

### Option 2 — CrewAI

- **Pros**: High-level "crew of agents" abstraction; quick to prototype.
- **Cons**: Optimised for collaborative reasoning, not stateful graphs.
  Conditional branching and per-node retry are weaker.

### Option 3 — Raw vendor SDK + custom orchestrator

- **Pros**: Zero framework dep; minimal install footprint.
- **Cons**: We rewrite stateful graphs, conditional edges, retries,
  checkpointing, observability. Time we shouldn't spend.

### Option 4 — Microsoft Autogen

- **Pros**: Strong multi-agent conversation patterns.
- **Cons**: Same as CrewAI — workflow-centric, not graph-centric.
  Heavier than needed for sequential pipelines.

## Links

- [`docs/architecture/02-agentic-pipeline.md`](../architecture/02-agentic-pipeline.md)
- [`docs/design/agents/`](../design/agents/)
- [`backend/apps/pipeline/`](../../backend/apps/pipeline/)
- [LangGraph docs](https://langchain-ai.github.io/langgraph/)
