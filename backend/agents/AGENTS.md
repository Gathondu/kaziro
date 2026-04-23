# backend/agents — AGENTS.md

> Scope: every LangGraph agent in `backend/agents/`. Inherits from
> [`../AGENTS.md`](../AGENTS.md) and the [root AGENTS.md](../../AGENTS.md).

## What lives here

```
backend/agents/
├── AGENTS.md                  ← you are here
├── __init__.py
├── parser_agent.py            ← raw job → structured JSON + embedding
├── evaluator_agent.py         ← 3-pass scoring (Draft / Critic / Judge)
├── research_agent.py          ← company brief via Firecrawl + LLM
├── document_agent.py          ← tailored CV + cover letter
└── pipeline_orchestrator.py   ← chains the agents end-to-end
```

Per-agent design specs live in [`../../docs/design/agents/`](../../docs/design/agents/).
Pipeline-level overview: [`../../docs/architecture/02-agentic-pipeline.md`](../../docs/architecture/02-agentic-pipeline.md).

## Required file structure

Every agent file (`<role>_agent.py`) must contain exactly these sections,
in order. This is enforced by [`.cursor/rules/001-agents.mdc`](../../.cursor/rules/001-agents.mdc).

1. **Module docstring** — responsibility, framework, model choice.
2. **LLM / embedder initialisation** — module-level singletons. Never
   instantiate inside a node.
3. **Pydantic state class** — `<AgentName>State(BaseModel)`. Always
   includes `error: str | None = None`.
4. **Node functions** — `async def <step>_node(state) -> <AgentName>State`.
5. **Routing functions** — `def route_after_<step>(state) -> str` for
   conditional edges.
6. **Graph builder** — `def build_<role>_graph() -> Any`.
7. **Compiled graph singleton** — `<role>_graph = build_<role>_graph()`.
8. **Public entry point** — `async def run_<role>_agent(...) -> <AgentName>State`.

## State rules

- Inherit from `pydantic.BaseModel` (not `TypedDict`).
- Always include `error: str | None = None`.
- Sensible defaults for every field — state must be constructible with
  minimal args.
- Never mutate state in place. Use `state.model_copy(update={...})`.
- DB-loaded fields (`raw_cv: str = ""`, `evaluations: list[...] = []`)
  default to empty values until a `load_data` node fills them.

## Node rules

- `async def` only.
- First line: `log = logger.bind(<relevant_ids>, node="<node_name>")`.
- Log at `INFO` start and completion. Use `log.exception(...)` on
  failure.
- Wrap core logic in try/except. On failure, return
  `state.model_copy(update={"error": "<short message>"})`.
- Never call other agents from inside a node — only the **pipeline
  orchestrator** chains agents.
- Never make DB calls inside prompt construction. Load data first in a
  `load_data` / `load_context` node.
- Prompts live next to the node that uses them. No shared prompt
  constants module.

## LLM prompt rules

- Every prompt explicitly states the expected output format (JSON
  schema *or* prose).
- For JSON output:
  - Strip markdown fences before `json.loads()`.
  - Include "Respond in this exact JSON format:" with a typed example.
  - Use `temperature=0` for structured extraction (parser, scoring).
- For generative tasks (CV tailoring, cover letters):
  - `temperature=0.3–0.5`.
  - Include an "IMPORTANT RULES" block to prevent hallucination —
    especially "Do not invent any fact not present in the master CV."
- Use `model.with_structured_output(SchemaModel)` (LangChain) when the
  schema is non-trivial — it's safer than parsing free-form JSON.

## Graph rules

- Use `StateGraph` (not `MessageGraph`).
- Single entry point via `graph.set_entry_point(...)`.
- Error paths route to `END` (or to a named `"error_end"` no-op node) —
  never to a dead loop.
- The compiled graph is a module-level singleton — built once at import.
- Conditional edges live in `route_after_<step>` functions; routing is
  pure state inspection (no side effects).

## Model selection

Always read from `settings`:

