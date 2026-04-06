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

## Implemented Endpoints

### `GET /api/v1/ai-metrics`

Returns AI pipeline activity metrics for a given time period. Queries the GitHub Search API using the `GITHUB_TOKEN` and `GITHUB_REPO` environment variables.

**Required environment variables (validated at startup):**
| Variable | Format | Description |
|----------|--------|-------------|
| `GITHUB_TOKEN` | string | GitHub personal access token with `repo` scope |
| `GITHUB_REPO` | `owner/repo` | Target GitHub repository (e.g. `acme/my-repo`) |

**Query parameters:**
| Parameter | Type | Required | Values | Description |
|-----------|------|----------|--------|-------------|
| `period` | `string` | Yes | `this_week`, `this_month` | Time window for metrics |

**Response `200 OK`:**
```json
{
  "period": "this_week",
  "period_start": "2024-01-15",
  "period_end": "2024-01-21",
  "plans_generated": 5,
  "issues_created_by_ai": 12,
  "ai_prs_opened": 8,
  "ai_prs_merged": 6,
  "ai_prs_rejected_closed": 2
}
```

**Response schema (`AiMetricsResponse`):**
| Field | Type | Description |
|-------|------|-------------|
| `period` | `string` | Echoed query parameter |
| `period_start` | `string` (ISO-8601 date) | Start of the period (Monday for `this_week`, 1st for `this_month`) |
| `period_end` | `string` (ISO-8601 date) | Today's date (UTC) |
| `plans_generated` | `integer` | Issues with labels `ai-generated` and `ai-plan` |
| `issues_created_by_ai` | `integer` | Issues with label `ai-generated` |
| `ai_prs_opened` | `integer` | Pull requests with label `ai-generated` |
| `ai_prs_merged` | `integer` | Subset of `ai_prs_opened` that are merged |
| `ai_prs_rejected_closed` | `integer` | Subset of `ai_prs_opened` that are closed but not merged |

**Error responses:**
- `422 Unprocessable Entity` — `period` query parameter is missing or not a recognised value
- `502 Bad Gateway` — GitHub API returned a non-2xx status or was unreachable; detail is always `"GitHub API error: <status>"` — raw GitHub response bodies are never forwarded

---

## Contract Rules

1. All responses are JSON (`Content-Type: application/json`)
2. All success responses use `2xx` status codes
3. Validation errors return `422 Unprocessable Entity` (FastAPI default)
4. Unexpected errors return `500 Internal Server Error` with `{"detail": "<message>"}`
5. GitHub API errors return `502 Bad Gateway` with a sanitised message — raw upstream error bodies are never forwarded
6. Endpoints never return `null` for top-level fields — use `"unknown"` or omit the field
7. When adding a new endpoint, add it to this file in the same PR as the implementation
