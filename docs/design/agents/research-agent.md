# Research Agent

**Status**: Implemented
**Last updated**: 2026-07-27

The research agent runs only after a `GOOD_FIT` evaluation. It does not browse
the web. Kaziro delegates official-site discovery, rendered crawling, content
extraction, and provenance collection to the separately deployed Scrapper
service.

## Flow

1. Check `CompanySummary` for a user-owned job and reuse it while its
   30-day freshness window is valid.
2. Call `POST /research/company` with company name, optional known website,
   the required job URL, bounded crawl limits, and `X-Scrapper-Key`.
3. Preserve every returned source document, canonical URL, page type,
   retrieval timestamp, warning, and failure.
4. Send only that evidence to `LLM_MODEL_RESEARCH`. Scraped text is explicitly
   treated as untrusted data, never as instructions.
5. Validate the structured mission, values, culture, technology, size, recent
   developments, and applicant summary. Every populated field must cite at
   least one URL returned by Scrapper; unsupported fields become
   `Not available`.
6. Persist the structured brief, citations, raw evidence, synthesis model, and
   failure metadata in `CompanySummary`.

Partial crawl failures preserve usable evidence. If no sources are returned,
Kaziro records the diagnostics, emits a durable failure notification, and does
not generate application documents with invented company facts.

## Service Boundary

`/discover` remains the provider-documentation discovery contract.
`/extract-page` is raw model-free extraction used for manual job import.
`/research/company` performs model-free company research. OpenRouter is used
inside Kaziro only for evidence-grounded synthesis.
