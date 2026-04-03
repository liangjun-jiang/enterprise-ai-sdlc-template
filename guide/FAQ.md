# FAQ

## Branches

### What is each branch for?

| Branch | Holds | PR merge triggers |
|--------|-------|-------------------|
| `prd` | PRDs | `prd-to-roadmap.yml` → PR to `roadmap` |
| `roadmap` | `ROADMAP.md` | `roadmap-to-milestones.yml` → PR to `milestone` |
| `milestone` | `milestone-*.md` files | `milestone-to-plans.yml` → PR to `plan` |
| `plan` | `PLAN-NNN-*.md` feature plans | `plan-to-execution.yml` → PR to `plan-execution` |
| `plan-execution` | `EXECUTION_PLAN.md` files | `execution-to-issues.yml` → GitHub Issues |
| `dev` | All code | `post-merge-housekeeping.yml` → context docs updated |
| `main` | Production-ready code | — |

See [`GIT_BRANCHES_FLOW.md`](./GIT_BRANCHES_FLOW.md) for the full flow diagram, branch naming convention, human gates, and local testing steps.

---

### How does code get to main?

The AI code writer opens PRs targeting `dev`. Once a human reviews, approves, and merges to `dev`, it goes through normal promotion:

```
feature branch → dev (AI + human review) → main (human approval)
```

`main` is production-only. Nothing merges to `main` automatically — a human PR from `dev` → `main` is always required.

---

### Why does the workflow only process the newly merged PRD, not all PRDs on the branch?

Each workflow uses `git diff HEAD~1 HEAD` to extract the single file changed in the merged PR.
Only that file is sent to the LLM.

**Why:** if a branch has 10 PRDs and you add an 11th, reprocessing all 10 would regenerate
plans and milestones that already exist — wasting tokens and creating duplicates.

The AI still knows about existing work: scripts run `git ls-files` on downstream branches
(roadmap, milestone, plan) to build a short deduplication list, so the LLM is told "these
files already exist — skip them."

**Result:** each merge is cheap and idempotent. Adding a 5th PRD costs the same tokens as
adding the 1st.

---

## Planning

### Do I have to follow the full PRD → Milestone → Plan → Execution Plan pipeline?

No. The pipeline is modular — enter at whatever stage makes sense:

| You have | Start here |
|----------|-----------|
| A PRD and want full structure | `prd_to_milestone.py` → full pipeline |
| A milestone file already written | `milestone_to_plans.py` → onwards |
| A feature idea, skip the formality | Write a `PLAN.md` directly → merge to `plan` branch |
| A well-scoped task, skip planning entirely | Write a GitHub Issue → add `ready-for-ai-coding` |

Most teams start somewhere in the middle. The earlier stages (PRD → milestone → plan) exist to keep larger projects structured, not as mandatory overhead for every change.

---

### What is the difference between a roadmap and a milestone?

- **Roadmap** — the big-picture timeline: what gets built, in what order, across quarters
- **Milestone** — a specific deliverable within the roadmap with a clear definition of done and a feature list

```
Roadmap
  └─► Milestone 1 (MVP)       ← one milestone file
        └─► Feature Plan A
        └─► Feature Plan B
  └─► Milestone 2 (Beta)
        └─► Feature Plan C
```

In practice these terms get used loosely. What matters is that a milestone is concrete enough to break into feature plans.

---


### Should I write an issue before making a code change?

It depends on the size of the change.

**No issue needed:**
- Bug fixes and hotfixes
- Small tweaks (config, copy, minor refactors) touching 1–2 files

**Issue recommended:**
- Any non-trivial feature or change
- Anything that will take more than an hour
- Anything affecting an API shape, data model, or architectural decision

The issue isn't bureaucracy — it's context for the AI reviewer. Without one, `review_code.py` can only check style and security. With one, it can verify the PR actually solves the right problem and meets the stated acceptance criteria.

**Practical rule of thumb:**

| Change type | Write issue first? | Use AI code writer? |
|-------------|-------------------|---------------------|
| Bug fix / hotfix | No | No |
| Small feature (1–2 files) | Optional | No |
| Non-trivial feature | Yes | Your call |
| Feature from an execution plan | Yes (auto-created) | Yes |

---

### Can a human bypass the AI pipeline entirely?

Yes. The AI pipeline is opt-in at every step. A human can:
- Branch from `dev`, write code, and open a PR directly
- The `ai-code-review.yml` workflow only runs on PRs labeled `ai-generated`, so human PRs won't get an automated review
- `post-merge-housekeeping.yml` runs on **all** merges to `dev` (human or AI) to keep context docs up to date

---

### What happens if AI-generated code is wrong?

The human gate catches it. Every AI-generated PR requires a human to review and approve before it can merge to `dev`. If the code is wrong:
1. Request changes on the PR
2. Close the PR and re-label the issue `ready-for-ai-coding` to trigger a fresh attempt, or fix it manually

---

### When should I use the AI code writer vs. just writing the code myself?

