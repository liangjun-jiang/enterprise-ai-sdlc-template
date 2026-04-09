# Current Tech Stack

## Version Pins (source of truth: `.mise.toml` and `backend/pyproject.toml`)

| Tool / Library | Pinned Version | Where |
|----------------|---------------|-------|
| Python | 3.12.2 | `.mise.toml` |
| Node | 20 | `.mise.toml` |
| uv | 0.5.4 | `.mise.toml` |
| FastAPI | ≥0.115.0 | `backend/pyproject.toml` |
| uvicorn | ≥0.32.0 (standard) | `backend/pyproject.toml` |
| pytest | ≥8.3.0 | `backend/pyproject.toml` |
| pytest-asyncio | ≥0.24.0 | `backend/pyproject.toml` |
| httpx | ≥0.27.0 | `backend/pyproject.toml` |
| ruff | 0.7.4 | `.mise.toml` tasks + `backend/pyproject.toml` |
| mypy | ≥1.13.0 | `backend/pyproject.toml` |
| React | ^18.3.1 | `frontend/package.json` |
| react-dom | ^18.3.1 | `frontend/package.json` |
| Vite | ^5.4.11 | `frontend/package.json` |
| TypeScript | ^5.6.3 | `frontend/package.json` |
| vitest | ^2.1.5 | `frontend/package.json` |
| @testing-library/react | ^16.1.0 | `frontend/package.json` |
| @testing-library/user-event | (latest) | `frontend/package.json` |
| eslint | ^9.15.0 | `frontend/package.json` |
| typescript-eslint | ^8.15.0 | `frontend/package.json` |
| Docker base (backend) | python:3.12-slim-bookworm | `backend/Dockerfile` |
| Docker base (frontend) | nginx:alpine | `frontend/Dockerfile` |
| pre-commit hooks | v5.0.0 | `.pre-commit-config.yaml` |
| ruff-pre-commit | v0.7.4 | `.pre-commit-config.yaml` |

## Package Managers

- **Python:** `uv` exclusively. Never use `pip install` directly.
  - Lock file: `backend/uv.lock` (committed, never hand-edited)
  - Install: `cd backend && uv sync --frozen`
  - Add dep: `cd backend && uv add <package>`
- **Node:** `npm` exclusively. Never use `yarn` or `pnpm`.
  - Lock file: `frontend/package-lock.json` (committed)
  - Install: `cd frontend && npm ci` (CI) or `npm install` (local)
  - Add dep: `cd frontend && npm install <package>`

## Version Management

`mise` manages Python and Node versions. Run `mise install` from repo root before anything else.

## Build Tools

- **Backend:** `hatchling` (build backend, defined in `pyproject.toml`)
- **Frontend:** `vite build` (outputs to `frontend/dist/`)
- **Type check frontend:** `tsc --noEmit` (run before `vite build` in `npm run build`)

## Styling

The frontend uses hand-rolled **Material Design 3** CSS:
- MD3 color tokens defined as CSS custom properties (`--md-sys-color-*`, `--md-sys-elevation-*`, `--md-sys-shape-*`) in `App.css`
- **Roboto** font loaded from Google Fonts via `<link>` tags in `index.html`
- No CSS framework, no component library (no Tailwind, no MUI)

## What Is NOT in This Stack

- No database (no SQLAlchemy, no Alembic, no Postgres)
- No Redis / caching layer
- No authentication (no JWT, no OAuth)
- No state management library (no Redux, no Zustand)
- No CSS framework or component library (no Tailwind, no MUI — styling is hand-rolled MD3 CSS)

When adding any of the above, update this file first.
