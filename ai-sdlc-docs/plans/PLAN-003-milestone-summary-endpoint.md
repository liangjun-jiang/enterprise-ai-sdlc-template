---
authors:
  - AI-generated
approvers:
  - ""
feature: milestone-summary-endpoint
priority: medium
milestone: milestone-001-mvp
prd_ref: docs/prd/prd-000-dashboard.md
assignees:
  planning: ""
  development: ""
  review: ""
  qa: ""
---

# Feature Plan: Milestone Summary Endpoint

## Summary

Implement two FastAPI endpoints — `GET /api/v1/milestones` and `GET /api/v1/milestones/{milestone_number}/summary` — that return milestone data including open/closed issue counts and completion percentage. These endpoints use the GitHub API client and return data shaped by the Pydantic response models.

## Background

The PRD's primary success metric is: "A PM can answer 'what % of milestone-001 is complete?' in under 30 seconds without opening GitHub." This requires an endpoint that fetches milestone data from GitHub and computes a completion percentage from open and closed issue counts. The API_CONTRACTS.md convention requires all new endpoints under `/api/v1/` and that the contracts file is updated in the same PR.

## Requirements

1. Create `backend/app/routers/milestones.py` with an `APIRouter` prefixed at `/api/v1/milestones`.

2. Implement `GET /api/v1/milestones`:
   - Calls `GitHubClient.get_milestones(state="all")`.
   - Maps each GitHub milestone to `MilestoneSummaryResponse`, computing `completion_percentage` as `closed_issues / (open_issues + closed_issues) * 100` (0.0 if no issues).
   - Returns `MilestoneListResponse` with HTTP 200.

3. Implement `GET /api/v1/milestones/{milestone_number}/summary`:
   - Path parameter `milestone_number` (int).
   - Calls `GitHubClient.get_milestone(milestone_number)`.
   - Returns a single `MilestoneSummaryResponse` with HTTP 200.
   - Returns HTTP 404 with `ErrorResponse` if the milestone does not exist.

4. Map GitHub API client exceptions to HTTP responses:
   - `GitHubAuthError` → 502 Bad Gateway with `ErrorResponse` ("GitHub authentication failed").
   - `GitHubRateLimitError` → 503 Service Unavailable with `ErrorResponse` and `Retry-After` header.
   - `GitHubNotFoundError` → 404 Not Found with `ErrorResponse`.
   - `GitHubAPIError` → 502 Bad Gateway with `ErrorResponse`.

5. Register the router in `backend/app/main.py`.

6. Use dependency injection (`Depends`) to provide the `GitHubClient` instance to route handlers, allowing easy mocking in tests.

7. Create `backend/app/routers/test_milestones.py` with tests:
   - Mock the `GitHubClient` dependency to return controlled data.
   - Test `GET /api/v1/milestones` returns correct list with computed percentages.
   - Test completion percentage is 0.0 when a milestone has zero issues.
   - Test `GET /api/v1/milestones/{milestone_number}/summary` returns correct data for a valid milestone.
   - Test 404 response when milestone does not exist.
   - Test 502 response when GitHub auth fails.
   - Use `httpx.ASGITransport(app=app)` for the test client.

8. All code must pass `mypy --strict` and `ruff check`.

9. Update `API_CONTRACTS.md` with the full contract for both endpoints.

## Out of Scope

- Filtering milestones by state via query parameter (can be added later).
- Milestone burn-down or time-series data (Phase 3).
- Caching milestone data.
- Any write operations on milestones.

## Definition of Done

- `GET /api/v1/milestones` returns a list of milestones with open/closed counts and completion percentage.
- `GET /api/v1/milestones/{milestone_number}/summary` returns a single milestone summary.
- 404 is returned for non-existent milestones.
- GitHub client errors are mapped to appropriate HTTP status codes.
- Router is registered in `main.py`.
- All tests in `test_milestones.py` pass.
- `mypy --strict` passes.
- `ruff check` and `ruff format` pass.
- `API_CONTRACTS.md` is updated with both endpoint contracts.
