---
authors:
  - AI-generated
approvers:
  - ""
feature: milestone-burndown-endpoint
priority: medium
milestone: milestone-003-ai-metrics-and-polish
prd_ref: docs/prd/prd-000-dashboard.md
assignees:
  planning: ""
  development: ""
  review: ""
  qa: ""
---

# Feature Plan: Milestone Burndown Endpoint

## Summary

Implement a `GET /api/v1/milestones/{milestone_id}/burndown` endpoint that returns daily open and closed issue counts over the milestone's date range, providing the data needed for a frontend burn-down chart. The endpoint queries GitHub milestones and issues, computing a day-by-day time series.

## Background

The PRD lists Project Managers as target users who "want milestone burn-down, per-person workload, and cycle time." The primary success metric is that a PM can answer "what % of milestone-001 is complete?" in under 30 seconds without opening GitHub. A burndown endpoint that returns pre-computed daily totals enables a lightweight frontend chart component without complex client-side data processing. GitHub is the sole source of truth — the endpoint reads milestone metadata and issue events from the GitHub API.

## Requirements

1. The endpoint must be available at `GET /api/v1/milestones/{milestone_id}/burndown` where `milestone_id` is the GitHub milestone number (integer).
2. The response must include: `milestone_id`, `milestone_title`, `start_date` (ISO-8601), `due_date` (ISO-8601), and `series` — an array of objects each containing `date` (ISO-8601 date), `open_count` (int), and `closed_count` (int).
3. The `series` array must contain one entry per calendar day from `start_date` through `due_date` (or through today's date if the milestone is still open and `due_date` is in the future).
4. If the GitHub milestone has no `due_on` date, the endpoint must return `422` with a descriptive error explaining that a due date is required for burndown calculation.
5. The `start_date` is derived from the milestone's `created_at` field (or an optional `start_date` query parameter override if provided).
6. If the milestone does not exist on GitHub, return `404 Not Found` with `{"detail": "Milestone not found"}`.
7. The endpoint must use `httpx.AsyncClient` with `GITHUB_TOKEN` and `GITHUB_REPO` environment variables.
8. Issue open/close events must be used to compute daily snapshots. For each day, `open_count` = total issues in milestone that were open as of end-of-day UTC, `closed_count` = total issues that were closed as of end-of-day UTC.
9. A Pydantic response model `BurndownResponse` with nested `BurndownDataPoint` must be defined in `backend/app/models/burndown.py`.
10. The router must live in `backend/app/routers/burndown.py` and be registered in `main.py`.
11. GitHub API errors must be caught and returned as `502 Bad Gateway`.
12. Unit tests must cover: valid milestone with series data, milestone not found → 404, milestone without due date → 422, GitHub API failure → 502. All GitHub calls mocked.
13. The endpoint contract must be added to `API_CONTRACTS.md` in the same PR.

## Out of Scope

- Scope change tracking (added/removed issues mid-milestone) — the burndown shows total open vs. closed, not ideal vs. actual scope lines.
- Per-assignee burndown breakdown.
- Caching of burndown data.
- Frontend chart rendering (covered by `burndown-chart-ui`).
- Milestones from external systems (Jira, Linear).

## Definition of Done

- `GET /api/v1/milestones/1/burndown` returns `200` with a JSON body matching `BurndownResponse` schema, including a populated `series` array.
- `GET /api/v1/milestones/99999/burndown` (non-existent) returns `404`.
- Milestone without `due_on` returns `422`.
- GitHub API failure scenarios return `502`.
- All tests pass with mocked GitHub API calls.
- `ruff check`, `ruff format`, and `mypy --strict` pass.
- `API_CONTRACTS.md` is updated with the full endpoint contract.
- Pydantic models are defined in `backend/app/models/burndown.py`.
- Router is defined in `backend/app/routers/burndown.py`.