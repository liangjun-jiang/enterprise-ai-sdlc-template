# Data Models

## Current State

**No database.** This service has no persistent storage. There are no ORM models, no migrations, no connection pools.

All data returned by the API is either:
- Derived from environment variables at startup
- Computed inline in the route handler
- Hardcoded constants (e.g., `{"status": "ok"}`)

---

## Pydantic as the Contract Layer

All API request bodies and response bodies **must** be typed with Pydantic models, even when they are trivially simple. This enforces:
1. Automatic OpenAPI schema generation
2. Input validation at the boundary
3. A single source of truth for payload shape

### Conventions

- Models live in `backend/app/models/`
- One file per logical domain (e.g., `models/health.py`, `models/version.py`)
- Request models: suffix `Request` (e.g., `CreateItemRequest`)
- Response models: suffix `Response` (e.g., `HealthResponse`)
- No shared request/response models — keep them separate even if fields overlap

### Example

```python
# backend/app/models/health.py
from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str
```

```python
# backend/app/main.py
from app.models.health import HealthResponse

@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
```

---

## Defined Models

### `AiMetricsResponse` (`backend/app/models/ai_metrics.py`)

Response body for the AI pipeline metrics endpoint.

| Field | Type | Description |
|-------|------|-------------|
| `period` | `str` | Echoed query parameter — `'this_week'` or `'this_month'` |
| `period_start` | `date` | ISO-8601 date of the period start (Monday or 1st of month) |
| `period_end` | `date` | ISO-8601 date of today (UTC) |
| `plans_generated` | `int` | Count of issues with labels `ai-generated` and `ai-plan` |
| `issues_created_by_ai` | `int` | Count of issues with label `ai-generated` |
| `ai_prs_opened` | `int` | Count of pull requests with label `ai-generated` |
| `ai_prs_merged` | `int` | Subset of `ai_prs_opened` that are merged |
| `ai_prs_rejected_closed` | `int` | Subset of `ai_prs_opened` that are closed but not merged |

**Companion helpers in the same module:**

- `compute_period_range(period: str) -> tuple[date, date]` — returns `(period_start, today)` for `'this_week'` (Monday-anchored) or `'this_month'` (1st-of-month-anchored); raises `ValueError` for unrecognised values.
- `validate_github_env() -> None` — raises `RuntimeError` at startup if `GITHUB_TOKEN` or `GITHUB_REPO` are missing, or if `GITHUB_REPO` does not match the `owner/repo` format.

---

## When a Database Is Added

Before adding any database integration, the following must happen first:

1. Update this file with the entity definitions and field types
2. Update `CURRENT_TECH_STACK.md` with the chosen ORM and migration tool
3. Update `ARCHITECTURE.md` with the new service topology
4. Create an `alembic/` directory (if using SQLAlchemy + Alembic)

Do not add `sqlalchemy` or any DB driver to `pyproject.toml` without completing the above.
