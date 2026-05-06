

# Execution Plan: AI Pipeline Metrics Endpoint

**Authors:** AI-generated
**Approvers:** *(unset)*

## Summary

Implement a `GET /api/v1/ai-metrics` endpoint that queries the GitHub REST API (issues + pull requests search) to return aggregate counts of AI pipeline activity — plans generated, AI-created issues, AI PRs opened/merged/rejected. The endpoint accepts a required `period` query parameter (`this_week` or `this_month`) and returns an `AiMetricsResponse` Pydantic model. All GitHub interaction uses `httpx.AsyncClient` authenticated via `GITHUB_TOKEN`, with `GITHUB_REPO` validated at startup.

**Assumption:** "Plans generated" will be counted as GitHub issues carrying both the `ai-generated` and `ai-plan` labels within the time range. This heuristic will be documented in a docstring on the counting function. The GitHub Search API (`GET /search/issues`) will be used with date-range qualifiers (`created:>=YYYY-MM-DD`) to fetch results, avoiding the need for pagination in this phase (per the out-of-scope note on >1000 items).

## Tasks

### Task 1: Define Pydantic response model and environment config validation

**ID:** TASK-001
**Depends on:** none
**Assignee:** *(unset — will be handled by AI code writer)*
**Affected files:**
- `backend/app/models/ai_metrics.py` (create)
- `backend/app/models/__init__.py` (modify — add re-export if pattern exists, or leave empty)

**Description:**

Create the Pydantic response model `AiMetricsResponse` in `backend/app/models/ai_metrics.py`. The model must include:

| Field | Type | Description |
|---|---|---|
| `period` | `str` | Echoed query parameter (`this_week` or `this_month`) |
| `period_start` | `date` | ISO-8601 date of the period start (Monday or 1st of month) |
| `period_end` | `date` | ISO-8601 date of today (UTC) |
| `plans_generated` | `int` | Count of issues with labels `ai-generated` + `ai-plan` |
| `issues_created_by_ai` | `int` | Count of issues with label `ai-generated` |
| `ai_prs_opened` | `int` | Count of PRs with label `ai-generated` |
| `ai_prs_merged` | `int` | Subset of above that are merged |
| `ai_prs_rejected_closed` | `int` | Subset of above that are closed but not merged |

Also create a small helper module or function (can live in `ai_metrics.py` or a separate `backend/app/services/github_metrics.py` — see Task 2) that computes `period_start` and `period_end` given a period string, using `datetime.date` and UTC. `this_week` = Monday of the current ISO week through today. `this_month` = 1st of the current month through today.

Additionally, add startup validation for the `GITHUB_TOKEN` and `GITHUB_REPO` environment variables. This can be a function called during app startup (in `main.py` lifespan or an import-time check in the service module) that raises a clear `RuntimeError` if either variable is missing. `GITHUB_REPO` must match the `owner/repo` format.

**Acceptance criteria:**
- [ ] `AiMetricsResponse` is defined in `backend/app/models/ai_metrics.py` with all fields typed and documented
- [ ] A `compute_period_range(period: str) -> tuple[date, date]` function (or equivalent) returns correct start/end for `this_week` and `this_month`
- [ ] `GITHUB_TOKEN` and `GITHUB_REPO` are validated at import/startup — missing values raise `RuntimeError` with descriptive message
- [ ] `ruff check`, `ruff format`, and `mypy --strict` pass on the new file(s)

---

### Task 2: Implement GitHub API service layer and the `/api/v1/ai-metrics` router

**ID:** TASK-002
**Depends on:** TASK-001
**Assignee:** *(unset — will be handled by AI code writer)*
**Affected files:**
- `backend/app/services/__init__.py` (create — empty)
- `backend/app/services/github_metrics.py` (create)
- `backend/app/routers/ai_metrics.py` (create)
- `backend/app/main.py` (modify — register the new router and trigger env-var validation)

**Description:**

