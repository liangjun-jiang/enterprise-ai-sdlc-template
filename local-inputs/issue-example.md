# Add Milestone Summary Endpoint

## Problem Statement
Project managers cannot quickly see milestone completion health in one API response. They need a concise summary endpoint for dashboard cards.

## Business Goal / User Impact
- Reduce time to assess milestone status during weekly planning.
- Enable frontend dashboard to show milestone health without multiple API calls.

## Current Behavior
- Milestone data exists, but consumers must compose summaries client-side.
- No dedicated endpoint returns aggregated counts and completion percentage.

## Requested Change
Add a new backend endpoint that returns a milestone summary for a given milestone id.

## Proposed API
- Method: `GET`
- Path: `/api/v1/milestones/{milestone_id}/summary`
- Response (example):

```json
{
  "milestone_id": "ms-123",
  "total_tasks": 12,
  "completed_tasks": 7,
  "in_progress_tasks": 3,
  "not_started_tasks": 2,
  "completion_percent": 58.33,
  "updated_at": "2026-05-08T10:00:00Z"
}
```

## Acceptance Criteria
1. Endpoint exists and returns HTTP 200 for a valid `milestone_id`.
2. Response includes all fields listed in the proposed API shape.
3. `completion_percent` is rounded to 2 decimal places.
4. Returns HTTP 404 when milestone is missing.
5. Unit/integration tests cover:
   - success response shape and values
   - missing milestone behavior

## Constraints
- Do not add new dependencies.
- Follow existing coding conventions and validation patterns.
- Keep changes scoped to backend API/service/model/test files only.

## Out of Scope
- Frontend UI changes.
- Database schema changes.

## Notes From Discussion
- Prefer reusing existing milestone/task query logic where possible.
- Keep endpoint response lightweight for dashboard usage.
