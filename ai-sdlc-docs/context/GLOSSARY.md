# Glossary

Terms specific to this project's AI-assisted SDLC pipeline.

---

## Pipeline Concepts

**Feature Plan**
A Markdown document describing a feature to be built. AI-generated from a milestone file, or human-authored for ad-hoc work. Lives in `docs/plans/PLAN-NNN-<slug>.md`. The number reflects suggested build order.

**Execution Plan (`EXECUTION_PLAN.md`)**
An AI-generated Markdown document (produced by `generate_execution_plan.py` using Claude Opus) that breaks a Feature Plan into an ordered list of tasks. Each task has: title, description, acceptance criteria, affected files, and dependencies. Validated against `docs/schemas/execution-plan-schema.yaml`.

**Task Issue**
A GitHub Issue created by `parse_plan_to_issues.py` from a single task in an Execution Plan. The issue body contains the full task description, acceptance criteria, and affected files. Linked to a GitHub Project board.

**Human Gate**
A mandatory human approval step in the pipeline. There are two:
1. Review and merge the Execution Plan PR (on `plan-execution` branch)
2. Review and merge each AI-generated code PR (on `dev` branch)

The pipeline cannot proceed past a human gate without explicit human action.

**Circuit Breaker**
A flag in `AI_PIPELINE_CONFIG.json` (`circuit_breaker_active: true`) that halts all AI workflows immediately. Used when the pipeline is producing bad output and needs to be paused without modifying workflow YAML files.

**Context Docs**
The files in `docs/context/` that are injected into every Claude API call as system context. They describe architecture, standards, and contracts so the AI has full project awareness without reading source code.

**AI Pipeline Config (`AI_PIPELINE_CONFIG.json`)**
A JSON file controlling pipeline behavior: model names, concurrency limits, retry settings, and the circuit breaker flag. Read by all `.claude/scripts/` at startup.

---

## Branch Names

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready code. Protected. |
| `dev` | Integration branch. All AI-generated PRs target `dev`. |
| `plan-execution` | Holds AI-generated Execution Plan PRs for human review. |
| `plan` | Accepts merged Feature Plan PRs, triggering `plan-to-execution.yml`. |

---

## Labels

| Label | Applied by | Meaning |
|-------|-----------|---------|
| `ai-generated` | `ai-code-writer.yml` | PR was opened by an AI script |
| `ready-for-ai-coding` | Human | Task issue is approved for AI to implement |
| `ai-reviewed` | `ai-code-review.yml` | AI has posted a review on this PR |
| `needs-human-review` | `ai-code-review.yml` when requesting changes | AI flagged issues; human must resolve |

---

## Scripts

| Script | Model | Trigger |
|--------|-------|---------|
| `generate_execution_plan.py` | claude-opus-4-6 | Workflow 1 |
| `parse_plan_to_issues.py` | claude-sonnet-4-6 | Workflow 2 |
| `write_code.py` | claude-sonnet-4-6 | Workflow 3 |
| `review_code.py` | claude-sonnet-4-6 | Workflow 4 |
| `update_context_docs.py` | claude-sonnet-4-6 | Workflow 5 |