**Service layer (`backend/app/services/github_metrics.py`):**

Create an async function `fetch_ai_metrics(period: str) -> AiMetricsResponse` that:

1. Calls `compute_period_range(period)` to get `period_start` and `period_end`.
2. Uses `httpx.AsyncClient` to call the GitHub Search API (`GET https://api.github.com/search/issues`) with appropriate query strings:
   - **AI issues:** `repo:{GITHUB_REPO} is:issue label:ai-generated created:>={period_start}`
   - **AI plan issues:** `repo:{GITHUB_REPO} is:issue label:ai-generated label:ai-plan created:>={period_start}`
   - **AI PRs (all):** `repo:{GITHUB_REPO} is:pr label:ai-generated created:>={period_start}`
   - **AI PRs merged:** `repo:{GITHUB_REPO} is:pr label:ai-generated is:merged created:>={period_start}`
   - **AI PRs closed (not merged):** `repo:{GITHUB_REPO} is:pr label:ai-generated is:closed is:unmerged created:>={period_start}`
3. Authenticates each request with `Authorization: Bearer {GITHUB_TOKEN}` and sets `Accept: application/vnd.github+json`.
4. Uses the `total_count` field from each search response to populate the integer counts.
5. Wraps all `httpx` calls in a `try/except` that catches `httpx.HTTPStatusError` (for 4xx/5xx from GitHub) and `httpx.RequestError` (for network issues). On any such error, raises an `HTTPException(status_code=502, detail="GitHub API error: <sanitized message>")`. Never forward raw GitHub response bodies.
6. Documents the "plans generated" heuristic in a module-level or function-level docstring.

**Router (`backend/app/routers/ai_metrics.py`):**

Create a router with a single `GET /ai-metrics` endpoint:
- The `period` query parameter must be a required `str` validated via a `Literal["this_week", "this_month"]` type annotation (FastAPI will auto-return 422 for missing/invalid values).
- The handler is `async def`, calls `fetch_ai_metrics(period)`, and returns the result with `response_model=AiMetricsResponse`.

**Registration (`backend/app/main.py`):**

- Import the new router and include it with `prefix="/api/v1"`.
- Ensure the environment variable validation from Task 1 runs at startup (e.g., call the validation function in a lifespan handler or at module-import time of the service layer). If `GITHUB_TOKEN` or `GITHUB_REPO` is missing, the application must fail to start.

**Acceptance criteria:**
- [ ] `GET /api/v1/ai-metrics?period=this_week` returns 200 with a JSON body conforming to `AiMetricsResponse`
- [ ] `GET /api/v1/ai-metrics?period=this_month` returns 200 with a JSON body conforming to `AiMetricsResponse`
- [ ] `GET /api/v1/ai-metrics` (no period) returns 422
- [ ] `GET /api/v1/ai-metrics?period=invalid` returns 422
- [ ] GitHub API errors result in 502 with `{"detail": "..."}` — raw GitHub payloads are never exposed
- [ ] Application refuses to start if `GITHUB_TOKEN` or `GITHUB_REPO` is missing
- [ ] All route handlers are `async def`
- [ ] `httpx.AsyncClient` is used for all outbound HTTP calls
- [ ] `ruff check`, `ruff format`, and `mypy --strict` pass on all new/modified files

---

### Task 3: Write unit tests for the AI metrics endpoint

**ID:** TASK-003
**Depends on:** TASK-002
**Assignee:** *(unset — will be handled by AI code writer)*
**Affected files:**
- `backend/app/routers/test_ai_metrics.py` (create)

**Description:**

Create `backend/app/routers/test_ai_metrics.py` with comprehensive tests. All tests must mock the GitHub API calls — no real network calls during `pytest`. Use `unittest.mock.patch` (or `pytest-mock`) to mock `httpx.AsyncClient` responses at the service layer level or use `respx` / monkeypatching to intercept outbound HTTP.

