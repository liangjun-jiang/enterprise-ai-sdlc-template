## Title
[feature]: PR list view

## Summary
- What problem are we solving?
A: right now we show a total count of PR opened, PR merged. We want to show the list of PR opened, or merged with the PR title and timestamp.
- Why does this matter?
A: we can get an better idea about what PR is opened/merged.

<!-- ai-implementation-plan -->
## AI Implementation Plan (v1)
_Generated at 2026-05-11 19:00 UTC_

## Implementation Plan

### Scope
Add a PR list view feature: when a user clicks a PR count tile (opened or merged), a modal/panel appears showing a list of PRs with title and timestamp, fetched live from the GitHub API.

### Assumptions
1. The existing backend already has a GitHub token available via environment variable (e.g., `GITHUB_TOKEN`) and a configured repo owner/name.
2. The frontend already renders "PR opened" and "PR merged" count tiles as clickable or easily made clickable elements.
3. "Opened" PRs = state `open`; "Merged" PRs = state `closed` and merged.
4. The PR list will be displayed in a modal overlay (no routing change needed).
5. Pagination is out of scope for this PR — we fetch a reasonable default (e.g., first 30 PRs).
6. The GitHub API is called server-side (backend proxies to GitHub) so the token is never exposed to the browser.

---

### Proposed Changes

**Step 1 — Backend: Pydantic models**
Create `backend/app/models/pr.py` with:
- `PRItem` model: `number: int`, `title: str`, `url: str`, `created_at: str`, `merged_at: str | None`, `state: str`
- `PRListResponse` model: `prs: list[PRItem]`, `total: int`

**Step 2 — Backend: New router endpoint**
Create `backend/app/routers/prs.py` with a `GET /api/prs` endpoint:
- Query param: `state: Literal["open", "merged"]`
- Use `httpx.AsyncClient` to call `GET https://api.github.com/repos/{owner}/{repo}/pulls` with `state=open` or `state=closed` (filter merged server-side for the merged case).
- Return `PRListResponse`.
- Register router in `main.py`.

**Step 3 — Backend: Tests**
Add `backend/app/test_prs.py`:
- Mock `httpx.AsyncClient` responses.
- Test `state=open` returns open PRs.
- Test `state=merged` returns only merged PRs (filters out closed-but-not-merged).
- Test GitHub API error propagates as 502.

**Step 4 — Frontend: PRListModal component**
Create `frontend/src/components/PRListModal.tsx`:
- Props: `{ state: "open" | "merged", onClose: () => void }`
- Fetches `/api/prs?state={state}` on mount.
- Shows a loading indicator (`data-testid="pr-list-loading"`), error state, or list of PRs with title + formatted timestamp + link.
- Accessible: uses a `<dialog>` or role="dialog" with focus trap basics.

**Step 5 — Frontend: Wire modal into existing tile**
In the component that renders the PR count tiles:
- Add `useState` for `activeFilter: "open" | "merged" | null`.
- Make the count tiles `<button>` elements (if not already) with `onClick` handlers.
- Render `<PRListModal>` when `activeFilter` is non-null.
- Add `data-testid="pr-open-tile"` and `data-testid="pr-merged-tile"`.

**Step 6 — Frontend: Tests**
Add `frontend/src/components/PRListModal.test.tsx`:
- Mock `fetch` with `vi.stubGlobal`.
- Test loading state renders.
- Test PR list renders with title and timestamp after fetch resolves.
- Test modal closes on button click.
- Test in the parent tile component that clicking the count opens the modal.

---

### Test Plan
- Backend: `pytest backend/` — all new tests pass, mypy strict passes, ruff clean.
- Frontend: `vitest run` — PRListModal and tile-click tests pass, ESLint zero warnings.
- Manual: click "PR opened" tile → modal shows open PRs with titles and dates; click "PR merged" tile → modal shows merged PRs; close button dismisses modal.

---

### Risks
- **GitHub API rate limits**: unauthenticated = 60 req/hr. Mitigation: ensure `GITHUB_TOKEN` is always set; document this as a required env var.
- **Large PR lists**: repos with many PRs may return slow responses. Mitigation: cap at 30 items per request (default GitHub page size); pagination is out of scope.
- **GitHub token exposure**: token must stay server-side only — the backend proxies the call. Frontend never receives the token.

---

### Out of Scope
- Pagination / infinite scroll of PR list
- Showing GitHub Issues
- PR detail view (comments, diffs)
- Caching / server-side pagination
- Filtering by date range or author

---

## Ready for Coding Checklist
- [x] Requirements are clear
- [x] Acceptance criteria are testable
- [x] Dependencies/risks are identified
- [x] Scope is bounded for one PR

---

## Open Questions
1. What are the exact environment variable names used for `GITHUB_TOKEN`, repo owner, and repo name in the existing backend? (Needed to wire up the new endpoint consistently.)
2. What is the existing component/file name that renders the PR count tiles? (Needed to know exactly where to add the click handler in Step 5.)
3. Should the PR list be sorted by most-recent first, or follow GitHub's default ordering?
4. Is there a maximum number of PRs to display, or is 30 (one GitHub API page) acceptable for now?