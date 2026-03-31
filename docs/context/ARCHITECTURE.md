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

### Frontend (`frontend/`)
- **Runtime:** Node 20, React 18, Vite 5
- **Entry point:** `src/main.tsx` → `<App />`
- **Dev port:** 3000 (Vite dev server proxies `/health` and `/api` → `localhost:8000`)
- **Production:** Built to `dist/`, served by nginx on port 80
- **Communicates with backend** via relative paths (`/health`, `/api/...`) — never hardcoded base URLs

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
