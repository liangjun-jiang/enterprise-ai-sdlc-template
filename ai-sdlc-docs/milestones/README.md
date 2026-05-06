# Milestones

One file per milestone. A milestone is a shippable slice of a PRD — a coherent set of features that can be released together.

Files are named `milestone-NNN-<slug>.md` (zero-padded, kebab-case).

## Format

```markdown
---
id: milestone-001-mvp
title: Short milestone title
target_date: YYYY-MM-DD
prd_ref: docs/prd/prd-000-example.md
status: planned | in-progress | complete
authors:
  - AI-generated
approvers:
  - ""
---

# Milestone: <Title>

## Goal
One sentence: what does this milestone deliver?

## Features
- feature-slug: one line description
- feature-slug: one line description

## Out of Scope for This Milestone
What is deferred to a later milestone?
```

## How the pipeline uses this

When a `milestone-*.md` file is merged to the `milestone` branch, `milestone-to-plans.yml` fires:
1. Reads the milestone file and the referenced PRD
2. Calls Claude Opus to generate one `PLAN-NNN-<slug>.md` per listed feature
3. Opens a PR to the `plan` branch with all generated plans (in suggested build order) for human review

If `prd_ref` is blank, Opus generates plans from the milestone content alone.

## Ad-hoc work

Not everything needs a milestone. If a Feature Plan is created directly (no milestone backing it),
set `milestone: ad-hoc` in the plan frontmatter. The pipeline runs normally.
