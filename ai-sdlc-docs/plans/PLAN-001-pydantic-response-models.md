---
authors:
  - AI-generated
approvers:
  - ""
feature: pydantic-response-models
priority: medium
milestone: milestone-001-mvp
prd_ref: docs/prd/prd-000-dashboard.md
assignees:
  planning: ""
  development: ""
  review: ""
  qa: ""
---

# Feature Plan: Pydantic Response Models

## Summary

Define all Pydantic models that represent the API response shapes for milestones, issues, and pull requests. These models are the contract layer between backend and frontend, and they must exist before any endpoint or service layer can be implemented.

## Background

The DATA_MODELS.md convention requires that all API response bodies are typed with Pydantic models. The PRD specifies that the dashboard reads data from GitHub API (issues, PRs, labels, milestones, assignees) and presents milestone completion percentage and per-user issue/PR lists. Before building endpoints or the GitHub API client, we need stable, well-defined response shapes that all other features can depend on. This also ensures automatic OpenAPI schema generation for frontend integration.

## Requirements

1. Create `backend/app/models/milestones.py` containing:
   - `MilestoneSummaryResponse` with fields: `id` (int), `title` (str), `state` (str), `open_issues` (int), `closed_issues` (int), `completion_percentage` (float), `html_url` (str), `due_on` (str | None).
   - `MilestoneListResponse` with field: `milestones` (list[MilestoneSummaryResponse]).

2. Create `backend/app/models/issues.py` containing:
   - `IssueResponse` with fields: `id` (int), `number` (int), `title` (str), `state` (str), `assignee` (str | None), `labels` (list[str]), `html_url` (str), `created_at` (str), `updated_at` (str).
   - `IssueListResponse` with field: `issues` (list[IssueResponse]).

3. Create `backend/app/models/pull_requests.py` containing:
   - `PullRequestResponse` with fields: `id` (int), `number` (int), `title` (str), `state` (str), `assignee` (str | None), `labels` (list[str]), `html_url` (str), `created_at` (str), `updated_at` (str), `draft` (bool), `merged_at` (str | None).
   - `PullRequestListResponse` with field: `pull_requests` (list[PullRequestResponse]).

4. Create `backend/app/models/errors.py` containing:
   - `ErrorResponse` with fields: `detail` (str).

5. All models must use `BaseModel` from Pydantic, follow the `Response` suffix convention from DATA_MODELS.md, and use Python 3.10+ type hint syntax (`str | None`, `list[str]`).

6. All models must pass `mypy --strict` without `type: ignore` comments.

7. Create `backend/app/models/test_models.py` with unit tests verifying:
   - Each model can be instantiated with valid data.
   - Each model rejects invalid data (e.g., missing required fields) by raising `ValidationError`.
   - `completion_percentage` is correctly represented as a float.
   - Serialization to dict produces the expected keys.

8. Update `API_CONTRACTS.md` with the response schemas for the planned endpoints (milestones, issues, pull-requests).

9. Update `DATA_MODELS.md` to document the new model files and their purpose.

## Out of Scope

- Request body models (no write operations in this milestone).
- Models for PRD → Milestone → Feature hierarchy (Phase 2).
- Models for AI pipeline metrics (Phase 3).
- Models for cycle time or burn-down data (Phase 3).
- Database ORM models — these are pure Pydantic response shapes.

## Definition of Done

- All model files exist under `backend/app/models/` with correct naming.
- `MilestoneSummaryResponse`, `MilestoneListResponse`, `IssueResponse`, `IssueListResponse`, `PullRequestResponse`, `PullRequestListResponse`, and `ErrorResponse` are importable.
- All models pass `mypy --strict`.
- All models pass `ruff check` and `ruff format` with no issues.
- Unit tests in `test_models.py` pass via `pytest`.
- `API_CONTRACTS.md` is updated with the new endpoint response schemas.
- `DATA_MODELS.md` is updated to reference the new model files.
