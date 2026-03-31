# enterprise-ai-sdlc-template

A reference implementation of a GitHub-centric AI-assisted SDLC. React frontend, FastAPI backend, and a fully automated pipeline from PRD → Milestone → Feature Plans → Execution Plans → GitHub Issues → Code PRs — all via Claude and GitHub Actions.

> **This is a template.** Clone it, fill in `docs/prd/` with your own product requirements, and the pipeline takes over from there.

---

## Stack

- **Frontend:** React 18 + TypeScript + Vite
- **Backend:** Python 3.12 + FastAPI
- **AI pipeline:** Claude API (Opus + Sonnet) via GitHub Actions
- **Tooling:** mise (version management), uv (Python packages), pre-commit

---

## 1. Prerequisites

- [mise](https://mise.jdx.dev/) — manages Python and Node versions
- Docker + Docker Compose — for local end-to-end runs
- A GitHub repo with Actions enabled

---

## 2. Local setup

```bash
mise install
cd backend && uv sync && cd ..
cd frontend && npm install && cd ..
```

Run locally:

```bash
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000

---

## 3. GitHub repo configuration

### 3a. Secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Required | Description |
|--------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key, or your LiteLLM gateway key |
| `ANTHROPIC_BASE_URL` | No | LiteLLM gateway URL — omit to call Anthropic directly |

`GITHUB_TOKEN` is provided automatically by GitHub Actions — no setup needed.

### 3b. Branches

Push to `main` once — `init-branches.yml` automatically creates all required branches:

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready code |
| `dev` | Integration branch — all code PRs target this |
| `plan` | Accepts Feature Plan PRs, triggers execution plan generation |
| `plan-execution` | Holds AI-generated Execution Plan PRs for human review |
| `roadmap` | Accepts milestone files, triggers Feature Plan generation |

### 3c. Branch protection rules

Configure in **Settings → Branches → Add rule** for each branch:

**`main`**
- Require a pull request before merging
- Require status checks to pass: `Backend`, `Frontend` (from `ci.yml`)
- Require at least 1 approving review
- Do not allow bypassing the above settings

**`dev`**
- Require a pull request before merging
- Require status checks to pass: `Backend`, `Frontend`
- Allow AI-generated PRs to be approved by 1 reviewer (no self-merge)

**`plan`, `plan-execution`, `roadmap`**
- Require a pull request before merging
- Require at least 1 approving review
- No status checks required (these branches hold docs, not code)

### 3d. Workflow permissions

Go to **Settings → Actions → General → Workflow permissions** and set:

- **Read and write permissions** ✓
- **Allow GitHub Actions to create and approve pull requests** ✓

These are required for the AI pipeline workflows to create branches, open PRs, and post reviews.

### 3e. GitHub Project (optional but recommended)

Create a Project board to visualize work across all roles:

1. Go to **Projects → New project → Board**
2. Add columns: `Backlog`, `Ready`, `In Progress`, `In Review`, `Done`
3. Add custom fields:
   - `Milestone` (text) — links to `docs/roadmap/` file
   - `PRD Ref` (text) — links to `docs/prd/` file
   - `Role` (single select): Product, Engineering, QA, Support
4. Link the project to your repository
5. Issues created by `parse_plan_to_issues.py` appear automatically once linked

---

## 4. First end-to-end run

Use the included `feature-000-example` to verify the full pipeline works before writing your own plans.

**Step 1 — Verify CI passes**
```bash
cd backend && uv run pytest       # should pass
cd frontend && npm run test       # should pass
```

**Step 2 — Push to main, confirm branches are created**
```bash
git push origin main
# Wait ~30s, then check: Settings → Branches
# dev, plan, plan-execution, roadmap should all exist
```

**Step 3 — Trigger execution plan generation**
```bash
git checkout plan
git checkout -b feat/feature-000-example
# docs/plans/feature-000-example/PLAN.md already exists in the repo
git push origin feat/feature-000-example
```
Open a PR from `feat/feature-000-example` → `plan` and merge it.

`plan-to-execution.yml` fires → an Execution Plan PR appears targeting `plan-execution`.

**Step 4 — Review and merge the Execution Plan**

Open the PR on `plan-execution`, review `docs/execution-plans/feature-000-example/EXECUTION_PLAN.md`, and merge.

`execution-to-issues.yml` fires → 3 GitHub Issues are created (TASK-001, TASK-002, TASK-003).

**Step 5 — Trigger AI code generation**

On TASK-001, add the label `ready-for-ai-coding`.

`ai-code-writer.yml` fires → a code PR opens targeting `dev`.

**Step 6 — Review the AI PR**

`ai-code-review.yml` fires automatically → an AI review is posted on the PR.

Read the review, check the diff, approve and merge.

`post-merge-housekeeping.yml` fires → TASK-001 is closed, context docs updated.

Repeat Steps 5–6 for TASK-002 and TASK-003.

---

## 5. Customising for your project

1. Replace `docs/prd/prd-000-dashboard.md` with your own PRD
2. Update `docs/context/ARCHITECTURE.md` to describe your actual architecture
3. Update `docs/context/CURRENT_TECH_STACK.md` if you change the stack
4. Update `docs/context/API_CONTRACTS.md` as you add endpoints
5. Leave `docs/context/SYSTEM_PROMPT_PLANNER.md` and `SYSTEM_PROMPT_CODER.md` as-is until you find the AI making consistent mistakes — then tune them

---

## 6. Docs

| File | Purpose |
|------|---------|
| [`guide/TYPICAL_DAY.md`](guide/TYPICAL_DAY.md) | What each role does day-to-day |
| [`guide/FAQ.md`](guide/FAQ.md) | Common questions |
| [`guide/TOKEN_COST_CONSCIOUSNESS.md`](guide/TOKEN_COST_CONSCIOUSNESS.md) | How context size is managed |
| [`docs/context/`](docs/context/) | AI context layer — architecture, standards, prompts |
| [`docs/prd/`](docs/prd/) | Product Requirements Documents |
| [`docs/roadmap/`](docs/roadmap/) | Milestones |
| [`docs/plans/`](docs/plans/) | Feature Plans |
| [`docs/execution-plans/`](docs/execution-plans/) | AI-generated task breakdowns |
