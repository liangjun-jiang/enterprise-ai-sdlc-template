---
authors:
  - AI-generated
approvers:
  - ""
feature: issues-prs-list-endpoint
priority: medium
milestone: milestone-001-mvp
prd_ref: docs/prd/prd-000-dashboard.md
assignees:
  planning: ""
  development: ""
  review: ""
  qa: ""
---

# Feature Plan: Issues & Pull Requests List Endpoints

## Summary

Implement `GET /api/v1/issues` and `GET /api/v1/pull-requests` endpoints with query filters for assignee, state, and labels. These endpoints return compact summaries suitable for the frontend table view, enabling developers to see their assigned work without opening GitHub.

## Background

The PRD states that developers need to see their assigned issues and PR status in one place. The milestone goal specifically calls out showing "a combined issues/PRs list for the authenticated user." These endpoints provide the data layer for that view. They depend on the GitHub API client and use the Pydantic response models defined in the earlier feature.

## Requirements

1. Create `backend/app/routers/issues.py` with an `APIRouter` prefixed at `/api/v1/issues`.

2. Implement `GET /api/v1/issues`:
   - Query parameters: `state` (str, default `"open"`, values: `"open"`, `"closed"`, `"all"`), `assignee` (str | None, default None), `labels` (str | None, default None, comma-separated).
   - Calls `GitHubClient.get_issues()` with the provided filters.
   - Maps each GitHub issue to `IssueResponse`.
   - Returns `IssueListResponse` with HTTP 200.
   - Excludes pull requests from the results (GitHub's issues endpoint includes PRs — filter by absence of `pull_request` key).

3. Create `backend/app/routers/pull_requests.py` with an `APIRouter` prefixed at `/api/v1/pull-requests`.

4. Implement `GET /api/v1/pull-requests`:
   - Query parameters: `state` (str, default `"open"`, values: `"open"`, `"closed"`, `"all"`), `assignee` (str | None, default None), `labels` (str | None, default None, comma-separated).
   - Calls `GitHubClient.get_pull_requests()` with the provided filters.
   - Maps each GitHub PR to `PullRequestResponse`.
   - Returns `PullRequestListResponse` with HTTP 200.

5. Validate query parameter values:
   - `state` must be one of `"open"`, `"closed"`, `"all"` — return 422 for invalid values.
   - `assignee` and `labels` are passed through to GitHub API as-is.

6. Map GitHub API client exceptions to HTTP responses using the same pattern as milestone endpoints:
   - `GitHubAuthError` → 502, `GitHubRateLimitError` → 503, `GitHubNotFoundError` → 404, `GitHubAPIError` → 502.

7. Register both routers in `backend/app/main.py`.

8. Use dependency injection (`Depends`) for `GitHubClient` in both routers.

9. Create `backend/app/routers/test_issues.py` with tests:
   - Mock `GitHubClient` to return sample issue data.
   - Test default query (state=open) returns correctly shaped response.
   - Test filtering by assignee passes the parameter to the client.
   - Test filtering by labels passes the parameter to the client.
   - Test that items with a `pull_request` key are excluded from issue results.
   - Test invalid `state` value returns 422.

10. Create `backend/app/routers/test_pull_requests.py` with tests:
    - Mock `GitHubClient` to return sample PR data.
    - Test default query returns correctly shaped response.
    - Test filtering by assignee and state.
    - Test that `draft` and `merged_at` fields are correctly mapped.
    - Test error mapping for GitHub client exceptions.

11. All code must pass `mypy --strict` and `ruff check`.

12. Update `API_CONTRACTS.md` with the full contracts for both endpoints, including query parameters and response schemas.

## Out of Scope

- Pagination parameters for the API consumer (the backend fetches all pages from GitHub and returns the full list).
- Sorting options.
- Full issue/PR body content — only compact summaries.
- Linking issues to milestones or PRDs in the response (Phase 2).
- Any write operations.

## Definition of Done

- `GET /api/v1/issues` returns filtered issue list excluding pull requests.
- `GET /api/v1/pull-requests` returns filtered pull request list with draft and merged status.
- Query parameters `state`, `assignee`, and `labels` work correctly on both endpoints.
- Invalid `state` values return 422.
- GitHub client errors map to appropriate HTTP status codes.
- Both routers are registered in `main.py`.
- All tests in `test_issues.py` and `test_pull_requests.py` pass.
- `mypy --strict` passes.
- `ruff check` and `ruff format` pass.
- `API_CONTRACTS.md` is updated with both endpoint contracts.