Set `GITHUB_TOKEN` and `GITHUB_REPO` environment variables in test fixtures (e.g., via `monkeypatch.setenv`).

Use `httpx.AsyncClient` with `httpx.ASGITransport(app=app)` for all test requests (per coding standards).

**Required test cases:**

1. **`test_ai_metrics_this_week_returns_200`** — Mock GitHub search API to return known `total_count` values. Assert response status is 200, all integer fields match expected values, `period` is `"this_week"`, and `period_start`/`period_end` are valid ISO date strings with correct semantics.

2. **`test_ai_metrics_this_month_returns_200`** — Same pattern with `period=this_month`. Verify `period_start` is the 1st of the current month.

3. **`test_ai_metrics_missing_period_returns_422`** — `GET /api/v1/ai-metrics` with no query parameter. Assert 422.

4. **`test_ai_metrics_invalid_period_returns_422`** — `GET /api/v1/ai-metrics?period=yesterday`. Assert 422.

5. **`test_ai_metrics_github_api_failure_returns_502`** — Mock GitHub API to raise an `httpx.RequestError` or return a 500/403. Assert the endpoint returns 502 with a `detail` key in the JSON body.

6. **`test_period_range_this_week_starts_on_monday`** — Unit test for the `compute_period_range` helper to verify `this_week` returns the Monday of the current week.

7. **`test_period_range_this_month_starts_on_first`** — Unit test for `compute_period_range` to verify `this_month` returns the 1st of the current month.

**Acceptance criteria:**
- [ ] All 7 test cases (minimum) are implemented and pass with `pytest`
- [ ] No real HTTP calls are made — all GitHub API interactions are mocked
- [ ] Test client uses `httpx.ASGITransport(app=app)` pattern (not deprecated `app=` kwarg)
- [ ] Environment variables are set via `monkeypatch.setenv` in fixtures
- [ ] `ruff check`, `ruff format`, and `mypy --strict` pass on the test file
- [ ] `pytest` passes with zero failures

---

### Task 4: Update API_CONTRACTS.md with the ai-metrics endpoint contract

**ID:** TASK-004
**Depends on:** TASK-001
**Assignee:** *(unset — will be handled by AI code writer)*
**Affected files:**
- `docs/context/API_CONTRACTS.md` (modify)

**Description:**

Add a new section to `API_CONTRACTS.md` documenting the `GET /api/v1/ai-metrics` endpoint. Follow the existing documentation format (see `/health` and `/api/v1/version` as examples). Include:

1. **Endpoint heading:** `### GET /api/v1/ai-metrics`
2. **Description:** Returns aggregate AI pipeline activity metrics for the specified period.
3. **Query parameters table:**

   | Parameter | Type | Required | Allowed Values | Description |
   |-----------|------|----------|----------------|-------------|
   | `period` | `string` | yes | `this_week`, `this_month` | Time range to aggregate |

4. **Response `200 OK`** with example JSON body showing all fields.
5. **Response schema table** listing every field, type, and description.
6. **Error responses:**
   - `422 Unprocessable Entity` — missing or invalid `period` parameter
   - `502 Bad Gateway` — GitHub API call failed (with `{"detail": "..."}` body)
7. **Environment variables section** documenting:
   - `GITHUB_TOKEN` (required) — GitHub personal access token for API authentication
   - `GITHUB_REPO` (required, format `owner/repo`) — target repository for metrics queries
8. **Heuristics note:** Document that `plans_generated` counts issues with labels `ai-generated` + `ai-plan`.

**Acceptance criteria:**
- [ ] `API_CONTRACTS.md` contains a complete `### GET /api/v1/ai-metrics` section
- [ ] Query parameters, response schema, and error responses are all documented
- [ ] `GITHUB_TOKEN` and `GITHUB_REPO` environment variable requirements are documented
- [ ] The heuristic for counting "plans generated" is explicitly stated
- [ ] Documentation format matches the style of existing endpoint entries in the file