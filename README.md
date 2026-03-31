# enterprise-ai-sdlc-template

A reference implementation of an AI-assisted software development pipeline. React frontend, FastAPI backend, fully automated from feature plan to code PR.

## Stack

- **Frontend:** React 18 + TypeScript + Vite
- **Backend:** Python 3.12 + FastAPI
- **AI pipeline:** Claude API (Opus + Sonnet) via GitHub Actions

## Prerequisites

- [mise](https://mise.jdx.dev/) for Python and Node version management
- Docker + Docker Compose

## Setup

```bash
mise install
cd backend && uv sync && cd ..
cd frontend && npm install && cd ..
```

## Run locally

```bash
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000

## Required secrets (GitHub repo settings)

| Secret | Description |
|--------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key, or your LiteLLM gateway key |
| `ANTHROPIC_BASE_URL` | *(Optional)* LiteLLM gateway URL — omit to use Anthropic directly |

`GITHUB_TOKEN` is provided automatically by GitHub Actions — no manual setup needed.

## Branch setup

Required branches (`dev`, `plan`, `plan-execution`, `roadmap`) are created automatically on first push to `main` by `init-branches.yml`. No manual branch creation needed.

## Docs

- [`guide/TYPICAL_DAY.md`](guide/TYPICAL_DAY.md) — how to use the pipeline day-to-day
- [`guide/FAQ.md`](guide/FAQ.md) — common questions
- [`docs/context/`](docs/context/) — AI context layer (architecture, standards, prompts)
