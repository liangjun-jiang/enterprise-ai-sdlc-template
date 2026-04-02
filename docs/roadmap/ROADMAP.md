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

The dashboard will be delivered in three phases, starting with a read-only backend that proxies GitHub data, then building the frontend views progressively from simple summaries to the full hierarchy and AI pipeline metrics. All phases treat GitHub as the sole source of truth (no database), consistent with the PRD's Phase 0 constraint. The architecture follows the existing monorepo pattern: FastAPI backend endpoints under `/api/v1/`, React SPA frontend consuming them via relative URLs.

## Phase 1: MVP — GitHub API Backend + Summary Dashboard

**Target:** Q3 2025 (Weeks 1–4)

**Goal:** Deliver a minimal, read-only dashboard where a PM can see milestone completion percentage and a developer can see their assigned issues and PR status.

### Features

- **github-api-client** — Backend service module using `httpx.AsyncClient` to authenticate with the GitHub API via a `GITHUB_TOKEN` environment variable and fetch issues, PRs, milestones, labels, and assignees. Includes response caching with a short TTL to avoid rate limits. [ASSUMPTION: A single GitHub repository is targeted; the repo owner/name will be configured via environment variables `GITHUB_OWNER` and `GITHUB_REPO`.]
- **milestones-endpoint** — `GET /api/v1/milestones` — Returns all milestones with open/closed issue counts and computed completion percentage.
- **issues-endpoint** — `GET /api/v1/issues` — Returns issues with filtering by milestone, assignee, and label. Includes PR linkage metadata.
- **pull-requests-endpoint** — `GET /api/v1/pull-requests` — Returns PRs with status, author, reviewers, and linked issue references.
- **dashboard-summary-page** — Frontend page showing a table of milestones with progress bars (% complete) and totals for open issues and open PRs. Answers the success metric: "what % of milestone-001 is complete?" in under 30 seconds.
- **my-work-panel** — Frontend component showing the current user's assigned issues and PR status in a single list. [ASSUMPTION: "Current user" is determined by a configurable GitHub username passed as a query parameter or frontend setting, since there is no authentication layer.]

### Out of Scope

- PRD → Milestone → Feature → Task hierarchy view (Phase 2)
- AI pipeline metrics (Phase 2)
- Per-person activity summaries with time-range filtering (Phase 2)
- Any write operations to GitHub
- Database or persistent storage

## Phase 2: Beta — Hierarchy View + Activity Summaries

**Target:** Q3 2025 (Weeks 5–8)

**Goal:** Enable Product Owners to trace work from PRD requirements down to individual tasks/PRs, and give Project Managers per-person activity breakdowns.

### Features

- **hierarchy-endpoint** — `GET /api/v1/hierarchy` — Returns the full PRD → Milestone → Feature Plan → Task Issue tree, constructed by parsing GitHub labels and issue/PR metadata. [ASSUMPTION: The hierarchy is encoded in GitHub via a labeling convention, e.g., labels like `prd:prd-000`, `feature:feature-slug`, and milestone assignments. The exact label schema is not specified in the PRD and will need to be defined before implementation.]
- **hierarchy-view-page** — Frontend tree/accordion view displaying the PRD → Milestone → Feature → Task hierarchy. Each node is expandable and shows status (open/closed/merged). Clicking a task links to its GitHub issue; clicking a PR links to GitHub.
- **prd-to-pr-traceability** — Within the hierarchy view, merged PRs are shown under their originating task, which rolls up to the feature and PRD requirement. Satisfies the success metric: "trace any merged PR back to its originating PRD requirement."
- **person-activity-endpoint** — `GET /api/v1/activity?assignee={username}&period={this_week|this_month}` — Returns per-person summary: issues closed, PRs merged, reviews posted within the given time range.
- **person-activity-panel** — Frontend component displaying per-person activity cards with issues closed, PRs merged, and reviews posted, filterable by this week / this month.

### Out of Scope

- AI pipeline metrics (Phase 3)
- Cycle time and burn-down charts (Phase 3)
- Database or persistent storage
- Any write operations to GitHub

## Phase 3: GA — AI Pipeline Metrics + Polish

**Target:** Q4 2025 (Weeks 9–12)

**Goal:** Surface AI pipeline health metrics on the dashboard and deliver the complete, polished experience described in the PRD.

### Features

- **ai-pipeline-metrics-endpoint** — `GET /api/v1/ai-metrics?period={this_week|this_month}` — Returns counts of: plans generated, issues created by AI, AI PRs opened, AI PRs merged, AI PRs rejected. [ASSUMPTION: AI-generated artifacts are identified by the `ai-generated` label on PRs/issues, as defined in the Git/PR standards. "Plans generated" will be derived from commits or files in `docs/plans/` and `docs/execution-plans/` directories, or from AI workflow run counts — the exact data source needs clarification from the product owner.]
- **ai-pipeline-dashboard-panel** — Frontend component showing AI pipeline activity: a summary card with key counts and a simple bar/trend chart for merged vs. rejected AI PRs over time.
- **cycle-time-metrics** — Backend computation and frontend display of cycle time per issue (time from opened to closed) and per PR (time from opened to merged), surfaced in the milestone and person-activity views.
- **burn-down-chart** — Frontend burn-down chart component for each milestone, showing remaining open issues over time. [ASSUMPTION: Historical burn-down data will be approximated from issue event timestamps available via the GitHub API, since there is no database to store snapshots.]
- **dashboard-layout-polish** — Unified dashboard layout with navigation between Summary, Hierarchy, Activity, and AI Metrics views. Responsive design for desktop screens. Loading states, error handling for GitHub API failures, and empty states.
- **rate-limit-resilience** — Backend middleware/logic to handle GitHub API rate limiting gracefully: exponential backoff, user-visible rate-limit status indicator, and response caching to minimize API calls.

### Out of Scope

- Write operations from the dashboard (creating/editing issues)
- Jira/Linear integration
- Authentication beyond GitHub API token
- Database & schemas (deferred per PRD until sufficient GitHub data exists)
- Mobile-optimized layouts
