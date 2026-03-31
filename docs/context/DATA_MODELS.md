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

## When a Database Is Added

Before adding any database integration, the following must happen first:

1. Update this file with the entity definitions and field types
2. Update `CURRENT_TECH_STACK.md` with the chosen ORM and migration tool
3. Update `ARCHITECTURE.md` with the new service topology
4. Create an `alembic/` directory (if using SQLAlchemy + Alembic)

Do not add `sqlalchemy` or any DB driver to `pyproject.toml` without completing the above.
