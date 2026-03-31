# A Typical Day with the AI-SDLC Pipeline

Everyone on the team interacts with the same GitHub repo, but at different layers. This guide shows what a typical day looks like for each role.

---

## Product Owner

Your primary artifact is the **Feature Plan** (`PLAN.md`). You define what gets built and why. The AI handles decomposition and implementation from there.

**Morning**
- Check the Project board for features in progress — are execution plans approved and tasks flowing to the board?
- Review any new `plan-execution` PRs opened overnight (AI-generated Execution Plans awaiting your approval)
- If an Execution Plan looks wrong (wrong scope, missing a requirement), comment and request changes — don't merge until it reflects your intent

**During the day**
- When you have a new feature to build, create `docs/plans/<feature-slug>/PLAN.md` on a new branch
- Include YAML frontmatter at the top (see format below) with your name as `author` and proposed `assignees`
- Open a PR to the `plan` branch — this is the human gate where scope is agreed before any AI work starts
- Work with the Project Manager to prioritize which issues on the board get labeled `ready-for-ai-coding`

**PLAN.md frontmatter format:**
```yaml
---
author: Jane Smith
approver: ""           # filled in by the person who merges the PR
feature: add-version-endpoint
priority: medium
assignees:
  planning: Jane Smith
  development: ""      # leave blank to let the PM assign
  review: Alex Chen
  qa: ""
---
```

**End of day**
- Are any features blocked waiting for your approval on an execution plan PR? Unblock them.
- Update `priority` in open Feature Plans if business needs have shifted

---

## Project Manager

Your job is **flow**. You keep tasks moving from the plan stage through to merged code, and you own the reporting view.

**Morning**
- Review the Project board — what's in progress, what's blocked, what's been idle more than a day?
- Check for issues with no assignee — assign them or confirm AI will handle them
- Check for `needs-human-review` labeled PRs — flag the right person to unblock them
- Review any overnight workflow failures (Actions tab) — failed runs post comments on the relevant issue/PR

**During the day**
- When an Execution Plan PR is opened, coordinate with the Tech Lead to review it
- Merge approved Execution Plans → issues are created automatically with assignees from the frontmatter
- Label tasks `ready-for-ai-coding` once they're unblocked and prioritized
- Track `assignees` in `PLAN.md` frontmatter — this is the source of truth for who owns each stage

**Reporting**
GitHub gives you the raw data: issue creation timestamps, PR open/merge times, assignees, label history, and commit authors. To aggregate this into a report:
- Use the GitHub API (`/repos/{owner}/{repo}/issues`, `/pulls`) filtered by label, assignee, or date range
- Each `PLAN.md` frontmatter has `author`, `approver`, and `assignees` — the scripts propagate these into issue metadata
- The full audit trail (who wrote the plan, who approved it, who wrote the code, who reviewed it) is in GitHub history

**End of day**
- Close any issues that were superseded or descoped during the day
- Confirm the Project board reflects reality — no ghost issues in "In Progress" for idle tasks

---

## Tech Lead / Architect

You own the **context layer** and the **quality gate**. You're the last human check before AI-generated code merges.

**Morning**
- Review any `ai-generated` PRs with the `ai-reviewed` label — the AI has already checked them, now it's your turn
- Focus on: does this match the architecture? Are there decisions the AI couldn't have known about?
- Check if `post-merge-housekeeping` updated any context docs overnight — review the commits to `dev` to make sure docs are accurate

**During the day**
- Review Execution Plan PRs on `plan-execution` — is the task breakdown sensible? Are `affected_files` correct? Are dependencies right?
- If a context doc is going stale (e.g., a new architectural pattern was introduced), update `docs/context/` directly and commit to `dev`
- If the AI is consistently making the same mistake, update `SYSTEM_PROMPT_CODER.md` or `CODING_STANDARDS.md` to correct it

