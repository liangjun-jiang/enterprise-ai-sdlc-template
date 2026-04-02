---
id: prd-000
title: AI-SDLC Demo Dashboard
status: draft
owner: "James Smith"
---

# PRD: AI-SDLC Demo Dashboard

## Problem Statement

Teams adopting the AI-SDLC pipeline need a way to visualize progress across all roles — product, project, development, QA, and support — in a single view. GitHub Projects handles task-level tracking but has no concept of PRD → Milestone → Feature → Task hierarchy, and no cross-role reporting.

## Target Users

- **Product Owners** — want to see which features from their PRDs are in progress, done, or blocked
- **Project Managers** — want milestone burn-down, per-person workload, and cycle time
- **Tech Leads** — want AI pipeline health: how many AI PRs opened/merged/rejected this week
- **Developers** — want to see their assigned issues and PR status in one place

## Success Metrics

- A PM can answer "what % of milestone-001 is complete?" in under 30 seconds without opening GitHub
- A Product Owner can trace any merged PR back to its originating PRD requirement
- AI pipeline activity (plans generated, issues created, PRs opened/reviewed) is visible on a single dashboard

## Requirements

1. Dashboard reads data from GitHub API (issues, PRs, labels, milestones, assignees)
2. Hierarchy view: PRD → Milestone → Feature Plan → Task Issue
3. Per-person activity summary: issues closed, PRs merged, reviews posted (this week / this month)
4. AI pipeline metrics: plans generated, issues created by AI, AI PRs merged vs. rejected
5. For Phase 0, there is no separate database — GitHub is the source of truth. We will immplement the database & schemas later once we have enough data in Github. 

## Out of Scope

- No write operations from the dashboard (no creating/editing issues from the UI)
- No Jira/Linear integration in v1
- No authentication beyond what GitHub API provides
