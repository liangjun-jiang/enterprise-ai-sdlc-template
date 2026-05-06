---
authors:
  - AI-generated
approvers:
  - ""
feature: ai-pipeline-dashboard-ui
priority: medium
milestone: milestone-003-ai-metrics-and-polish
prd_ref: docs/prd/prd-000-dashboard.md
assignees:
  planning: ""
  development: ""
  review: ""
  qa: ""
---

# Feature Plan: AI Pipeline Dashboard UI

## Summary

Build a dedicated dashboard panel in the React frontend that displays AI pipeline summary cards (plans generated, AI PRs merged vs. rejected) and a trend chart showing AI activity over the last 4 weeks. The panel consumes the `GET /api/v1/ai-metrics` endpoint.

## Background

PRD success metric #3 requires that "AI pipeline activity (plans generated, issues created, PRs opened/reviewed) is visible on a single dashboard." The backend endpoint (`ai-pipeline-metrics-endpoint`) provides the raw data; this feature renders it in a user-friendly panel. The dashboard must let Tech Leads quickly assess AI pipeline health without navigating to GitHub. The trend chart requires fetching metrics for multiple periods (weekly buckets over 4 weeks) and rendering them visually.

## Requirements

1. Create an `AiPipelineDashboard` component in `frontend/src/components/AiPipelineDashboard.tsx`.
2. The component must display five summary cards: "Plans Generated", "Issues Created by AI", "AI PRs Opened", "AI PRs Merged", "AI PRs Rejected/Closed".
3. Each card must show the numeric count for the selected period and be identifiable via `data-testid` attributes (e.g., `data-testid="ai-metric-plans-generated"`).
4. A period toggle ("This Week" / "This Month") must allow switching between `this_week` and `this_month` API calls. Default to `this_week`.
5. The component must display a trend chart showing weekly AI activity (PRs opened, merged, rejected) for the last 4 weeks. The chart must use a lightweight charting library (e.g., Recharts or Chart.js via react-chartjs-2). The chosen library must be added to `CURRENT_TECH_STACK.md`.
6. The trend chart data may require 4 separate API calls (one per week) or a single `this_month` call with client-side bucketing — the implementation must document the chosen approach.
7. Loading state: while fetching, show a loading indicator with `data-testid="ai-metrics-loading"`.
8. Error state: if the API call fails, show an error message with `data-testid="ai-metrics-error"` and a retry button.
9. The panel must be integrated into the main dashboard page (`App.tsx` or a dashboard page component).
10. All API calls must use relative URLs (`/api/v1/ai-metrics?period=...`).
11. Component tests must cover: successful data render (mocked fetch), loading state, error state, period toggle switches the displayed data.
12. No `any` types. All API response shapes must be typed.

## Out of Scope

- Drill-down from a summary card to individual PR/issue lists.
- Real-time/WebSocket updates — data refreshes on page load or manual toggle.
- Custom date range picker beyond the two preset periods.
- Backend changes — this feature consumes the endpoint built in `ai-pipeline-metrics-endpoint`.

## Definition of Done

- `AiPipelineDashboard` component renders five summary cards with correct counts from mocked API data.
- Period toggle switches between "This Week" and "This Month" and re-fetches data.
- Trend chart renders with 4-week data points.
- Loading indicator appears during fetch.
- Error message and retry button appear on fetch failure.
- All `data-testid` attributes are present for testability.
- Component test file `AiPipelineDashboard.test.tsx` exists and all tests pass.
- `eslint --max-warnings 0` and `tsc --noEmit` pass.
- `vitest` passes with all new tests green.
- Charting library is added to `package.json` and documented in `CURRENT_TECH_STACK.md`.
- No `any` types in new code.