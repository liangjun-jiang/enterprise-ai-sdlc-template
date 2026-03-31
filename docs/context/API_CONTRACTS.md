# API Contracts

## Base URL

- **Local dev:** `http://localhost:8000`
- **Docker (from frontend container):** `http://backend:8000`
- **From browser:** relative paths only (proxy handles routing)

## Versioning Convention

- Current: no version prefix (bootstrap phase)
- Future endpoints: `/api/v1/<resource>`
- Breaking changes require a new version prefix — never modify an existing versioned endpoint's shape

---

## Endpoints

### `GET /health`

Health check. Used by Docker healthcheck and frontend status indicator.

**Request:** No parameters.

**Response `200 OK`:**
```json
{
  "status": "ok"
}
```

**Response schema:**
| Field | Type | Description |
|-------|------|-------------|
| `status` | `string` | Always `"ok"` when the service is running |

**Error responses:** None. If the service is down, the TCP connection fails.

---

## Planned Endpoints (from feature-000-example)

### `GET /api/v1/version`

Returns build metadata.

**Response `200 OK`:**
```json
{
  "version": "0.1.0",
  "git_sha": "abc1234",
  "environment": "development"
}
```

**Response schema:**
| Field | Type | Description |
|-------|------|-------------|
| `version` | `string` | Value of `project.version` from `pyproject.toml` |
| `git_sha` | `string` | First 7 chars of `GIT_SHA` env var, or `"unknown"` |
| `environment` | `string` | Value of `APP_ENV` env var, default `"development"` |

---

## Contract Rules

1. All responses are JSON (`Content-Type: application/json`)
2. All success responses use `2xx` status codes
3. Validation errors return `422 Unprocessable Entity` (FastAPI default)
4. Unexpected errors return `500 Internal Server Error` with `{"detail": "<message>"}`
5. Endpoints never return `null` for top-level fields — use `"unknown"` or omit the field
6. When adding a new endpoint, add it to this file in the same PR as the implementation
