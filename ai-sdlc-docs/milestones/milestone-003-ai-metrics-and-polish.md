---
id: milestone-003-ai-metrics-and-polish
title: "AI Pipeline Metrics & Reporting Polish"
target_date: 2027-03-31
prd_ref: docs/prd/prd-000-dashboard.md
status: planned
authors:
  - AI-generated
approvers:
  - ""
---

# Milestone: AI Pipeline Metrics & Reporting Polish

## Goal

Make all AI pipeline activity visible on the dashboard and ensure a PM can answer cross-role reporting questions in under 30 seconds.

## Features

- ai-pipeline-metrics-endpoint: GET /api/v1/ai-metrics?period={this_week|this_month} returning counts of plans generated, issues created by AI, AI PRs opened, AI PRs merged, and AI PRs rejected/closed.
- ai-pipeline-dashboard-ui: Dedicated dashboard panel with summary cards (plans generated, AI PRs merged vs. rejected) and a trend chart showing AI activity over the last 4 weeks.
- milestone-burndown-endpoint: GET /api/v1/milestones/{milestone_id}/burndown returning daily open/closed issue counts over the milestone's date range, suitable for a burn-down chart.
- burndown-chart-ui: Frontend burn-down chart component on the milestone detail view, using a lightweight charting library.
- traceability-search: Frontend search/filter on the hierarchy view that lets a Product Owner enter a PR number or merged PR URL and see the full trace back to the originating PRD requirement.

## Out of Scope for This Milestone

- Write operations from the dashboard (creating/editing issues)
- Jira or Linear integration
- Per-user OAuth authentication
- Separate database — GitHub remains the sole source of truth for this version