**End of day**
- If the pipeline needs to pause (bad output, broken context docs), flip `circuit_breaker_active: true` in `AI_PIPELINE_CONFIG.json`
- Document the reason in a commit message so others know why it's paused

---

## Developer

You either implement tasks yourself or review what the AI built. Both happen on the same board.

**Morning**
- Check for `ai-generated` PRs assigned to your area — review and merge, or request changes
- Check your assigned issues — anything newly labeled `ready-for-ai-coding` you want to implement yourself? Remove the label and assign it to yourself
- Check CI on any open PRs — fix failures before picking up new work

**During the day**

*Letting the AI implement a task:*
1. Confirm the issue has a clear description and explicit `Affected files` section
2. Label it `ready-for-ai-coding` — the workflow fires automatically
3. Review the PR when it appears; check the AI review comment first
4. Approve and merge, or leave review comments

*Implementing a task yourself:*
1. Remove `ready-for-ai-coding` label, assign to yourself
2. Branch from `dev`: `git checkout -b feat/short-description`
3. Implement, open PR to `dev` — CI runs automatically
4. Get a human review and merge
5. `post-merge-housekeeping` updates context docs automatically

*Small bug fix (no issue needed):*
1. Branch from `dev`, fix, open PR
2. Reference the symptom in the PR body so there's a record

**End of day**
- Don't leave AI-generated PRs approved but unmerged — they go stale as `dev` moves forward
- If you found something wrong with the context docs while working, fix them in the same PR

---

## QA / Tester

You own **acceptance criteria**. You work upstream (shaping what good looks like) and downstream (verifying it was delivered).

**Morning**
- Review newly created issues — are the acceptance criteria testable and complete?
- If criteria are vague, comment on the issue to tighten them *before* it gets labeled `ready-for-ai-coding` — the AI codes to what's written
- Review any `ai-generated` PRs that passed AI review — do they actually satisfy the acceptance criteria?

**During the day**
- Work with the Product Owner during Feature Plan authoring to write acceptance criteria in the `PLAN.md`
- When reviewing AI-generated code PRs:
  - Run the tests locally if needed
  - Check that tests are present and meaningful, not just passing trivially
  - Request changes if test coverage is insufficient — don't approve on faith
- Label issues `ready-for-ai-coding` only after you're satisfied the criteria are clear enough to code against

**End of day**
- Flag any patterns of poor AI output to the Tech Lead — they'll update `SYSTEM_PROMPT_CODER.md`
- Close issues that were delivered and verified

---

## Customer Support

You are the **signal source** for bugs and pain points. Your job is to translate user problems into actionable GitHub Issues.

**When a user reports a problem**
1. Check if an issue already exists (search open issues before creating)
2. Create a GitHub Issue with:
   - What the user saw (exact behavior)
   - What they expected
   - Steps to reproduce if known
   - Environment (browser, version, etc.)
3. Label it `bug` — do **not** label it `ready-for-ai-coding` yet; let the Tech Lead or PM triage it first
4. If it's urgent, tag the PM or Tech Lead directly in the issue

**You don't need to diagnose the root cause** — that's for the developer or AI. Your job is to capture the symptom accurately so the issue is actionable.

**Reporting**
- Track recurring issue patterns — if the same type of bug keeps appearing, flag it to the Product Owner as a systemic problem worth a Feature Plan
- Use GitHub Issue labels and milestones to group related bugs for sprint reporting

---

## Quick reference by role

| Role | Primary artifact | Main GitHub action |
|------|-----------------|-------------------|
| Product Owner | `PLAN.md` | Open PRs to `plan` branch |
| Project Manager | Project board | Assign issues, manage labels |
| Tech Lead | `docs/context/` | Review execution plans + AI PRs |
| Developer | Code + PRs | Branch from `dev`, open PRs |
| QA / Tester | Acceptance criteria | Review issues + AI PRs |
| Customer Support | Bug reports | Create issues with `bug` label |
