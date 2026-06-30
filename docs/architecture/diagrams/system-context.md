# System Context Diagram (C4 Level 1)

**Status**: Active
**Last updated**: 2026-04-22
**Source**: Section 2 of [`Kaziro_Design_Document.pdf`](../../../Kaziro_Design_Document.pdf)
**Referenced from**: [`../01-system-overview.md`](../01-system-overview.md)

This is a [C4 Level 1](https://c4model.com/) context diagram showing Kaziro's
external actors and systems.

## Diagram

```mermaid
flowchart TB
  subgraph users [Users]
    user["Job Seeker<br/>(uses the platform)"]
    admin["Admin<br/>(operates the platform)"]
  end

  subgraph kaziro [Kaziro Platform]
    fe["React SPA<br/>(Next.js)"]
    api["Django Ninja Backend"]
    workers["Celery Workers<br/>+ LangGraph Agents"]
  end

  subgraph external [External Services]
    supa["Supabase<br/>(Auth + Postgres + Storage)"]
    rapid["RapidAPI<br/>(JSearch / LinkedIn Jobs)"]
    firecrawl["Firecrawl API<br/>(web scraping)"]
    openrouter["OpenRouter API<br/>(LLM + embeddings)"]
  end

  user -->|HTTPS| fe
  admin -->|HTTPS| fe
  fe -->|REST + WSS| api
  api --> supa
  api --> workers
  workers --> rapid
  workers --> firecrawl
  workers --> openrouter
  workers --> supa
```

## Actors

| Actor          | Description                                                    |
| -------------- | -------------------------------------------------------------- |
| **Job Seeker** | Configures profile and search preferences; reviews evaluations and applies. |
| **Admin**      | Operator: triggers manual fetches, monitors pipeline health, manages subscriptions. |

## External systems

| System         | Purpose                                                              |
| -------------- | -------------------------------------------------------------------- |
| **Supabase**   | Hosted Postgres + pgvector + Auth (JWT) + Storage (object store).    |
| **RapidAPI**   | Source of raw job postings (JSearch / LinkedIn Jobs endpoints).      |
| **Firecrawl**  | JS-rendered web scraping for company websites and job pages.         |
| **OpenRouter** | All LLM and embedding calls (default chat `nvidia/nemotron-3-super-120b-a12b:free`; default embeddings `nvidia/llama-nemotron-embed-vl-1b-v2:free`). |
