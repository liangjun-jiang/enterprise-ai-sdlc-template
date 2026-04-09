# Architecture

## Overview

Monorepo with two independently deployable services: a React SPA frontend and a FastAPI Python backend. No shared code between them — they communicate exclusively over HTTP.

```
enterprise-ai-sdlc-template/
├── frontend/       # React 18 + Vite 5 SPA
├── backend/        # FastAPI 0.115 Python service
├── docs/           # Context docs, plans, schemas
├── .claude/        # AI pipeline scripts
└── .github/        # CI + AI workflow definitions
```

## Services

### Backend (`backend/`)
- **Runtime:** Python 3.12, FastAPI, uvicorn
- **Entry point:** `app/main.py` → `app` (FastAPI instance)
- **Port:** 8000 (local), 8000 (Docker)
- **Endpoints:** All under `/` or `/api/v1/` prefix
- **No database.** All state is in-memory or read from env vars.
- **Startup validation:** `validate_github_env()` is called at import time — the application refuses to start if `GITHUB_TOKEN` or `GITHUB_REPO` are missing (unless `SKIP_ENV_VALIDATION=1` is set).

### Frontend (`frontend/`)
- **Runtime:** Node 20, React 18, Vite 5
- **Entry point:** `src/main.tsx` → `<App />`
- **Dev port:** 3000 (Vite dev server proxies `/health` and `/api` → `localhost:8000`)
- **Production:** Built to `dist/`, served by nginx on port 80
- **Communicates with backend** via relative paths (`/health`, `/api/...`) — never hardcoded base URLs
- **UI:** Metrics dashboard (title: "AI Pipeline Dashboard") displaying AI pipeline activity; period selector (`this_week` / `this_month`) rendered as a `<select>` dropdown; loading, error, and success states
- **Styling:** Hand-rolled Material Design 3 CSS using MD3 color tokens and Roboto font (via Google Fonts); no CSS framework or component library

## Docker Topology

```
docker-compose.yml
├── backend   (python:3.12-slim) → port 8000
└── frontend  (nginx:alpine)     → port 3000→80
              nginx proxies /health and /api/ → http://backend:8000
```

Both images use multi-stage builds. The backend image copies only the `.venv` and `app/` directory — no build tools in the runtime layer. The frontend image copies only the `dist/` directory into nginx.

Both services run as non-root users.

## Communication Pattern

- Frontend calls backend using **relative URLs** (`/health`, `/api/v1/...`)
- In dev: Vite proxy forwards these to `localhost:8000`
- In production (Docker): nginx proxy forwards to `http://backend:8000`
- No CORS configuration needed — same-origin from the browser's perspective

## Backend Module Structure

```
backend/app/
├── __init__.py
├── main.py               # FastAPI app instance + route registration + startup validation
├── routers/
│   └── ai_metrics.py     # GET /api/v1/ai-metrics
├── models/
│   └── ai_metrics.py     # AiMetricsResponse, compute_period_range, validate_github_env
└── services/
    └── github_metrics.py # GitHub Search API client
```

## Frontend Module Structure

```
frontend/src/
├── main.tsx          # React entry point
├── App.tsx           # Root component: period selector, fetch logic, metrics display
├── App.test.tsx      # Full test coverage for all UI states
├── App.css           # Material Design 3 styles (hand-rolled CSS, no framework)
└── setupTests.ts     # @testing-library/jest-dom import
```

## AI Pipeline Topology

```
docs/plans/          → plan-to-execution.yml  → docs/execution-plans/
docs/execution-plans/ → execution-to-issues.yml → GitHub Issues
GitHub Issues         → ai-code-writer.yml     → PRs on dev
PRs on dev            → ai-code-review.yml     → AI review posted
Merged PRs            → post-merge-housekeeping.yml → context docs updated
```

Scripts live in `.claude/scripts/`. Each script is independently runnable locally.

## Anti-patterns

- **Never** hardcode `http://localhost:8000` in frontend source
- **Never** import from `../frontend` in backend or vice versa
- **Never** add a database without updating `DATA_MODELS.md` first
- **Never** add a new endpoint without updating `API_CONTRACTS.md`
