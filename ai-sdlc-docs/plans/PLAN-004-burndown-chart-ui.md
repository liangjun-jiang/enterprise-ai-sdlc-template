---
authors:
  - AI-generated
approvers:
  - ""
feature: burndown-chart-ui
priority: medium
milestone: milestone-003-ai-metrics-and-polish
prd_ref: docs/prd/prd-000-dashboard.md
assignees:
  planning: ""
  development: ""
  review: ""
  qa: ""
---

# Feature Plan: Burndown Chart UI

## Summary

Build a frontend burn-down chart component that visualizes daily open vs. closed issue counts for a given milestone, displayed on the milestone detail view. The component consumes the `GET /api/v1/milestones/{milestone_id}/burndown` endpoint and renders using the same lightweight charting library chosen for the AI pipeline dashboard.

## Background

The PRD identifies Project Managers as users who need "milestone burn-down" visibility. The primary success metric is answering "what % of milestone-001 is complete?" in under 30 seconds. A visual burndown chart on the milestone detail view directly addresses this need. The backend endpoint (`milestone-burndown-endpoint`) provides the daily time series; this feature renders it as a line/area chart showing open issues trending down over the milestone date range.

## Requirements

1. Create a `BurndownChart` component in `frontend/src/components/BurndownChart.tsx`.
2. The component must accept a `milestoneId` prop (number) and fetch data from `/api/v1/milestones/{milestoneId}/burndown` on mount.
3. The chart must render two lines/areas: one for open issues and one for closed issues, plotted against the date axis.
4. The chart must display milestone title, start date, and due date as contextual information (either in chart header or axis labels).
5. An ideal burndown line (straight diagonal from total issues on start date to 0 on due date) should be rendered as a dashed reference line.
6. Loading state: show a loading indicator with `data-testid="burndown-loading"` while data is being fetched.
7. Error state: if the endpoint returns 404 (milestone not found) or 422 (no due date), display a user-friendly message with `data-testid="burndown-error"` explaining the issue.
8. If the endpoint returns 502, show a generic error with a retry button.
9. The component must use the same charting library installed for `ai-pipeline-dashboard-ui` — do not introduce a second charting library.
10. The component must be integrated into a milestone detail view. If no milestone detail page exists yet, create a minimal `MilestoneDetail` page component at `frontend/src/pages/MilestoneDetail.tsx` that accepts a milestone ID (via URL param or prop) and renders the burndown chart.
11. Component tests must cover: successful chart render with mocked data, loading state, 404 error state, 422 error state, 502 error with retry.
12. All `data-testid` attributes: `burndown-chart`, `burndown-loading`, `burndown-error`, `burndown-retry-button`.

## Out of Scope

- Scope change visualization (showing when issues were added/removed from milestone).
- Multiple milestone comparison on a single chart.
- Print/export chart functionality.
- Backend changes — this feature consumes the endpoint built in `milestone-burndown-endpoint`.

## Definition of Done

- `BurndownChart` component renders a line/area chart with open and closed issue counts from mocked API data.
- Ideal burndown reference line is visible.
- Milestone title, start date, and due date are displayed.
- Loading indicator appears during fetch.
- Appropriate error messages appear for 404, 422, and 502 responses.
- Retry button works for 502 errors.
- All `data-testid` attributes are present.
- Component test file `BurndownChart.test.tsx` exists and all tests pass.
- `eslint --max-warnings 0` and `tsc --noEmit` pass.
- `vitest` passes with all new tests green.
- No additional charting library added beyond what `ai-pipeline-dashboard-ui` introduced.