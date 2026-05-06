---
authors:
  - AI-generated
approvers:
  - ""
feature: hierarchy-view-endpoint
priority: medium
milestone: milestone-002-hierarchy-and-analytics
prd_ref: docs/prd/prd-000-dashboard.md
assignees:
  planning: ""
  development: ""
  review: ""
  qa: ""
---

# Feature Plan: Hierarchy View Endpoint

## Summary

Expose a `GET /api/v1/hierarchy` endpoint that returns the full PRD → Milestone → Feature Plan → Task Issue tree as nested JSON, with status roll-ups at each level. This endpoint is the API contract consumed by the hierarchy tree UI.

## Background

The hierarchy data engine (feature `hierarchy-data-engine`) reconstructs the project hierarchy from GitHub data. This feature wraps that engine in a FastAPI endpoint so the frontend (and any other consumer) can retrieve the hierarchy over HTTP. The PRD requires that a Product Owner can trace any merged PR back to its originating PRD requirement — this endpoint provides the data to make that possible. Per the architecture, all new endpoints go under `/api/v1/` and must be documented in `API_CONTRACTS.md`.

## Requirements

1. Create a router file `backend/app/routers/hierarchy.py` containing the `GET /api/v1/hierarchy` endpoint.
2. Register the router in `backend/app/main.py`.
3. The endpoint must call the hierarchy data engine (from `backend/app/services/hierarchy.py`) to build the tree.
4. The endpoint must return a JSON response with the following top-level structure:
   ```json
   {
     "prds": [
       {
         "id": "prd-000",
         "title": "AI-SDLC Demo Dashboard",
         "status": "in-progress",
         "html_url": "https://github.com/...",
         "milestones": [
           {
             "id": "milestone-001",
             "title": "...",
             "status": "done",
             "html_url": "...",
             "features": [
               {
                 "id": "feature-slug",
                 "title": "...",
                 "status": "in-progress",
                 "html_url": "...",
                 "tasks": [
                   {
                     "id": 42,
                     "title": "...",
                     "status": "open",
                     "html_url": "...",
                     "assignee": "octocat",
                     "linked_prs": [{"number": 55, "html_url": "...", "state": "merged"}]
                   }
                 ]
               }
             ]
           }
         ]
       }
     ]
   }
   ```
5. Define a `HierarchyResponse` Pydantic model in `backend/app/models/hierarchy.py` (extending or composing the models from `hierarchy-data-engine`) that serves as the `response_model`.
6. The endpoint must return `200 OK` on success.
7. If the GitHub API is unreachable or returns a rate-limit error, the endpoint must return `502 Bad Gateway` with a JSON body `{"detail": "GitHub API unavailable"}` or `{"detail": "GitHub API rate limit exceeded"}`.
8. If `GITHUB_TOKEN` or `GITHUB_REPO` is misconfigured, the endpoint must return `503 Service Unavailable` with `{"detail": "GitHub integration not configured"}`.
9. The route handler must be `async def`.
10. Write tests in `backend/app/routers/test_hierarchy.py` using `httpx.AsyncClient` with `ASGITransport`. Tests must cover:
    - Successful 200 response with a mocked hierarchy engine return value
    - 502 response when the engine raises a GitHub API error
    - Response schema matches `HierarchyResponse`
11. Update `API_CONTRACTS.md` with the full contract for `GET /api/v1/hierarchy`.

## Out of Scope

- The hierarchy reconstruction logic itself (that is `hierarchy-data-engine`)
- Frontend rendering (that is `hierarchy-tree-ui`)
- Filtering or searching within the hierarchy (Phase 3)
- Caching headers or ETag support
- Pagination of the hierarchy response (the tree is returned in full)

## Definition of Done

- [ ] `GET /api/v1/hierarchy` returns a nested JSON tree with PRDs, milestones, features, and tasks
- [ ] `HierarchyResponse` Pydantic model validates the response shape
- [ ] Status roll-ups are present at every level (prd, milestone, feature)
- [ ] GitHub API errors result in 502 responses with descriptive messages
- [ ] Missing configuration results in 503 responses
- [ ] Route handler is `async def`
- [ ] Tests pass with mocked hierarchy engine
- [ ] `API_CONTRACTS.md` is updated with the full endpoint contract
- [ ] All code passes `ruff check`, `ruff format --check`, and `mypy --strict`
- [ ] All tests pass via `pytest`
