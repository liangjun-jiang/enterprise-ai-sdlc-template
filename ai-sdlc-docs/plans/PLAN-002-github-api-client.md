---
authors:
  - AI-generated
approvers:
  - ""
feature: github-api-client
priority: medium
milestone: milestone-001-mvp
prd_ref: docs/prd/prd-000-dashboard.md
assignees:
  planning: ""
  development: ""
  review: ""
  qa: ""
---

# Feature Plan: GitHub API Client

## Summary

Build a backend service layer that authenticates with the GitHub REST API using a `GITHUB_TOKEN` environment variable and provides async methods to fetch issues, pull requests, milestones, labels, and assignees for a configured repository. The client must handle rate limiting, error mapping, and provide a clean internal interface that the API routers will consume.

## Background

The PRD states that the dashboard reads all data from the GitHub API — GitHub is the sole source of truth with no database. Every endpoint in this milestone depends on a reliable, well-tested GitHub API client. The CODING_STANDARDS.md mandates `httpx.AsyncClient` for all outbound HTTP calls. The SECURITY_CHECKLIST.md requires that tokens are read exclusively from environment variables and that missing env vars cause a startup error.

## Requirements

1. Create `backend/app/services/__init__.py` (empty) and `backend/app/services/github_client.py`.

2. Implement a `GitHubClient` class that:
   - Accepts `token` (str) and `repo` (str, format `owner/repo`) as constructor parameters.
   - Uses `httpx.AsyncClient` as the underlying HTTP client with `Authorization: Bearer <token>` header and `Accept: application/vnd.github+json` header.
   - Exposes an async context manager (`async with GitHubClient(...) as client:`) or explicit `close()` method to manage the httpx client lifecycle.

3. Implement the following async methods on `GitHubClient`:
   - `get_milestones(state: str = "all") -> list[dict]` — fetches all milestones for the repo.
   - `get_milestone(milestone_number: int) -> dict` — fetches a single milestone.
   - `get_issues(state: str = "open", assignee: str | None = None, labels: str | None = None, milestone: str | None = None) -> list[dict]` — fetches issues with optional filters, excluding pull requests.
   - `get_pull_requests(state: str = "open", assignee: str | None = None) -> list[dict]` — fetches pull requests with optional filters.
   - All list methods must handle GitHub pagination (follow `Link` header `rel="next"`) to retrieve all results.

4. Implement rate-limit handling:
   - Read `X-RateLimit-Remaining` and `X-RateLimit-Reset` headers from every response.
   - When `X-RateLimit-Remaining` reaches 0, `await asyncio.sleep()` until the reset timestamp before making the next request.
   - Log a warning (via `logging`) when remaining requests drop below 10.

5. Implement error mapping:
   - 401 → raise a custom `GitHubAuthError` exception.
   - 403 (rate limit) → raise a custom `GitHubRateLimitError` exception.
   - 404 → raise a custom `GitHubNotFoundError` exception.
   - 5xx → raise a custom `GitHubAPIError` exception.
   - All custom exceptions live in `backend/app/services/exceptions.py` and include the HTTP status code and response body.

6. Create a module-level factory function `get_github_client() -> GitHubClient` that reads `GITHUB_TOKEN` and `GITHUB_REPO` from environment variables. If either is missing, raise `RuntimeError` at call time with a descriptive message.

7. Create `backend/app/services/test_github_client.py` with tests:
   - Mock `httpx.AsyncClient` responses to verify each method parses GitHub API JSON correctly.
   - Test pagination handling with mocked `Link` headers.
   - Test that 401, 403, 404, and 5xx responses raise the correct custom exceptions.
   - Test that `get_github_client()` raises `RuntimeError` when env vars are missing.
   - Test rate-limit sleep behavior (mock `asyncio.sleep`).

8. All code must pass `mypy --strict` and `ruff check`.

9. Update `CURRENT_TECH_STACK.md` to note that `httpx` is now also used as the GitHub API client (not just for tests).

## Out of Scope

- Caching or storing GitHub responses (no database in this milestone).
- Write operations (creating issues, commenting, etc.).
- GraphQL API — use REST API v3 only.
- OAuth or per-user authentication — single `GITHUB_TOKEN` only.
- Webhook handling.

## Definition of Done

- `GitHubClient` class exists in `backend/app/services/github_client.py` with all specified methods.
- Custom exceptions exist in `backend/app/services/exceptions.py`.
- All methods handle pagination correctly.
- Rate-limit handling sleeps when remaining requests hit 0.
- Error responses map to specific exception types.
- `get_github_client()` fails fast when env vars are missing.
- All tests in `test_github_client.py` pass.
- `mypy --strict` passes with no errors.
- `ruff check` and `ruff format` pass with no issues.
- `CURRENT_TECH_STACK.md` is updated.
