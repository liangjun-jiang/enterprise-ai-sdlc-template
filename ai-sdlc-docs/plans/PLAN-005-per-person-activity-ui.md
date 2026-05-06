---
authors:
  - AI-generated
approvers:
  - ""
feature: per-person-activity-ui
priority: medium
milestone: milestone-002-hierarchy-and-analytics
prd_ref: docs/prd/prd-000-dashboard.md
assignees:
  planning: ""
  development: ""
  review: ""
  qa: ""
---

# Feature Plan: Per-Person Activity UI

## Summary

Build a frontend page that displays a filterable table of team members with per-person activity summaries (issues closed, PRs merged, reviews posted) and inline sparklines for the selected time period. This gives Project Managers at-a-glance workload visibility.

## Background

The PRD requires that a PM can see per-person activity summaries including issues closed, PRs merged, and reviews posted for this week or this month. The `per-person-activity-endpoint` provides the data per user; this feature builds the UI that aggregates and displays it. The page must allow filtering by time period and present data in a scannable table format with visual indicators of activity levels.

## Requirements

1. Create a page component `frontend/src/pages/ActivityPage.tsx` that serves as the container for the activity view.
2. Create a component `frontend/src/components/ActivityTable.tsx` that renders the table of team members and their activity.
3. Create a component `frontend/src/components/Sparkline.tsx` that renders a small inline SVG sparkline chart (no external charting library).
4. The page must accept a configurable list of team member GitHub logins. For Phase 0, this list is hardcoded as a constant in `frontend/src/config/team.ts` (e.g., `export const TEAM_MEMBERS = ["octocat", "..."]; `). This can be made dynamic later.
5. On mount and when the period filter changes, the page must call `GET /api/v1/activity?assignee={login}&period={period}` for each team member (parallel fetches).
6. The page must include a period selector (dropdown or toggle) with options:
   - "This Week" (value: `this_week`)
   - "This Month" (value: `this_month`)
   The selector must have `data-testid="period-selector"`.
7. The activity table must display one row per team member with columns:
   - **Assignee**: GitHub login (linked to `https://github.com/{login}` in a new tab)
   - **Issues Closed**: count + sparkline
   - **PRs Merged**: count + sparkline
   - **Reviews Posted**: count + sparkline
8. The sparkline for each metric should visualize a simple proportional bar or mini-bar relative to the maximum value across all team members for that metric (providing at-a-glance comparison).
9. The table must be sortable by any numeric column (clicking a column header toggles ascending/descending sort).
10. While data is loading, display a loading indicator with `data-testid="activity-loading"`.
11. If any individual fetch fails, display that user's row with an error indicator rather than failing the entire table.
12. If all fetches fail, display a full-page error with `data-testid="activity-error"`.
13. Define TypeScript types for the activity response in `frontend/src/types/activity.ts` matching the API contract.
14. Add `data-testid` attributes:
    - `activity-table` on the table element
    - `activity-row-{login}` on each row
    - `activity-count-issues-{login}`, `activity-count-prs-{login}`, `activity-count-reviews-{login}` on count cells
15. Write tests in `frontend/src/pages/ActivityPage.test.tsx` and `frontend/src/components/ActivityTable.test.tsx`:
    - Test that loading state is shown initially
    - Test that the table renders rows for each team member after successful fetch
    - Test that changing the period selector triggers new fetches
    - Test that a failed fetch for one user shows an error indicator in that row only
    - Test that sorting by a column reorders rows correctly
    - Test that counts display correct values from the API response
16. Use no external UI library or charting library — plain CSS/CSS modules and inline SVG for sparklines.
17. All components must be functional components with explicit prop types.

## Out of Scope

- Dynamic team member discovery from GitHub (hardcoded list for now)
- Custom date range picker
- Drill-down into individual activity items (clicking a count to see the list of issues/PRs)
- Export to CSV or PDF
- Real-time updates or WebSocket subscriptions
- Routing integration (standalone page for now)

## Definition of Done

- [ ] `ActivityPage.tsx` fetches activity data for all configured team members
- [ ] `ActivityTable.tsx` renders a sortable table with one row per team member
- [ ] `Sparkline.tsx` renders inline SVG sparklines without external dependencies
- [ ] Period selector toggles between `this_week` and `this_month` and triggers re-fetch
- [ ] Counts for issues closed, PRs merged, and reviews posted are displayed correctly
- [ ] Table is sortable by any numeric column
- [ ] Loading and error states are handled gracefully with appropriate `data-testid` attributes
- [ ] Partial failures (one user's fetch fails) do not break the entire table
- [ ] TypeScript types match the API contract
- [ ] All tests pass via `vitest`
- [ ] ESLint passes with `--max-warnings 0`
- [ ] `tsc --noEmit` passes with no errors
- [ ] No `any` types used
- [ ] No hardcoded backend URLs
- [ ] No external charting or UI component libraries added
