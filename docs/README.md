# Kaziro Documentation

> AI-powered agentic job recommendation and application system.
> Source of truth: [Kaziro_Design_Document.pdf](../Kaziro_Design_Document.pdf) (v1.0.0 — MVP).

This folder contains every architectural, design, and decision artefact for
Kaziro. If you are writing code, read the relevant section before you start —
the Cursor rules in [`.cursor/rules/`](../.cursor/rules/) enforce the
conventions described here.

## How to navigate

| If you want to…                                            | Read                                                                                  |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Understand the system end-to-end                           | [`architecture/01-system-overview.md`](architecture/01-system-overview.md)             |
| Understand how the LangGraph pipeline runs                 | [`architecture/02-agentic-pipeline.md`](architecture/02-agentic-pipeline.md)           |
| Look up a database table or column                         | [`architecture/03-data-model.md`](architecture/03-data-model.md)                       |
| Find an API endpoint                                       | [`architecture/04-api-design.md`](architecture/04-api-design.md)                       |
| Understand the SvelteKit frontend                          | [`architecture/05-frontend-architecture.md`](architecture/05-frontend-architecture.md) |
| Add logging, metrics, or alerts                            | [`architecture/06-observability.md`](architecture/06-observability.md)                 |
| Touch auth, RLS, secrets, or user data                     | [`architecture/07-security.md`](architecture/07-security.md)                           |
| Deploy the app or change infrastructure                    | [`architecture/08-deployment.md`](architecture/08-deployment.md)                       |
| Run AWS Terraform + GitHub Actions deployment flow         | [`architecture/09-aws-deployment-runbook.md`](architecture/09-aws-deployment-runbook.md) |
| Implement or modify a specific agent                       | [`design/agents/`](design/agents/)                                                     |
| Build a frontend page or component                         | [`design/frontend/`](design/frontend/)                                                 |
| Write or run tests                                         | [`design/testing-strategy.md`](design/testing-strategy.md)                             |
| Plan work for a phase                                      | [`design/roadmap.md`](design/roadmap.md)                                               |
| Understand *why* a technology was chosen                   | [`decisions/`](decisions/)                                                             |
| Look up an env var, dependency, or term                    | [`reference/`](reference/)                                                             |

## Folder layout

```
docs/
├── architecture/   # How the system is built (system, pipeline, data, API, FE, ops, security, deploy)
│   └── diagrams/   # Mermaid diagrams referenced from the architecture docs
├── design/         # How specific features work (agents, frontend, testing, roadmap)
│   ├── agents/
│   └── frontend/
├── decisions/      # Architecture Decision Records (ADRs) — MADR format
└── reference/      # Lookup tables: env vars, dependencies, glossary
```

## Document conventions

Every architecture/design doc starts with a small header:

```
**Status**: Draft | Active | Superseded
**Last updated**: YYYY-MM-DD
**Source**: Section X.Y of Kaziro_Design_Document.pdf
**Related ADRs**: ADR-0001, ADR-0002, …
```

ADRs follow the [MADR template](decisions/_template.md): Context, Decision
Drivers, Considered Options, Decision Outcome, Consequences.

## See also

- Repo entry point: [`/AGENTS.md`](../AGENTS.md)
- Backend rules: [`/backend/AGENTS.md`](../backend/AGENTS.md)
- Agents-specific rules: [`/backend/agents/AGENTS.md`](../backend/agents/AGENTS.md)
- Frontend rules: [`/frontend/AGENTS.md`](../frontend/AGENTS.md)
- Cursor rules: [`/.cursor/rules/`](../.cursor/rules/)
