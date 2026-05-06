---
id: roadmap-000
title: "AI-SDLC Demo Dashboard Roadmap"
prd_ref: docs/prd/prd-000-dashboard.md
status: draft
authors:
  - AI-generated
approvers:
  - ""
---

# Roadmap: AI-SDLC Demo Dashboard

## Overview

The dashboard will be delivered in three phases, starting with the smallest useful read-only view of GitHub data and progressively layering on hierarchy visualization, per-person analytics, and AI pipeline metrics. All phases treat GitHub as the sole source of truth (no database), aligning with the PRD's Phase 0 constraint. The frontend is a React SPA communicating with a FastAPI backend that proxies all GitHub API calls.

## Phase 1: MVP — GitHub Data Foundation & Basic Dashboard

**Target:** Q3 2026

**Goal:** Let a PM see milestone completion percentage and let a developer see their assigned issues and PR status from a single page, without opening GitHub.

### Features

- **github-api-client** — Backend service layer using `httpx.AsyncClient` to authenticate with GitHub API (via `GITHUB_TOKEN` env var) and fetch issues, PRs, milestones, labels, and assignees for a configured repository. Includes rate-limit handling and error mapping. [ASSUMPTION: The dashboard targets a single GitHub repository; multi-repo support is not specified in the PRD.]
- **milestone-summary-endpoint** — `GET /api/v1/milestones` and `GET /api/v1/milestones/{milestone_id}/summary` returning open/closed issue counts and completion percentage per milestone.
- **issues-prs-list-endpoint** — `GET /api/v1/issues` and `GET /api/v1/pull-requests` with query filters for assignee, state, and labels. Returns compact summaries suitable for the frontend table view.
- **dashboard-shell-ui** — React SPA shell with a nav bar, health indicator (existing `/health` endpoint), and a single "Overview" page showing a milestone progress table and a combined issues/PRs list for the authenticated user. [ASSUMPTION: "authenticated user" means the user identity behind the configured `GITHUB_TOKEN`, not per-user OAuth — since no auth beyond GitHub API token is in scope.]
- **pydantic-response-models** — Pydantic models for all new endpoints (`MilestoneSummaryResponse`, `IssueResponse`, `PullRequestResponse`, etc.) following `DATA_MODELS.md` conventions.

### Out of Scope

- PRD → Milestone → Feature → Task hierarchy view (Phase 2)
- Per-person activity summaries with time-range filtering (Phase 2)
- AI pipeline metrics (Phase 3)
- Any write operations to GitHub
- Database or caching layer

---

## Phase 2: Hierarchy View & Per-Person Analytics

**Target:** Q4 2026

**Goal:** Enable a Product Owner to trace any PR back to its originating PRD requirement through a visual hierarchy, and give PMs per-person workload and activity breakdowns.

### Features

- **hierarchy-data-engine** — Backend logic that reconstructs the PRD → Milestone → Feature Plan → Task Issue hierarchy by parsing GitHub labels and issue/PR cross-references. [ASSUMPTION: The hierarchy is encoded via GitHub labels (e.g., `prd:prd-000`, `feature:feature-slug`) and issue body links. The PRD does not specify the exact labeling convention, so the engine will rely on a documented label taxonomy that must be defined before implementation.]
- **hierarchy-view-endpoint** — `GET /api/v1/hierarchy` returning a nested JSON tree (PRD → milestones → features → tasks) with status roll-ups at each level.
- **hierarchy-tree-ui** — Frontend collapsible tree component that renders the hierarchy, with color-coded status badges (open, in-progress, done, blocked) and click-through to GitHub URLs.
- **per-person-activity-endpoint** — `GET /api/v1/activity?assignee={login}&period={this_week|this_month}` returning issues closed, PRs merged, and reviews posted for a given person and time range.
- **per-person-activity-ui** — Frontend page/panel showing a filterable table of team members with activity sparklines and summary counts for the selected period.

### Out of Scope

- AI pipeline metrics (Phase 3)
- Cycle time / burn-down charts (Phase 3)
- Database persistence
- Any write operations to GitHub

---

## Phase 3: AI Pipeline Metrics & Reporting Polish

**Target:** Q1 2027

**Goal:** Make all AI pipeline activity visible on the dashboard and ensure a PM can answer cross-role reporting questions in under 30 seconds.

### Features

- **ai-pipeline-metrics-endpoint** — `GET /api/v1/ai-metrics?period={this_week|this_month}` returning counts of: plans generated, issues created by AI (identified by `ai-generated` label), AI PRs opened, AI PRs merged, AI PRs rejected/closed. [ASSUMPTION: "Plans generated" can be inferred from files committed under `docs/plans/` or `docs/execution-plans/` in recent commits. If this is not reliable, an alternative signal (e.g., a GitHub label or workflow run count) will be needed.]
- **ai-pipeline-dashboard-ui** — Dedicated dashboard panel with summary cards (plans generated, AI PRs merged vs. rejected) and a trend chart showing AI activity over the last 4 weeks.
- **milestone-burndown-endpoint** — `GET /api/v1/milestones/{milestone_id}/burndown` returning daily open/closed issue counts over the milestone's date range, suitable for a burn-down chart.
- **burndown-chart-ui** — Frontend burn-down chart component on the milestone detail view, using a lightweight charting library. [ASSUMPTION: A charting library (e.g., Recharts or Chart.js via react-chartjs-2) will need to be added to `frontend/package.json`. The PRD and tech stack do not specify a preference.]
- **traceability-search** — Frontend search/filter on the hierarchy view that lets a Product Owner enter a PR number or merged PR URL and see the full trace back to the originating PRD requirement.

### Out of Scope

- Write operations from the dashboard (creating/editing issues)
- Jira or Linear integration
- Per-user OAuth authentication
- Separate database — GitHub remains the sole source of truth for this version