| Use case                                           | Setting                       | Default                  |
| -------------------------------------------------- | ----------------------------- | ------------------------ |
| Structured extraction (parser)                     | `LLM_MODEL_PARSER`            | `openai/gpt-4o-mini`     |
| Quality reasoning (evaluator, all 3 passes)        | `LLM_MODEL_EVALUATOR`         | `openai/gpt-4o`          |
| Research brief generation                          | `LLM_MODEL_RESEARCH`          | `openai/gpt-4o`          |
| Document generation (CV, cover letter)             | `LLM_MODEL_DOCUMENT`          | `openai/gpt-4o`          |
| Embeddings (`job_postings.embedding`)              | `LLM_EMBEDDING_MODEL`         | `openai/text-embedding-3-small` |

Never hardcode model strings in agent files — use `settings` (values are
[OpenRouter model ids](https://openrouter.ai/models)).

## Naming conventions

- File: `<role>_agent.py` (e.g., `evaluator_agent.py`).
- State class: `<Role>State` (e.g., `EvaluatorState`).
- Node: `<step>_node` (e.g., `pass1_draft_node`).
- Routing: `route_after_<step>` (e.g., `route_after_parse`).
- Entry point: `run_<role>_agent` (e.g., `run_evaluator_agent`).
- Module-level graph: `<role>_graph` (e.g., `evaluator_graph`).

## What NOT to do in agent files

- ❌ Import FastAPI, `APIRouter`, or any HTTP framework.
- ❌ Call other agents — orchestration is the pipeline orchestrator's
  job.
- ❌ `print()` — always `structlog`.
- ❌ Hardcoded user / job / posting IDs.
- ❌ Fire-and-forget async (no awaits) unless intentional and noted.
- ❌ Business logic in routing functions — routing is pure state
  inspection.
- ❌ Hardcoded model strings.
- ❌ Per-call instantiation of `ChatOpenRouter` / `OpenAIEmbeddings` —
  module-level singletons only (construct via `backend.llm.openrouter`).

## Pipeline orchestrator (`pipeline_orchestrator.py`)

The orchestrator is the **only** place agents are chained. Public entry
points kick off either a single-job pipeline or a fan-out across many
jobs.

- Concurrency: `asyncio.Semaphore(N)` to bound parallel evaluator runs.
- Error isolation: each per-job pipeline runs in its own try/except so
  one failure doesn't poison the batch.
- Returns a structured `PipelineSummary` recording per-stage outcomes
  (success / skipped / failed) for logging and the UI.
- Emits WebSocket notifications via the Pub/Sub bridge after each major
  milestone (evaluation done, documents ready).

Detail: [`../../docs/design/agents/pipeline-orchestrator.md`](../../docs/design/agents/pipeline-orchestrator.md).

## Per-agent design docs

| Agent                  | Spec                                                                       |
| ---------------------- | -------------------------------------------------------------------------- |
| Parser                 | [`parser-agent.md`](../../docs/design/agents/parser-agent.md)              |
| Evaluator              | [`evaluator-agent.md`](../../docs/design/agents/evaluator-agent.md)        |
| Research               | [`research-agent.md`](../../docs/design/agents/research-agent.md)          |
| Document               | [`document-agent.md`](../../docs/design/agents/document-agent.md)          |
| Pipeline orchestrator  | [`pipeline-orchestrator.md`](../../docs/design/agents/pipeline-orchestrator.md) |

## Adding a new agent

1. Read the relevant existing agent for the pattern (`parser_agent.py`
   is the simplest reference).
2. Create `backend/agents/<role>_agent.py` following the eight-section
   structure.
3. Write the design doc at `docs/design/agents/<role>-agent.md`
   (purpose, state, nodes, routing, failure modes, testing).
4. Add tests at `backend/tests/agents/test_<role>_agent.py` —
   per-node unit tests + a graph-level integration test with a VCR
   cassette.
5. Wire the agent into the pipeline orchestrator if it's a pipeline
   stage.
6. Update [`docs/architecture/02-agentic-pipeline.md`](../../docs/architecture/02-agentic-pipeline.md)
   if you've changed the pipeline shape.
7. If the addition is architecturally significant (new framework, model,
   or model provider), write an ADR.
