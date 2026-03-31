# FAQ

## Code Changes

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
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key, or your LiteLLM gateway key |
| `ANTHROPIC_BASE_URL` | No | Only needed if using a LiteLLM gateway instead of direct Anthropic |
| `GITHUB_TOKEN` | Auto | Provided by GitHub Actions automatically — no manual setup needed |

---

### The workflow says "circuit breaker is active" but I didn't set it

Check `docs/context/AI_PIPELINE_CONFIG.json` in the `plan-execution` or `plan` branch (not just `main` — each branch has its own copy of the file at that point in history).

---

### Can I use a different LLM provider?

Yes, via LiteLLM. Set `ANTHROPIC_BASE_URL` to your LiteLLM gateway URL and configure LiteLLM to route `claude-opus-4-6` and `claude-sonnet-4-6` to your chosen provider. Model names in `AI_PIPELINE_CONFIG.json` stay the same.

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
