# GitHub Issue Label Lifecycle

This repository uses labels to move an issue from vague requirement to AI-generated pull request.

## States

1. `ready-for-implementation-plan`
   - Triggers `ai-implementation-planner`.
   - Workflow reads issue body + full comment thread.
   - Workflow posts an implementation plan comment marked with `<!-- ai-implementation-plan -->`.

2. `implementation-plan-ready-for-review`
   - Indicates plan is available for human review/feedback.
   - Maintainers can request revision with issue comments and re-run planner.

3. `ready-for-ai-coding`
   - Triggers `ai-code-writer`.
   - Workflow validates planner output and checklist before coding.
   - Workflow creates deterministic feature branch, writes code, and opens/updates PR.

## Replanning

- Add feedback on the issue, keep `ready-for-implementation-plan`, then comment `/replan`.
- Planner posts a new versioned plan comment and includes a markdown diff from the previous plan.

## Guardrails

- AI coding requires an approved implementation plan comment with a checked checklist.
- Context freshness is enforced via `ai-sdlc-docs/context/CONTEXT_STATUS.json`.
