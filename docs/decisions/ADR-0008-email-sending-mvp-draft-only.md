# ADR-0008: MVP generates documents only — no automatic email sending

**Status**: Accepted
**Date**: 2026-04-22
**Deciders**: Founding engineering team
**Tags**: product, agents, integrations

## Context and problem statement

Kaziro generates a tailored CV and cover letter per `GOOD_FIT` job. The
obvious next step is to send the application — either as an email to the
hiring manager or via a job-board submission flow.

Doing this in MVP would require:

- Hiring-manager email discovery (Hunter.io / Apollo / RocketReach API).
- An outbound email service (Resend / Postmark / SES) and from-address
  reputation management.
- Job-board submission integrations (LinkedIn EasyApply, Greenhouse,
  Workday — each is a heavy custom integration).
- User-facing review-and-edit before send (mandatory; sending unreviewed
  AI documents to real humans is a brand and trust risk).

> "Should the MVP send applications automatically, or stop at document
> generation?"

## Decision drivers

- Time-to-MVP — every integration added is weeks of work.
- Trust and reputation — users must review every doc before send.
- Email deliverability is its own ops discipline (SPF/DKIM/DMARC,
  warmup, bounce handling).
- Compliance — automated outreach intersects with CAN-SPAM, GDPR, and
  job-board ToS.
- Spam-blast risk — an over-eager pipeline could blast hundreds of bad
  applications and burn the user's reputation.

## Considered options

1. **Generate documents only; user downloads and sends manually**.
2. **Auto-send via email** with a "review-required" gate.
3. **Auto-submit via job-board APIs** (LinkedIn / Greenhouse / Workday).
4. **Generate + draft Gmail/Outlook drafts** in the user's mailbox.

## Decision outcome

**Chosen option**: Option 1 — generate documents only, user downloads and
sends manually.

The MVP closes the loop with: pipeline → notification → user reviews docs
in the UI → user downloads PDF → user submits through their own channel.
The `applications` table tracks status (`READY` → `SENT` → `RESPONDED`)
based on user-provided updates.

### Positive consequences

- We ship the MVP weeks earlier.
- Zero risk of sending unreviewed AI content to real humans.
- No deliverability ops to learn.
- Users stay in control — they see every doc before send.
- Status tracking in `applications` still gives us a useful product loop
  for retention and analytics.

### Negative consequences

- "Click download, then send manually" is more friction than auto-submit.
- We surrender the auto-applying narrative — competitors will market this
  more aggressively.
- We learn less about response rates per generated-doc unless users
  manually update status.

## Future / V2

ADR follow-ons (not yet written) will cover:

- Gmail draft creation in the user's mailbox (lowest-risk auto-assist).
- LinkedIn EasyApply integration (highest-volume job board).
- Auto-send with mandatory in-app review queue + per-send confirmation.

## Pros and cons of the options

### Option 1 — Documents only

- **Pros**: Fast; safe; zero deliverability ops; user in full control.
- **Cons**: More friction; weaker auto-apply narrative.

### Option 2 — Auto-send email with review gate

- **Pros**: Closes the loop; better metrics.
- **Cons**: Requires hiring-manager email discovery, outbound infra, and
  review UX. Weeks of work and a long brand-risk tail.

### Option 3 — Auto-submit via job-board APIs

- **Pros**: Highest leverage if it works.
- **Cons**: Each board is a custom integration; ToS is hostile to
  automation; LinkedIn in particular bans this.

### Option 4 — Drafts in Gmail/Outlook

- **Pros**: Hybrid — we do the typing, user clicks send.
- **Cons**: OAuth scopes are scary; per-provider quirks; still need hiring
  manager email.

## Links

- [`docs/design/agents/document-agent.md`](../design/agents/document-agent.md)
- [`docs/architecture/diagrams/application-state-machine.md`](../architecture/diagrams/application-state-machine.md)
- [`docs/design/roadmap.md`](../design/roadmap.md)
