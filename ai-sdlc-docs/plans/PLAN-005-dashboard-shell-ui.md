---
authors:
  - AI-generated
approvers:
  - ""
feature: dashboard-shell-ui
priority: medium
milestone: milestone-001-mvp
prd_ref: docs/prd/prd-000-dashboard.md
assignees:
  planning: ""
  development: ""
  review: ""
  qa: ""
---

# Feature Plan: Dashboard Shell UI

## Summary

Build the React SPA shell with a navigation bar, backend health indicator, and a single Overview page that displays a milestone progress table and a combined issues/PRs list. This is the user-facing surface that consumes the backend endpoints built in earlier features.

## Background

The milestone goal states: "Let a PM see milestone completion percentage and let a developer see their assigned issues and PR status from a single page, without opening GitHub." The frontend must fetch data from the backend API via relative URLs (per ARCHITECTURE.md) and present it in a clean, functional interface. The current frontend is a minimal React + Vite setup with no routing or data fetching — this feature builds out the first real page.

## Requirements

1. Create a persistent navigation bar component (`frontend/src/components/NavBar.tsx`):
   - Display the app title "AI-SDLC Dashboard" on the left.
   - Display a health indicator dot on the right that polls `GET /health` every 30 seconds.
   - Health indicator: green dot when status is `"ok"`, red dot when the request fails.
   - Add `data-testid="health-indicator"` to the health dot element.

2. Create an Overview page component (`frontend/src/pages/Overview.tsx`):
   - This is the default (and only) page for the MVP.

3. Implement a Milestone Progress section on the Overview page:
   - Fetch data from `GET /api/v1/milestones` on page load.
   - Display a table with columns: Title, State, Open Issues, Closed Issues, Completion %, Due Date.
   - Completion percentage should display as a number with one decimal place and a simple progress bar (CSS-only, no charting library).
   - Add `data-testid="milestone-table"` to the table element.
   - Show a loading state while fetching.
   - Show an error message if the fetch fails.

4. Implement an Issues & PRs section on the Overview page:
   - Fetch data from `GET /api/v1/issues?state=open` and `GET /api/v1/pull-requests?state=open` on page load.
   - Display a combined table with columns: Type (Issue/PR), Number, Title, State, Assignee, Labels, Draft (PRs only).
   - Issues and PRs should be visually distinguishable (e.g., different badge/icon for type).
   - Add `data-testid="issues-prs-table"` to the table element.
   - Show loading and error states.

5. All data fetching must use `fetch()` with relative URLs (e.g., `/api/v1/milestones`) — never hardcoded base URLs.

6. Define TypeScript types for all API response shapes in `frontend/src/types/api.ts`:
   - `MilestoneSummary`, `MilestoneListResponse`, `Issue`, `IssueListResponse`, `PullRequest`, `PullRequestListResponse`.
   - These types must match the Pydantic response models.

7. Update `frontend/src/App.tsx` to render `NavBar` and `Overview` as the default view.

8. No CSS framework — use plain CSS or CSS modules for styling. Keep it functional, not polished.

9. Create tests:
   - `frontend/src/components/NavBar.test.tsx`: Test that the health indicator shows green on successful `/health` response and red on failure. Mock `fetch`.
   - `frontend/src/pages/Overview.test.tsx`: Test that milestone table renders with mocked data. Test that issues/PRs table renders with mocked data. Test loading state appears. Test error state appears on fetch failure.

10. All code must pass `tsc --noEmit`, `eslint --max-warnings 0`, and `vitest`.

## Out of Scope

- Client-side routing (single page is sufficient for MVP).
- Per-user filtering in the UI (all open issues/PRs are shown).
- State management library (React state + `useEffect` is sufficient).
- CSS framework or design system.
- Dark mode or theming.
- Mobile-responsive layout (desktop-first is fine for MVP).
- Real-time updates or WebSocket connections.

## Definition of Done

- Navigation bar displays with app title and health indicator.
- Health indicator polls `/health` and shows green/red status.
- Overview page loads and displays a milestone progress table with data from `/api/v1/milestones`.
- Overview page displays a combined issues/PRs table with data from `/api/v1/issues` and `/api/v1/pull-requests`.
- Loading and error states are implemented for both data sections.
- TypeScript types for API responses exist in `frontend/src/types/api.ts`.
- All `data-testid` attributes are present on key elements.
- All tests pass (`vitest`).
- `tsc --noEmit` passes with no errors.
- `eslint --max-warnings 0` passes.
- No hardcoded backend URLs in frontend source.
- The app works in both Vite dev mode (proxy to backend) and Docker (nginx proxy).
