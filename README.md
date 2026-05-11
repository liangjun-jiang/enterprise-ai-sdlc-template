# enterprise-ai-sdlc-template

This repository demonstrates a **GitHub-centric AI SDLC** where GitHub Issues are the single source of truth for review, planning, and coding automation.

The primary goal is the workflow itself (Issue -> Review -> Labels -> Code -> PR -> Merge), not the sample app.

---

## What This Repo Showcases

- Label-driven GitHub issue lifecycle
- Reviewer comment gate before implementation planning
- AI-generated implementation plans written back to issue threads
- AI code generation gated by label readiness
- Deterministic feature branch + PR creation
- Post-merge context freshness maintenance

---

## Workflow at a Glance

1. Create or refine a GitHub Issue
2. Add reviewer feedback as an issue comment
3. Add label `ready-for-implementation-plan`
4. `ai-implementation-planner.yml` generates/updates an implementation plan comment
5. Add label `implementation-plan-ready-for-review` for plan review
6. Add label `ready-for-ai-coding`
7. `ai-code-writer.yml` creates a feature branch, writes code, pushes branch, and opens/updates a PR to `dev`
8. Merge PR to `dev`
9. `post-merge-housekeeping.yml` refreshes context metadata

See label contract: [`/.github/ISSUE_LABEL_LIFECYCLE.md`](.github/ISSUE_LABEL_LIFECYCLE.md)

---

## Required Labels

These labels are used by the workflow:

- `ready-for-implementation-plan`
- `implementation-plan-ready-for-review`
- `ready-for-ai-coding`

### Not part of this workflow anymore

- PRD documents
- Milestones
- Separate standalone planning artifacts outside the issue thread

`init-branches.yml` bootstraps them, and also ensures `main` / `dev` branches exist.

---

## Key Workflows

- [`/.github/workflows/ai-implementation-planner.yml`](.github/workflows/ai-implementation-planner.yml)
  - Trigger: issue labeled `ready-for-implementation-plan` (or `/replan` comment)
  - Reads issue thread
  - Writes/upserts implementation plan comment

- [`/.github/workflows/ai-code-writer.yml`](.github/workflows/ai-code-writer.yml)
  - Trigger: issue labeled `ready-for-ai-coding`
  - Verifies issue state and labels
  - Generates code -> feature branch -> push -> PR -> issue status comment

- [`/.github/workflows/post-merge-housekeeping.yml`](.github/workflows/post-merge-housekeeping.yml)
  - Trigger: PR merged into `dev`
  - Updates context docs/marker (`CONTEXT_STATUS.json`)

---

## Minimal Context Layer

Current high-signal context files:

- [`ai-sdlc-docs/context/SYSTEM_PROMPT_CODER.md`](ai-sdlc-docs/context/SYSTEM_PROMPT_CODER.md)
- [`ai-sdlc-docs/context/CODING_STANDARDS.md`](ai-sdlc-docs/context/CODING_STANDARDS.md)
- [`ai-sdlc-docs/context/SECURITY_CHECKLIST.md`](ai-sdlc-docs/context/SECURITY_CHECKLIST.md)
- [`ai-sdlc-docs/context/AI_PIPELINE_CONFIG.json`](ai-sdlc-docs/context/AI_PIPELINE_CONFIG.json)
- `ai-sdlc-docs/context/CONTEXT_STATUS.json` (generated/maintained by workflows)

---

## GitHub Setup

### 1) Actions secrets

Add in **Settings -> Secrets and variables -> Actions**:

- `LLM_PROVIDER` (`direct`, `gateway`, or `bedrock`)
- `LLM_API_KEY` (required for `direct`/`gateway`, or Bedrock API-key mode)
- `LLM_BASE_URL` (if using gateway)
- AWS credentials/region vars (if using Bedrock IAM mode)

`GITHUB_TOKEN` is provided automatically by GitHub Actions.

### 2) Repository Actions permissions

In **Settings -> Actions -> General**:

- Workflow permissions: **Read and write permissions**
- Enable: **Allow GitHub Actions to create and approve pull requests**

### 3) Branch protection (recommended)

- `main`: require PR + required checks
- `dev`: require PR + required checks

---

## Local Simulation (Before Running Actions)

Use local scripts to validate Issue -> Review comment -> Implementation plan -> AI code generation behavior first.

### Example issue input

- [`local-inputs/issue-example.md`](local-inputs/issue-example.md)

### Run local simulation

```bash
uv run --project .claude/scripts python .claude/scripts/simulate_pipeline.py \
  --issue-file local-inputs/issue-example.md
```

Artifacts are written to `.simulate-output/run-<timestamp>/`:

- `01_issue.md`
- `02_implementation_plan.md`
- `03_codegen.json`
- `04_review.json`

---

## Example App (Optional)

The app is included only as a demo target for the SDLC workflow.

### Stack

- Frontend: React + TypeScript + Vite
- Backend: FastAPI + Python 3.12

### Run locally

```bash
mise install
cd backend && uv sync && cd ..
cd frontend && npm install && cd ..
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
