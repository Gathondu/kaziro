# Testing Strategy

**Status**: Active
**Last updated**: 2026-04-22
**Source**: Section 9 of [`Kaziro_Design_Document.pdf`](../../Kaziro_Design_Document.pdf) and [`.cursor/rules/005-testing.mdc`](../../.cursor/rules/005-testing.mdc)
**Code (target)**: `backend/tests/`, `frontend/e2e/`, `tests/load/`

## 1. Test pyramid

```
           /\
          /E2E\           Playwright — critical user journeys
         /------\
        /Integration\     pytest — API + DB + Celery + agents (mocked LLM)
       /------------\
      /     Unit     \   pytest + Vitest — pure functions, agent nodes, components
     /----------------\
```

| Layer            | Volume          | Tool                                  | Run                |
| ---------------- | --------------- | ------------------------------------- | ------------------ |
| Unit (Python)    | Largest         | `pytest` + `pytest-asyncio`           | every PR (< 60 s)  |
| Unit (frontend)  | Largest         | `vitest` + `@testing-library/React`  | every PR           |
| Integration      | Many            | `pytest` + ephemeral Postgres+Redis   | every PR (< 5 min) |
| E2E              | Few critical    | `playwright`                          | nightly + main merge |
| Load             | Few key flows   | `locust`                              | weekly + before release |

## 2. Backend test layout

```
backend/tests/
├── conftest.py                # Shared Django, auth, Redis, and sample data fixtures
├── test_auth_profile_notifications.py
├── test_scaffold.py
├── accounts/
├── jobs/
├── pipeline/
├── notifications/
└── cassettes/                 # VCR cassettes for LLM-mocked tests
```

## 3. Mandatory backend fixtures (`conftest.py`)

| Fixture           | Scope    | Purpose                                                    |
| ----------------- | -------- | ---------------------------------------------------------- |
| `event_loop`      | session  | Async event loop                                           |
| `client`          | function | Django or Django Ninja test client against the app         |
| `db`              | function | Transactional Django test database                         |
| `mock_redis`      | function | `fakeredis.aioredis` instance                              |
| `sample_user`     | function | Authenticated `User` row for tenant scoping tests          |
| `sample_profile`  | function | Filled `UserProfile` for the `sample_user`                 |
| `sample_job`      | function | Pre-parsed `JobPosting` for evaluation tests               |
| `mock_llm`        | function | Mock `ChatOpenRouter` and `OpenAIEmbeddings` via VCR      |
| `mock_scrapper`   | function | `respx` route returning provenance-preserving evidence     |
| `auth_headers`    | function | `{ Authorization: Bearer <fake JWT> }` for `sample_user`   |

Fixture pattern:

```python
@pytest_asyncio.fixture
async def db_session():
    user = User.objects.create_user(email="user@example.com", password="test-pass")
    yield user
```

## 4. Agent tests

Agents are tested at three levels:

### 4.1 Per-node unit tests

Each node function tested in isolation with a hand-crafted state and a
mocked LLM response.

```python
async def test_pass1_draft_node_scores_within_range(mock_llm):
    state = EvaluatorState(job_posting_id="...", user_id="...", job_title="Senior Engineer", ...)
    result = await pass1_draft_node(state)
    assert result.pass1_scores is not None
    for s in (result.pass1_scores.skills_match, ...):
        assert 0 <= s <= 10
```

### 4.2 Graph-level integration tests

Run the full LangGraph from the public entry point against a real DB and
mocked LLM via **VCR.py cassettes** committed to
`backend/tests/cassettes/`.

```python
@pytest.mark.vcr
async def test_run_evaluator_agent_good_fit(sample_user, sample_profile, sample_job, db_session):
    state = await run_evaluator_agent(str(sample_job.id), str(sample_user.id))
    assert state.error is None
    assert state.final_classification == Classification.GOOD_FIT
    assert 6.5 <= state.overall_score <= 10
```

VCR scrubs `Authorization` headers and `api_key` params on record.

### 4.3 Calibration tests

Hand-labelled fixture set (50 `(job, profile)` pairs across software,
healthcare, design, legal). Pass criterion: ≥ 80% agreement with the human
label on classification bucket. Run nightly to detect prompt regressions.

## 5. API tests

Every route has tests covering:

- **Happy path** with valid auth.
- **401** without token.
- **403** with token for a different user.
- **404** for non-existent / not-owned resources.
- **422** for invalid request bodies (Pydantic errors).
- **409** for invalid state-machine transitions where applicable.
- **429** for rate-limited endpoints (sample only).

