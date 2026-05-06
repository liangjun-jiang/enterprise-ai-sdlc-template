---
authors:
  - AI-generated
approvers:
  - ""
feature: traceability-search
priority: medium
milestone: milestone-003-ai-metrics-and-polish
prd_ref: docs/prd/prd-000-dashboard.md
assignees:
  planning: ""
  development: ""
  review: ""
  qa: ""
---

# Feature Plan: Traceability Search

## Summary

Implement a frontend search/filter on the hierarchy view that allows a Product Owner to enter a PR number or merged PR URL and see the full traceability chain back to the originating PRD requirement (PR → Task Issue → Feature Plan → Milestone → PRD). This may require a new backend endpoint to resolve the trace.

## Background

PRD success metric #2 states: "A Product Owner can trace any merged PR back to its originating PRD requirement." The existing hierarchy view shows the PRD → Milestone → Feature Plan → Task Issue structure, but there is no reverse lookup capability. Product Owners need to quickly verify that a specific PR ties back to a planned requirement, especially for audit and compliance scenarios. The AI-SDLC pipeline encodes traceability through issue labels, PR descriptions referencing issue numbers, and the naming conventions in `docs/` — this feature surfaces that chain in the UI.

## Requirements

1. Create a `GET /api/v1/trace` backend endpoint that accepts a query parameter `pr` (either a PR number like `42` or a full GitHub PR URL like `https://github.com/owner/repo/pull/42`) and returns the full traceability chain.
2. The trace response must include: `pr` (number, title, state, URL), `linked_issue` (number, title, labels, URL — the task issue the PR closes/references), `feature_plan` (slug, title — derived from issue labels or milestone association), `milestone` (id, title), and `prd` (id, title — derived from milestone metadata or label conventions).
3. If any link in the chain cannot be resolved, that field must be `null` with a `trace_complete: false` flag, so the UI can indicate a broken trace.
4. If the PR number does not exist, return `404 Not Found`.
5. The endpoint must parse PR descriptions for `Closes #N`, `Fixes #N`, or `Resolves #N` patterns to identify the linked issue. It must also check the GitHub API's linked issues for the PR.
6. A Pydantic response model `TraceResponse` must be defined in `backend/app/models/trace.py`.
7. The router must live in `backend/app/routers/trace.py` and be registered in `main.py`.
8. Create a `TraceabilitySearch` frontend component in `frontend/src/components/TraceabilitySearch.tsx`.
9. The component must render a search input field (`data-testid="trace-search-input"`) and a search button (`data-testid="trace-search-button"`).
10. The input must accept either a PR number or a full PR URL. On submit, call `GET /api/v1/trace?pr={value}`.
11. Results must display the full trace chain visually (e.g., breadcrumb or vertical flow: PRD → Milestone → Feature Plan → Issue → PR) with `data-testid="trace-result"`.
12. If `trace_complete` is `false`, highlight the broken link in the chain with a warning indicator.
13. If the PR is not found (404), show "PR not found" with `data-testid="trace-not-found"`.
14. Loading state with `data-testid="trace-loading"` during the API call.
15. The component must be accessible from the hierarchy view — either embedded as a search bar at the top or as a dedicated tab/panel.
16. Backend unit tests: valid PR with full trace, PR with broken trace (missing issue link), PR not found → 404, GitHub API failure → 502. All GitHub calls mocked.
17. Frontend component tests: successful full trace render, partial trace with warning, PR not found, loading state, error state.
18. The endpoint contract must be added to `API_CONTRACTS.md`.

## Out of Scope

- Full-text search across all PRDs, milestones, or issues — this is a targeted PR-to-PRD reverse lookup only.
- Batch trace (tracing multiple PRs at once).
- Forward tracing from PRD requirement to all related PRs (the hierarchy view already covers this direction).
- Editing or creating links between artifacts.

## Definition of Done

- `GET /api/v1/trace?pr=42` returns `200` with a `TraceResponse` showing the full chain (mocked in tests).
- `GET /api/v1/trace?pr=https://github.com/owner/repo/pull/42` also resolves correctly.
- `GET /api/v1/trace?pr=99999` (non-existent PR) returns `404`.
- Broken trace chains return `trace_complete: false` with `null` for unresolvable links.
- Backend tests pass with all GitHub calls mocked.
- `TraceabilitySearch` component renders search input, submits query, and displays trace chain from mocked API.
- Partial trace shows warning indicator.
- Not-found state displays appropriate message.
- All `data-testid` attributes are present.
- `ruff check`, `ruff format`, `mypy --strict` pass for backend.
- `eslint --max-warnings 0`, `tsc --noEmit`, `vitest` pass for frontend.
- `API_CONTRACTS.md` is updated with the `/api/v1/trace` endpoint contract.