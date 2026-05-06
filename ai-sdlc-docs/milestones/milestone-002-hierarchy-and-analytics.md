---
id: milestone-002-hierarchy-and-analytics
title: "Hierarchy View & Per-Person Analytics"
target_date: 2026-12-31
prd_ref: docs/prd/prd-000-dashboard.md
status: planned
authors:
  - AI-generated
approvers:
  - ""
---

# Milestone: Hierarchy View & Per-Person Analytics

## Goal

Enable a Product Owner to trace any PR back to its originating PRD requirement through a visual hierarchy, and give PMs per-person workload and activity breakdowns.

## Features

- hierarchy-data-engine: Backend logic that reconstructs the PRD → Milestone → Feature Plan → Task Issue hierarchy by parsing GitHub labels and issue/PR cross-references.
- hierarchy-view-endpoint: GET /api/v1/hierarchy returning a nested JSON tree (PRD → milestones → features → tasks) with status roll-ups at each level.
- hierarchy-tree-ui: Frontend collapsible tree component that renders the hierarchy, with color-coded status badges (open, in-progress, done, blocked) and click-through to GitHub URLs.
- per-person-activity-endpoint: GET /api/v1/activity?assignee={login}&period={this_week|this_month} returning issues closed, PRs merged, and reviews posted for a given person and time range.
- per-person-activity-ui: Frontend page/panel showing a filterable table of team members with activity sparklines and summary counts for the selected period.

## Out of Scope for This Milestone

- AI pipeline metrics (Phase 3)
- Cycle time / burn-down charts (Phase 3)
- Traceability search by PR number or URL (Phase 3)
- Database persistence
- Any write operations to GitHub
- Per-user OAuth authentication