```python
async def test_get_job_returns_404_for_other_users_job(
    async_client, sample_user, other_users_job, auth_headers,
):
    response = await async_client.get(
        f"/api/v1/jobs/{other_users_job.id}",
        headers=auth_headers,
    )
    assert response.status_code == 404
```

## 6. Frontend tests

### 6.1 Unit (`vitest`)

- Pure utility functions in `lib/utils/` — 100% coverage target.
- Component rendering with `@testing-library/React`.
- Store logic (auth, notifications, toast).

### 6.2 Component contract tests

For each component documented in
[`frontend/components.md`](frontend/components.md):

- Renders given props without crashing.
- Reacts to prop changes.
- Calls callback props on user interaction.
- Accessible roles present (`getByRole`).

## 7. End-to-end (`playwright`)

Tests live in `frontend/e2e/`. Run against staging or a local stack via
`frontend/playwright.config.ts` projects.

Critical paths covered:

| Test                       | Steps                                                                     |
| -------------------------- | ------------------------------------------------------------------------- |
| `signup-and-onboard`       | Signup → confirm email (mailcatcher) → wizard → first config saved        |
| `pipeline-flows-end-to-end`| Trigger fetch → wait for evaluation → verify good-fit appears in dashboard |
| `apply-and-track`          | Open evaluation → edit docs → mark sent → verify status timeline           |
| `kanban-status-transitions`| Drag-drop card across columns; verify illegal transitions are rejected     |
| `account-deletion`         | Settings → delete account → verify rows + storage purged                  |

E2E tests use a dedicated Supabase project with seeded fixture users to
keep them deterministic.

## 8. Load tests (`locust`)

`tests/load/locustfile.py` simulates:

- 100 concurrent users browsing `/jobs`.
- 50 concurrent triggers of `/jobs/{id}/trigger-evaluation`.
- 200 concurrent SSE connections (notification streams).

SLO targets:

| Metric                          | Target                |
| ------------------------------- | --------------------- |
| `/jobs` p95                     | < 250 ms              |
| `/jobs/{id}/trigger-evaluation` p95 (enqueue only, not full pipeline) | < 100 ms |
| SSE connect p95                  | < 200 ms              |
| 5xx rate                         | < 0.1%                |

Pipeline throughput (full agent chain) is measured separately from
backlog metrics — it's not a request-latency SLO.

## 9. Coverage requirements

| Area                  | Minimum coverage |
| --------------------- | ---------------- |
| `backend/apps/pipeline/` | **90%**      |
| `backend/apps/*/services.py` | 85%       |
| `backend/apps/*/views.py` | 75%         |
| `backend/apps/*/repositories.py` | 75%  |
| `backend/apps/core/` | 70%             |
| Frontend components   | 75%              |
| Frontend stores       | 90%              |

CI fails if coverage drops more than 1% in any area.

## 10. Test naming

Pattern: `test_<action>_<expected_outcome>_<conditions>`:

```
test_create_user_succeeds_with_valid_data
test_create_user_returns_400_for_invalid_email
test_evaluator_classifies_as_reject_when_skills_dont_match
```

## 11. Mocking external services — required

Tests **never** call live external services. Always mock:

- OpenRouter / embedding calls — VCR cassettes (or `pytest-mock` for unit tests).
- Scrapper — authenticated `respx` evidence fixtures.
- Provider job APIs — HTTP route fixtures.
- Supabase Storage — local stub or mocked S3 (`moto`).
- Email sending (Phase 6+) — capture via `mailcatcher` in dev.

Live-API smoke tests live separately (`tests/smoke/`) and run only against
staging post-deploy, gated by an explicit env var.

## 12. Running tests locally

```bash
# Backend unit + integration
make test
cd backend && uv run python manage.py test
cd backend && uv run ruff check .

# Frontend checks
cd frontend && pnpm lint
cd frontend && pnpm typecheck

# E2E
cd frontend && pnpm test:e2e
cd frontend && pnpm exec playwright test --ui

# Load
locust -f tests/load/locustfile.py --host http://staging.kaziro.io
```

## 13. CI execution matrix

| Stage                  | Runs on                | Time budget |
| ---------------------- | ---------------------- | ----------- |
| Lint + typecheck       | every PR               | < 1 min     |
| Backend unit + agent   | every PR               | < 3 min     |
| Backend integration    | every PR               | < 5 min     |
| Frontend unit + lint   | every PR               | < 2 min     |
| E2E (Playwright)       | merge to main, nightly | < 15 min    |
| Calibration            | nightly                | < 10 min    |
| Load                   | weekly + pre-release   | 30 min      |
