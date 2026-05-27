# ADR-0005: Firecrawl for company-website scraping

**Status**: Accepted
**Date**: 2026-04-22
**Deciders**: Founding engineering team
**Tags**: backend, agents, integrations

## Context and problem statement

The Research agent gathers public company information (mission, values,
recent news, tech stack) from company websites. Modern company sites are
JS-heavy SPAs with bot-detection, dynamic rendering, and aggressive
rate-limiting. We need clean, LLM-ready text from arbitrary URLs.

Building this in-house means:

- Headless-browser pool (Playwright / Puppeteer).
- IP rotation and CAPTCHA handling.
- HTML → markdown conversion.
- Robots / ToS handling.

> "How do we scrape company websites reliably for the Research agent?"

## Decision drivers

- Time to MVP — this is not a competitive moat; we want to outsource it.
- LLM-ready output (clean markdown, no nav/footer noise).
- Built-in JS rendering and anti-bot evasion.
- Per-call pricing — we cache aggressively, so volume is low.
- Pluggable — easy to swap if pricing/quality changes.

## Considered options

1. **Firecrawl** — managed scraping API with markdown output and JS
   rendering.
2. **Self-hosted Playwright pool** + custom HTML → markdown.
3. **Bright Data / ScraperAPI** — generic scraping APIs.
4. **Tavily** — search + extraction API geared for LLMs.

## Decision outcome

**Chosen option**: Firecrawl.

It returns clean markdown, handles JS rendering, and has a `/scrape`
endpoint that fits the Research agent's need for one-page-at-a-time
scraping with a structured response. When job-board and ATS URLs obscure the
company's own site, Firecrawl `/search` is also used to locate the official
company website before scraping. The 30-day cache in
`company_summaries` keeps spend predictable.

### Positive consequences

- Research agent code stays small — a search call only when the stored company
  website is missing or looks like a job-board domain, then a single scrape per
  selected URL.
- No headless-browser ops to maintain.
- Markdown output goes straight into LLM context (no HTML cleanup step).
- Cached for 30 days per company, capping cost.

### Negative consequences

- Vendor lock-in; pricing changes affect us directly. Mitigated by a
  thin internal `web_scraper` service wrapper so we can swap providers.
- Per-call cost — we depend on the cache to keep budgets sane.
- ToS and rate-limiting for the upstream company sites is now Firecrawl's
  problem, not ours, but we still operate within their fair-use policies.

## Pros and cons of the options

### Option 1 — Firecrawl

- **Pros**: Clean markdown; JS rendering; LLM-friendly; minimal code.
- **Cons**: Per-call cost; vendor lock-in.

### Option 2 — Self-hosted Playwright

- **Pros**: Free per-request; full control.
- **Cons**: Headless-browser ops nightmare; CAPTCHA + bot-detection cat-and-mouse;
  weeks of work + ongoing maintenance.

### Option 3 — Bright Data / ScraperAPI

- **Pros**: Mature; vast IP pool.
- **Cons**: Generic — returns HTML; we still need HTML → markdown; pricing
  is opaque.

### Option 4 — Tavily

- **Pros**: Built for LLM workflows; great extraction.
- **Cons**: Optimised for search-and-extract; less suited to "scrape this
  exact URL" semantics; smaller free tier.

## Links

- [`docs/design/agents/research-agent.md`](../design/agents/research-agent.md)
- [Firecrawl](https://firecrawl.dev/)
