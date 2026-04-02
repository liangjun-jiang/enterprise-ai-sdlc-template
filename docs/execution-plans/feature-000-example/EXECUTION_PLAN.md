# Execution Plan: Add /version Endpoint

**Authors:** Jane Smith
**Approvers:** *(pending — fill in when execution plan PR is merged)*

## Summary

This plan implements a `GET /api/v1/version` endpoint on the FastAPI backend and surfaces the returned data in the React frontend. The work is split into three tasks: the backend model + endpoint, the backend router wiring + tests, and the frontend display component. Tasks 2 and 3 both depend on Task 1.

**Assumption:** `pyproject.toml` is read at application startup using `importlib.metadata` (standard library, no new dependency). The `version` string is the value of `project.version` in `backend/pyproject.toml`.

---

## Tasks

### Task 1: Add VersionResponse Pydantic model and version router

**ID:** TASK-001
**Depends on:** none
**Assignee:** *(unset — will be handled by AI code writer)*
**Affected files:**
- `backend/app/models/version.py` (create)
- `backend/app/routers/__init__.py` (create)
- `backend/app/routers/version.py` (create)

**Description:**
Create the `VersionResponse` Pydantic model and a FastAPI `APIRouter` with a single `GET /api/v1/version` route.

- `backend/app/models/version.py`: define `VersionResponse(BaseModel)` with three fields: `version: str`, `git_sha: str`, `environment: str`.
- `backend/app/routers/__init__.py`: empty file (package marker).
- `backend/app/routers/version.py`: define `router = APIRouter(prefix="/api/v1")`. Implement `GET /version` as an `async def` that:
  - Reads `version` via `importlib.metadata.version("enterprise-ai-sdlc-backend")`
  - Reads `git_sha` from `os.environ.get("GIT_SHA", "unknown")`, truncated to 7 chars
  - Reads `environment` from `os.environ.get("APP_ENV", "development")`
  - Returns `VersionResponse(version=..., git_sha=..., environment=...)`

**Acceptance criteria:**
- [ ] `VersionResponse` has exactly three fields: `version`, `git_sha`, `environment`, all `str`
- [ ] Router prefix is `/api/v1` and route path is `/version` (full path: `/api/v1/version`)
- [ ] `git_sha` is capped at 7 characters (e.g., `sha[:7]` or `sha[0:7]`)
- [ ] All three fields fall back to safe defaults when env vars are absent
- [ ] No new packages added to `pyproject.toml`

---

### Task 2: Register version router in main.py and add backend tests

**ID:** TASK-002
**Depends on:** TASK-001
**Assignee:** *(unset — will be handled by AI code writer)*
**Affected files:**
- `backend/app/main.py` (modify)
- `backend/app/test_version.py` (create)

**Description:**
Wire the version router into the FastAPI app and write pytest tests covering the endpoint behaviour.

- `backend/app/main.py`: add `from app.routers.version import router as version_router` and `app.include_router(version_router)`. No other changes.
- `backend/app/test_version.py`: write three tests using `httpx.ASGITransport(app=app)`:
  1. `test_version_returns_200`: asserts status code is 200.
  2. `test_version_returns_correct_shape`: asserts response JSON has keys `version`, `git_sha`, `environment`.
  3. `test_version_git_sha_defaults_to_unknown`: monkeypatches env to remove `GIT_SHA`, asserts `git_sha == "unknown"`.

**Acceptance criteria:**
- [ ] `GET /api/v1/version` returns `200` in tests
- [ ] Response body matches `VersionResponse` shape (all three string fields present)
- [ ] `git_sha` is `"unknown"` when `GIT_SHA` env var is not set (verified by a dedicated test)
- [ ] All three tests pass with `uv run pytest`
- [ ] `uv run ruff check .` passes with no errors
- [ ] `uv run mypy app` passes in strict mode

---

### Task 3: Display version info in the React frontend

**ID:** TASK-003
**Depends on:** TASK-001
**Assignee:** *(unset — will be handled by AI code writer)*
**Affected files:**
- `frontend/src/App.tsx` (modify)
- `frontend/src/App.test.tsx` (modify)

**Description:**
Extend `App.tsx` to fetch `/api/v1/version` and render the result. Update the tests to cover the new UI.

- `frontend/src/App.tsx`:
  - Add a second `useEffect` (or extend the existing one) to fetch `/api/v1/version`.
  - Define a `VersionInfo` type: `{ version: string; git_sha: string; environment: string }`.
  - Store the result in `useState<VersionInfo | null>(null)`.
  - Render a `<p data-testid="version-info">` element. When loading, show `"loading"`. On success, show `v{version} ({git_sha}) [{environment}]`. On error, show `"unavailable"`.

- `frontend/src/App.test.tsx`:
  - Add a test `renders version info after fetch`: mock `fetch` to return both `/health` and `/api/v1/version` responses, assert `data-testid="version-info"` contains the formatted string.
  - The existing heading test must continue to pass unchanged.

**Acceptance criteria:**
- [ ] `data-testid="version-info"` is present in the rendered output
- [ ] Version info displays in format `v{version} ({git_sha}) [{environment}]` when fetch succeeds
- [ ] Shows `"unavailable"` when the version fetch fails
- [ ] New test passes with `npm run test`
- [ ] `npm run lint` passes with no warnings
- [ ] Existing `renders the main heading` test is unmodified and still passes
