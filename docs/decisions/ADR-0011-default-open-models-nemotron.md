# ADR-0011: Use Nemotron as the default OpenRouter model family

**Status**: Accepted
**Date**: 2026-05-27
**Deciders**: Kaziro maintainers
**Tags**: backend | agents | data

## Context and problem statement

Kaziro's agent prompts were originally written around strong proprietary
OpenAI chat models. The project now needs a local-first, cost-conscious default
that works well through OpenRouter while preserving the existing LangGraph and
LangChain integration.

> "Which default LLM and embedding model should Kaziro use for MVP agent runs?"

## Decision drivers

- Must keep using OpenRouter-compatible chat and embedding calls.
- Must improve prompt reliability for open-source instruction models.
- Must keep vector dimensions aligned with PostgreSQL pgvector columns.
- Must avoid introducing a second model provider SDK in the pipeline.

## Considered options

1. **Keep OpenAI defaults** - retain `gpt-4o` / `gpt-4o-mini` and
   `text-embedding-3-small`.
2. **Switch defaults to NVIDIA Nemotron on OpenRouter** - use
   `nvidia/nemotron-3-super-120b-a12b:free` for chat and
   `nvidia/llama-nemotron-embed-vl-1b-v2:free` for embeddings.
3. **Make every stage model mandatory in environment config** - remove
   defaults and require operators to choose models explicitly.

## Decision outcome

**Chosen option**: Option 2, because it keeps the existing OpenRouter surface,
supports the current cost goal, and gives Kaziro one consistent open model
family to optimize prompts and tests against.

### Positive consequences

- Defaults match the open-model deployment target.
- Prompt contracts can be stricter and tested against one known behavior class.
- Embedding dimension is explicit at 2048 and checked before pgvector writes.

### Negative consequences

- Existing 1536-dimensional cached embeddings are invalid after migration and
  must be regenerated.
- OpenRouter free-tier model availability and rate limits can change.
- Returning to a 1536-dimensional embedding model would require another schema
  migration or a separate vector column.

## Pros and cons of the options

### Option 1 - Keep OpenAI defaults

- **Pros**: No schema migration; strongest historical prompt behavior.
- **Cons**: Does not match the open-source model target or cost goal.

### Option 2 - Switch defaults to NVIDIA Nemotron on OpenRouter

- **Pros**: Same OpenRouter integration; open-model defaults; 2048-dimensional
  embeddings align with the selected NVIDIA embedding model.
- **Cons**: Requires prompt hardening and a vector-dimension migration.

### Option 3 - Mandatory model env config

- **Pros**: Forces explicit operator choice in every environment.
- **Cons**: Worse local developer experience; does not document a recommended
  baseline for prompt and calibration tests.

## Links

- Related docs: [`docs/architecture/02-agentic-pipeline.md`](../architecture/02-agentic-pipeline.md)
- Related docs: [`docs/reference/env-vars.md`](../reference/env-vars.md)
- Related ADRs: [ADR-0001](ADR-0001-agentic-framework-langgraph.md),
  [ADR-0002](ADR-0002-database-postgres-pgvector.md)
- External reference: <https://openrouter.ai/nvidia/nemotron-3-super-120b-a12b/api>
- External reference: <https://build.nvidia.com/nvidia/llama-nemotron-embed-vl-1b-v2/modelcard>
