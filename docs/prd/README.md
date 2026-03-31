# Product Requirements Documents

One file per product initiative. These are the source of truth for *what* is being built and *why*.

## Format

```markdown
---
id: prd-001
title: Short initiative title
status: draft | approved | active | complete
owner: Product Owner Name
---

# PRD: <Title>

## Problem Statement
What problem are we solving? Who has this problem?

## Target Users
Who will use this? Be specific.

## Success Metrics
How will we know it worked? Measurable outcomes.

## Requirements
What must be true when this is done?

## Out of Scope
What are we explicitly NOT building?
```

## Notes

- PRDs are **always human-authored**. They are never AI-generated.
- A PRD may span multiple milestones. One milestone references one PRD.
- If a Feature Plan is created ad-hoc (no PRD), leave `prd_ref` blank in the plan frontmatter — the pipeline will still work.
- When `generate_execution_plan.py` finds a `prd_ref` in a `PLAN.md`, it loads the referenced PRD as additional context for Opus.
