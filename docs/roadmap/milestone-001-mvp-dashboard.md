---
id: milestone-001
title: MVP Dashboard — GitHub Data + Hierarchy View
target_date: 2026-06-01
prd_ref: docs/prd/prd-000-dashboard.md
status: planned
---

# Milestone: MVP Dashboard — GitHub Data + Hierarchy View

## Goal

Deliver a read-only web dashboard that reads from the GitHub API and shows the PRD → Milestone → Feature → Task hierarchy with basic per-person activity summaries.

## Features

- GitHub API client — authenticate and fetch issues, PRs, labels, milestones, and assignees
- Hierarchy view — display PRD → Milestone → Feature Plan → Task Issue as a collapsible tree
- Per-person activity summary — issues closed and PRs merged this week and this month
- AI pipeline metrics — plans generated, AI issues created, AI PRs merged vs. rejected

## Out of Scope for This Milestone

- Write operations (creating or editing issues from the UI)
- Real-time updates (polling is fine for MVP)
- Authentication UI (use a personal access token passed via env var)
- Jira/Linear integration
