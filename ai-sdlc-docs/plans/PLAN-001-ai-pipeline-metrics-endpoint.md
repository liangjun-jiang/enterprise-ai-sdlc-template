---
authors:
  - AI-generated
approvers:
  - ""
feature: ai-pipeline-metrics-endpoint
priority: medium
milestone: milestone-003-ai-metrics-and-polish
prd_ref: docs/prd/prd-000-dashboard.md
assignees:
  planning: ""
  development: ""
  review: ""
  qa: ""
---

# Feature Plan: AI Pipeline Metrics Endpoint

## Summary

Implement a `GET /api/v1/ai-metrics` endpoint that queries the GitHub API for AI pipeline activity and returns aggregate counts of plans generated, AI-created issues, AI PRs opened, AI PRs merged, and AI PRs rejected/closed. The endpoint accepts a `period` query parameter (`this_week` or `this_month`) to scope the time range.

## Background

The PRD identifies Tech Leads as a key user who wants "AI pipeline health: how many AI PRs opened/merged/rejected this week." Success metric #3 explicitly states that AI pipeline activity (plans generated, issues created, PRs opened/reviewed) must be visible on a single dashboard. This endpoint provides the backend data source for the AI pipeline dashboard panel (feature `ai-pipeline-dashboard-ui`). Since there is no database, all data must be fetched from the GitHub API in real-time, relying on labels and conventions already established by the AI pipeline (e.g., `ai-generated` label on PRs, label conventions for AI-created issues).

## Requirements

1. The endpoint must be available at `GET /api/v1/ai-metrics` and accept a required query parameter `period` with allowed values `this_week` and `this_month`.
2. If `period` is missing or has an invalid value, the endpoint must return `422 Unprocessable Entity` with a descriptive error.
3. The response must include the following integer fields: `plans_generated`, `issues_created_by_ai`, `ai_prs_opened`, `ai_prs_merged`, `ai_prs_rejected_closed`.
4. The response must also include `period` (echoed back) and `period_start` / `period_end` as ISO-8601 date strings indicating the computed date range.
5. `this_week` means Monday 00:00 UTC through the current UTC datetime. `this_month` means the 1st of the current month 00:00 UTC through the current UTC datetime.
6. AI-related artifacts are identified by the `ai-generated` label on GitHub issues and PRs. Plans generated are counted by issues or PRs with an additional convention label (e.g., `ai-plan`) or by counting merged plan files — the implementation must document the chosen heuristic.
7. The endpoint must use `httpx.AsyncClient` to call the GitHub REST API, authenticating via a `GITHUB_TOKEN` environment variable.
8. The `GITHUB_REPO` environment variable (format `owner/repo`) must be read at startup; if missing, the application must fail fast with a clear error message.
9. A Pydantic response model `AiMetricsResponse` must be defined in `backend/app/models/ai_metrics.py`.
10. The endpoint router must live in `backend/app/routers/ai_metrics.py` and be registered in `main.py`.
11. GitHub API errors (rate limit, auth failure, network) must be caught and returned as `502 Bad Gateway` with a `{"detail": "..."}` body — never expose raw GitHub error payloads.
12. Unit tests must cover: valid `this_week` request, valid `this_month` request, missing `period` → 422, invalid `period` value → 422, GitHub API failure → 502. GitHub calls must be mocked in all tests.
13. The endpoint contract must be added to `API_CONTRACTS.md` in the same PR.

## Out of Scope

- Caching or rate-limit management beyond basic error handling (no Redis, no in-memory TTL cache in this plan).
- Pagination across large result sets — the endpoint may use GitHub search API with date filters; handling repos with >1000 AI items in a single period is deferred.
- Webhook-based event ingestion — this endpoint is pull-based.
- Any write operations to GitHub.
- Frontend UI for displaying these metrics (covered by `ai-pipeline-dashboard-ui`).

## Definition of Done

- `GET /api/v1/ai-metrics?period=this_week` returns `200` with a JSON body matching the `AiMetricsResponse` schema.
- `GET /api/v1/ai-metrics?period=this_month` returns `200` with a JSON body matching the `AiMetricsResponse` schema.
- `GET /api/v1/ai-metrics` (no period) returns `422`.
- `GET /api/v1/ai-metrics?period=invalid` returns `422`.
- All GitHub API calls are mocked in tests; no real network calls during `pytest`.
- `ruff check`, `ruff format`, and `mypy --strict` pass with zero errors.
- `pytest` passes with all new tests green.
- `API_CONTRACTS.md` is updated with the full endpoint contract.
- Pydantic model is defined in `backend/app/models/ai_metrics.py`.
- Router is defined in `backend/app/routers/ai_metrics.py`.
- Environment variable requirements (`GITHUB_TOKEN`, `GITHUB_REPO`) are documented in `API_CONTRACTS.md`.