Use the AI code writer when:
- The task is well-specified (clear description, explicit affected files, testable acceptance criteria)
- The task is mechanical (add an endpoint, write a test, update a model)
- You'd rather review code than write it

Write it yourself when:
- The task requires architectural judgment the AI doesn't have context for
- You already know exactly what to write and reviewing AI output would take longer
- The change is exploratory and hard to specify upfront

---

### What is the circuit breaker for?

`circuit_breaker_active` in `docs/context/AI_PIPELINE_CONFIG.json` is an emergency stop. Set it to `true` to immediately halt all AI workflows without touching any workflow YAML files. Use it when:
- The AI is producing consistently bad output
- A prompt or context doc needs fixing before the next run
- You want to pause the pipeline during an incident

Set it back to `false` when ready to resume.

---

### What secrets do I need to configure?

| Secret | Required | Notes |
|--------|----------|-------|
| `LLM_API_KEY` | Yes | Your Anthropic API key, or your LiteLLM gateway key |
| `LLM_BASE_URL` | No | Only needed if using a LiteLLM gateway instead of direct Anthropic |
| `GITHUB_TOKEN` | Auto | Provided by GitHub Actions automatically — no manual setup needed |

---

### The workflow says "circuit breaker is active" but I didn't set it

Check `docs/context/AI_PIPELINE_CONFIG.json` in the `plan-execution` or `plan` branch (not just `main` — each branch has its own copy of the file at that point in history).

---

### Can I use a different LLM provider?

Yes, via LiteLLM. Set `LLM_BASE_URL` to your LiteLLM gateway URL and configure LiteLLM to route `claude-opus-4-6` and `claude-sonnet-4-6` to your chosen provider. Model names in `AI_PIPELINE_CONFIG.json` stay the same.

---

### Can I test the LLM scripts locally without GitHub Actions?

Yes. Three ways:

**1. Full end-to-end simulation** (recommended for first-time setup)

Walks the entire pipeline interactively — PRD → Roadmap → Milestones → Plans → Execution Plans → GitHub Issues. Pauses at each step for a named role to review and approve. Saves state so you can resume if interrupted.

```bash
# From repo root — requires .claude/scripts/.env with GITHUB_TOKEN + GITHUB_REPO
uv run --project .claude/scripts python .claude/scripts/simulate_pipeline.py

# Resume from a specific step (1=setup, 2=prd, 3=roadmap, ...)
uv run --project .claude/scripts python .claude/scripts/simulate_pipeline.py --from-step 5

# Reset saved state and start over
uv run --project .claude/scripts python .claude/scripts/simulate_pipeline.py --reset
```

Files generated are already on disk (reuses them without an LLM call). Only missing files trigger the LLM.

**2. Smoke test — verify LLM connectivity only**

Confirms your credentials and region are correct before running anything real:

```bash
cd .claude/scripts

# Direct Anthropic API
LLM_API_KEY=sk-... uv run python smoke_test.py

# AWS Bedrock
LLM_PROVIDER=bedrock AWS_DEFAULT_REGION=us-west-2 uv run python smoke_test.py
```

A successful run prints the model's one-sentence reply and `OK — LLM connectivity confirmed.`

**2. Dry-run — test the full code-writer prompt without touching GitHub**

Runs the real prompt pipeline (context loading → LLM call → JSON response) but skips branch creation and PR opening. Prints the raw LLM output so you can inspect it:

```bash
LLM_API_KEY=sk-... uv run python write_code.py \
  --dry-run \
  --context-dir ../../docs/context \
  --issue-title "Add /version endpoint" \
  --issue-body "Return app version. Affected files:\n- \`backend/app/main.py\` (modify)"
```

Swap in `LLM_PROVIDER=bedrock` instead of `LLM_API_KEY` for Bedrock.

The `--issue-title` / `--issue-body` defaults are a built-in sample task, so you can run `--dry-run --context-dir ../../docs/context` with no other flags and still get a meaningful response.

---

## Bugs

### I filed a bug issue. Will AI fix it automatically?

No — not until you explicitly add the `ready-for-ai-coding` label.

When you create an issue with the `bug` label, nothing triggers automatically. The flow is:

1. PM or Tech Lead triages the issue — is it clear and reproducible?
2. If yes, they either add `ready-for-ai-coding` (AI fixes it) or assign it to a developer (human fixes it)
3. Once labeled, `ai-code-writer.yml` fires and the fix goes through the normal PR → review → merge pipeline

The label is the explicit human sign-off that the bug is well-described enough for AI to act on. A vague bug report will produce a vague fix — make sure the issue includes reproduction steps and expected vs. actual behavior before labeling it.

### What makes a good bug report for AI?

The AI reads the issue body exactly as written. Include:

- **What happened** — the exact error message or unexpected behavior
- **Steps to reproduce** — numbered, specific
- **Expected behavior** — what should have happened
- **Affected files** — if you know them, list them; this helps the AI scope its fix correctly
- **Environment** — browser, OS, version if relevant

The more specific the issue, the better the fix.
