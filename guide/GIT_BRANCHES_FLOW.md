# Git Branch Flow

## Branch Purpose

Each branch has a single responsibility. Nothing lives on a branch that doesn't belong there.

| Branch | Owns | Who writes to it |
|--------|------|-----------------|
| `prd` | `docs/prd/prd-*.md` | Product Owner |
| `roadmap` | `docs/roadmap/ROADMAP.md` | AI (via `prd-to-roadmap.yml`) |
| `milestone` | `docs/milestones/milestone-*.md` | AI (via `roadmap-to-milestones.yml`) |
| `plan` | `docs/plans/PLAN-NNN-*.md` | AI (via `milestone-to-plans.yml`) |
| `plan-execution` | `docs/execution-plans/*/EXECUTION_PLAN.md` | AI (via `plan-to-execution.yml`) |
| `dev` | Application source code | AI code writer + humans |
| `main` | Production-ready code | Humans (promoted from `dev`) |

---

## Full Flow with Branch Naming

Each step follows the same pattern: a human or the AI opens a **feature branch**, opens a **PR to the target branch**, a human approves and merges it, and the next workflow fires automatically.

```
Product Owner
  creates branch: prod-01-proposal
  writes:         docs/prd/prd-001-dashboard.md
  opens PR to:    prd
  merges (PO):    prd branch updated
                  │
                  │ prd-to-roadmap.yml fires
                  │ (triggered by prd-*.md merged to prd)
                  ▼
AI creates branch: roadmap/prd-001-dashboard
  generates:       docs/roadmap/ROADMAP.md
  opens PR to:     roadmap
  merges (PM/TL):  roadmap branch updated
                   │
                   │ roadmap-to-milestones.yml fires
                   │ (triggered by ROADMAP.md merged to roadmap)
                   ▼
AI creates branch: milestones/ROADMAP
  generates:       docs/milestones/milestone-001-mvp.md
                   docs/milestones/milestone-002-beta.md
                   ...
  opens PR to:     milestone
  merges (PM):     milestone branch updated
                   │
                   │ milestone-to-plans.yml fires (once per milestone-*.md merged)
                   ▼
AI creates branch: plans/milestone-001-mvp
  generates:       docs/plans/PLAN-001-feature-auth.md
                   docs/plans/PLAN-002-feature-api.md
                   ...
  opens PR to:     plan
  merges (TL):     plan branch updated
                   │
                   │ plan-to-execution.yml fires
                   │ (triggered by PLAN.md merged to plan)
                   ▼
AI creates branch: execution/feature-001-auth
  generates:       docs/execution-plans/feature-001-auth/EXECUTION_PLAN.md
  opens PR to:     plan-execution
  merges (TL):     plan-execution branch updated
                   │
                   │ execution-to-issues.yml fires
                   ▼
GitHub Issues created: TASK-001, TASK-002, TASK-003
TL/PM labels:          ready-for-ai-coding on the desired task
                       │
                       │ ai-code-writer.yml fires
                       ▼
AI creates branch: feat/feature-001-auth-task-001
  writes code,     opens PR to dev
  ai-code-review.yml posts automated review
  merges (engineer): dev branch updated
                     │
                     │ post-merge-housekeeping.yml fires
                     │ (context docs updated, issue closed)
                     ▼
dev accumulates merged features
Human opens PR:    dev → main (when ready to release)
merges (TL):       main (production)
```

---

## Human Gates

Every transition requires a human to approve and merge a PR. The AI never merges its own output.

| Gate | Branch name → target | Who approves |
|------|----------------------|-------------|
| PRD proposal → prd | `prod-NN-proposal` → `prd` | Product Owner |
| Roadmap → roadmap | `roadmap/prd-NNN-...` → `roadmap` | Project Manager / Tech Lead |
| Milestones → milestone | `milestones/ROADMAP` → `milestone` | Project Manager |
| Plans → plan | `plans/milestone-NNN` → `plan` | Tech Lead |
| Execution plan → plan-execution | `execution/feature-NNN` → `plan-execution` | Tech Lead |
| Issue label trigger | `ready-for-ai-coding` label added | Tech Lead / PM |
| Code PR → dev | `feat/...` → `dev` | Any engineer |
| dev → main | `dev` → `main` | Tech Lead / release manager |

---

## Why Only the New File Is Picked Up

Each workflow uses `git diff HEAD~1 HEAD` to find the file that changed in the merged PR.
Only that single file is passed to the LLM — not the entire branch history.

This means:
- Merging `prd-001-dashboard.md` triggers roadmap generation for that PRD only
- When a second PRD (`prd-002-onboarding.md`) is merged later, only that file is processed
- Existing milestones, roadmap, and plans are passed as a short deduplication list via `git ls-files`
  so the AI knows what already exists and skips regenerating it

**Token savings:** loading one 2–5 KB PRD instead of the full branch history keeps API costs
predictable and responses focused as the repo grows.

---

## Deduplication via Git

When the AI generates plans or milestones, it runs `git ls-files` on the relevant branch
to detect what already exists. This prevents duplicate plans when a second PRD is added.
Only committed (merged) files count — untracked local files are invisible to the check.

---

## Local Testing

To mirror this flow locally without GitHub Actions:

```bash
# One-time branch setup
git checkout -b prd && git checkout main
git checkout -b roadmap && git checkout main
git checkout -b milestone && git checkout main
git checkout -b plan && git checkout main
git checkout -b plan-execution && git checkout main
git checkout -b dev && git checkout main

# Run scripts manually instead of relying on GHA triggers
cd .claude/scripts

# Step 1 — write PRD on prd branch, then generate roadmap
git checkout prd
# ... write docs/prd/prd-001-dashboard.md ...
git add ../../docs/prd/prd-001-dashboard.md && git commit -m "feat: add prd-001"
uv run python prd_to_roadmap.py --local \
  --prd-file ../../docs/prd/prd-001-dashboard.md \
  --context-dir ../../docs/context

# Step 2 — commit ROADMAP.md to roadmap branch, then generate milestones
git checkout roadmap
git add ../../docs/roadmap/ROADMAP.md && git commit -m "feat: roadmap"
uv run python roadmap_to_milestones.py --local \
  --roadmap-file ../../docs/roadmap/ROADMAP.md \
  --context-dir ../../docs/context

# Step 3 — commit milestone files to milestone branch, then generate plans
git checkout milestone
git add ../../docs/milestones/milestone-*.md && git commit -m "feat: milestones"
uv run python milestone_to_plans.py --local \
  --milestone-file ../../docs/milestones/milestone-001-mvp.md \
  --context-dir ../../docs/context
# ... and so on
```
