# A Typical Day with the AI-SDLC Pipeline

This guide walks through what a normal working day looks like for a developer on a team using this pipeline.

---

## Morning: Review what the AI did overnight

AI workflows often run unattended. Start the day by checking:

1. **Open PRs on `dev`** — any `ai-generated` PRs waiting for your review?
   - Check the AI review comment first (`ai-reviewed` label means it's been reviewed automatically)
   - If labeled `needs-human-review`, the AI flagged issues — read its comments before looking at the diff
   - Approve and merge, or request changes and re-label the issue `ready-for-ai-coding`

2. **GitHub Issues board** — any new issues created from an execution plan?
   - Newly created issues come pre-labeled `ready-for-ai-coding`
   - If you want AI to implement it, leave the label — the workflow fires automatically
   - If you want to implement it yourself, remove the label and assign it to yourself

3. **Failed workflow runs** — check Actions for any red runs
   - Failed runs post a comment on the relevant PR or issue with a link to the log
   - Common cause: context docs are stale, or the circuit breaker was accidentally left on

---

## Mid-morning: Decide what to work on

### If you're continuing an ongoing feature

- Check the Project board for your in-flight issues
- If an AI PR is open for your task, review it now
- If the AI PR needs changes, leave review comments and close the PR — re-labeling the issue will trigger a fresh attempt

### If you're starting something new

**Small change (bug fix, config, minor tweak):**
1. Branch from `dev`: `git checkout -b fix/short-description`
2. Make the change
3. Open a PR to `dev`
4. CI runs automatically (`ci.yml`) — fix any failures
5. Get a human review and merge

**Non-trivial feature:**
1. Write a Feature Plan: create `docs/plans/<feature-slug>/PLAN.md` on a new branch
2. Open a PR to the `plan` branch
3. Get it reviewed by a teammate (this is the human gate for scope/approach)
4. Merge → `plan-to-execution.yml` fires → an Execution Plan PR appears on `plan-execution`
5. Review the Execution Plan (check task breakdown, dependencies, affected files)
6. Merge → issues are created automatically on the Project board

---

## Afternoon: Implementation

### Letting the AI implement a task

1. Find the issue on the board
2. Confirm it has a clear description and explicit affected files listed
3. It should already be labeled `ready-for-ai-coding` — if not, add the label
4. `ai-code-writer.yml` fires within seconds
5. A PR appears on `dev` — review it when you get the AI review comment

### Implementing a task yourself

1. Unassign the `ready-for-ai-coding` label, assign the issue to yourself
2. Branch from `dev`, implement, open PR
3. CI runs; `ai-code-review.yml` skips it (no `ai-generated` label)
4. Get a human review and merge
5. `post-merge-housekeeping.yml` runs automatically to update context docs

---

## End of day: Housekeeping

- **Merge any approved PRs** — don't let them sit; stale AI-generated PRs go out of date as `dev` moves forward
- **Close stale issues** — if a task was superseded or descoped, close the issue so the board stays clean
- **Update context docs if needed** — if you made a significant architectural decision that `post-merge-housekeeping` wouldn't capture (e.g., a decision not to implement something), update the relevant `docs/context/` file manually and commit directly to `dev`
- **Check the circuit breaker** — if you paused the pipeline, make sure you've re-enabled it: set `circuit_breaker_active: false` in `docs/context/AI_PIPELINE_CONFIG.json`

---

## Quick reference

| I want to... | Do this |
|-------------|---------|
| Fix a small bug | Branch from `dev`, PR directly |
| Build a new feature | Write `PLAN.md`, PR to `plan` branch |
| Have AI implement a task | Label issue `ready-for-ai-coding` |
| Implement a task myself | Remove `ready-for-ai-coding`, assign to self |
| Stop the AI pipeline | Set `circuit_breaker_active: true` in `AI_PIPELINE_CONFIG.json` |
| Resume the AI pipeline | Set `circuit_breaker_active: false` |
| Update context docs manually | Edit files in `docs/context/`, commit to `dev` |
