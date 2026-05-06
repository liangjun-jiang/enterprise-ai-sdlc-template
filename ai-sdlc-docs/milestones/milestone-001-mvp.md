---
id: milestone-001-mvp
title: "MVP — GitHub Data Foundation & Basic Dashboard"
target_date: 2026-09-30
prd_ref: docs/prd/prd-000-dashboard.md
status: planned
authors:
  - AI-generated
approvers:
  - ""
---

# Milestone: MVP — GitHub Data Foundation & Basic Dashboard

## Goal

Let a PM see milestone completion percentage and let a developer see their assigned issues and PR status from a single page, without opening GitHub.

## Features

- github-api-client: Backend service layer using httpx.AsyncClient to authenticate with GitHub API (via GITHUB_TOKEN env var) and fetch issues, PRs, milestones, labels, and assignees for a configured repository, including rate-limit handling and error mapping.
- milestone-summary-endpoint: GET /api/v1/milestones and GET /api/v1/milestones/{milestone_id}/summary returning open/closed issue counts and completion percentage per milestone.
- issues-prs-list-endpoint: GET /api/v1/issues and GET /api/v1/pull-requests with query filters for assignee, state, and labels, returning compact summaries suitable for the frontend table view.
- dashboard-shell-ui: React SPA shell with a nav bar, health indicator, and a single Overview page showing a milestone progress table and a combined issues/PRs list for the authenticated user.
- pydantic-response-models: Pydantic models for all new endpoints (MilestoneSummaryResponse, IssueResponse, PullRequestResponse, etc.) following DATA_MODELS.md conventions.

## Out of Scope for This Milestone

- PRD → Milestone → Feature → Task hierarchy view (Phase 2)
- Per-person activity summaries with time-range filtering (Phase 2)
- AI pipeline metrics (Phase 3)
- Cycle time / burn-down charts (Phase 3)
- Any write operations to GitHub
- Database or caching layer
- Per-user OAuth authentication
