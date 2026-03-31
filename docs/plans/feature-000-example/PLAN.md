# Feature Plan: Add /version Endpoint

## Summary

Add a `GET /api/v1/version` endpoint to the FastAPI backend that returns the application version, current git SHA, and runtime environment. Display this information in the React frontend alongside the health status.

This is a small, self-contained feature that exercises the full stack: a new backend endpoint with a Pydantic response model, a frontend fetch call, and tests for both.

## Background

Currently the app only exposes `GET /health`. Teams deploying this service have no way to confirm which version is running or which git commit is deployed. This endpoint provides that signal without requiring SSH access to the container.

## Requirements

1. **Backend:** `GET /api/v1/version` returns JSON:
   ```json
   {
     "version": "0.1.0",
     "git_sha": "abc1234",
     "environment": "development"
   }
   ```
   - `version`: read from `pyproject.toml` at startup (do not hardcode)
   - `git_sha`: first 7 characters of `GIT_SHA` environment variable; fall back to `"unknown"` if not set
   - `environment`: value of `APP_ENV` environment variable; fall back to `"development"` if not set

2. **Frontend:** Display version info below the health status on the main page, using `data-testid="version-info"`.

3. **Tests:** Both backend and frontend changes must include unit tests.

4. **No new dependencies.** Use only what is already installed.

## Out of Scope

- No authentication on this endpoint
- No caching
- No build-time injection of git SHA (runtime env var is sufficient)
- No change to the `/health` endpoint

## Definition of Done

- `GET /api/v1/version` returns `200` with the correct JSON shape
- `version` field matches `pyproject.toml`
- `git_sha` returns `"unknown"` when `GIT_SHA` is not set
- `environment` returns `"development"` when `APP_ENV` is not set
- Frontend displays version info in the DOM with `data-testid="version-info"`
- All existing tests continue to pass
- CI (ruff + mypy + pytest + eslint + vitest) passes clean
