---
authors:
  - AI-generated
approvers:
  - ""
feature: per-person-activity-endpoint
priority: medium
milestone: milestone-002-hierarchy-and-analytics
prd_ref: docs/prd/prd-000-dashboard.md
assignees:
  planning: ""
  development: ""
  review: ""
  qa: ""
---

# Feature Plan: Per-Person Activity Endpoint

## Summary

Implement a `GET /api/v1/activity` endpoint that returns issues closed, PRs merged, and reviews posted for a given GitHub user within a specified time period. This endpoint supports the PRD requirement for per-person activity summaries.

## Background

Project Managers need per-person workload and activity breakdowns to understand team velocity and identify bottlenecks. The PRD lists "per-person activity summary: issues closed, PRs merged, reviews posted (this week / this month)" as a core requirement. GitHub's API provides the raw data (events, issues search, PR search), but there is no single endpoint that aggregates this per-person. This feature builds that aggregation layer in the backend.

## Requirements

1. Create a service module `backend/app/services/activity.py` containing the logic to query GitHub for a user's activity.
2. Create a router file `backend/app/routers/activity.py` containing the `GET /api/v1/activity` endpoint.
3. Register the router in `backend/app/main.py`.
4. The endpoint must accept the following query parameters:
   - `assignee` (required, string): GitHub login of the user
   - `period` (required, string, enum: `this_week` | `this_month`): the time range to query
5. If `assignee` is missing or empty, return `422 Unprocessable Entity`.
6. If `period` is not one of the allowed values, return `422 Unprocessable Entity`.
7. The service must compute the date range:
   - `this_week`: Monday 00:00 UTC of the current week through now
   - `this_month`: 1st of the current month 00:00 UTC through now
8. The service must query the GitHub API to determine:
   - **Issues closed**: issues in the repo assigned to `assignee` and closed within the period
   - **PRs merged**: pull requests in the repo authored by `assignee` and merged within the period
   - **Reviews posted**: pull request reviews authored by `assignee` within the period
9. The endpoint must return `200 OK` with the following JSON structure:
   ```json
   {
     "assignee": "octocat",
     "period": "this_week",
     "period_start": "2026-06-01T00:00:00Z",
     "period_end": "2026-06-05T14:30:00Z",
     "issues_closed": 5,
     "prs_merged": 3,
     "reviews_posted": 7,
     "issues": [{"number": 42, "title": "...", "closed_at": "...", "html_url": "..."}],
     "pull_requests": [{"number": 55, "title": "...", "merged_at": "...", "html_url": "..."}],
     "reviews": [{"pr_number": 55, "submitted_at": "...", "state": "APPROVED", "html_url": "..."}]
   }
   ```
10. Define Pydantic models in `backend/app/models/activity.py`: `ActivityResponse`, `IssueSummary`, `PullRequestSummary`, `ReviewSummary`.
11. If the GitHub API is unreachable or rate-limited, return `502 Bad Gateway` with an appropriate detail message.
12. The route handler must be `async def`.
13. Handle GitHub API pagination for all queries (issues, PRs, reviews may span multiple pages).
14. Write tests in `backend/app/routers/test_activity.py` and `backend/app/services/test_activity.py`:
    - Test successful 200 response with mocked GitHub data
    - Test correct date range computation for `this_week` and `this_month`
    - Test 422 response for missing/invalid `assignee`
    - Test 422 response for invalid `period` value
    - Test 502 response when GitHub API is unavailable
    - Test that counts match the detail arrays
15. Update `API_CONTRACTS.md` with the full contract for `GET /api/v1/activity`.

## Out of Scope

- Aggregation across multiple users in a single request (the frontend makes one call per user)
- Custom date ranges beyond `this_week` and `this_month`
- Cycle time or lead time calculations (Phase 3)
- Caching of activity data
- Frontend rendering (covered by `per-person-activity-ui`)

## Definition of Done

- [ ] `GET /api/v1/activity?assignee={login}&period={this_week|this_month}` returns the expected JSON
- [ ] `ActivityResponse` Pydantic model validates the response shape
- [ ] Summary counts (`issues_closed`, `prs_merged`, `reviews_posted`) are accurate
- [ ] Detail arrays (`issues`, `pull_requests`, `reviews`) contain the individual items
- [ ] Date range computation is correct for both `this_week` and `this_month`
- [ ] Invalid query parameters return 422
- [ ] GitHub API errors return 502
- [ ] Pagination is handled for all GitHub queries
- [ ] Route handler is `async def`
- [ ] All code passes `ruff check`, `ruff format --check`, and `mypy --strict`
- [ ] All tests pass via `pytest`
- [ ] `API_CONTRACTS.md` is updated with the full endpoint contract
