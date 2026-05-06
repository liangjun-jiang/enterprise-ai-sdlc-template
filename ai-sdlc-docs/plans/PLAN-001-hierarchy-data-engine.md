---
authors:
  - AI-generated
approvers:
  - ""
feature: hierarchy-data-engine
priority: medium
milestone: milestone-002-hierarchy-and-analytics
prd_ref: docs/prd/prd-000-dashboard.md
assignees:
  planning: ""
  development: ""
  review: ""
  qa: ""
---

# Feature Plan: Hierarchy Data Engine

## Summary

Build the backend logic that reconstructs the PRD → Milestone → Feature Plan → Task Issue hierarchy by querying the GitHub API and parsing labels, milestones, and issue/PR cross-references. This engine is the foundational data layer that all hierarchy-related endpoints and UI components depend on.

## Background

The AI-SDLC pipeline organizes work in a four-level hierarchy: PRDs → Milestones → Feature Plans → Task Issues. GitHub has no native concept of this hierarchy — the relationships are encoded in labels (e.g., `prd:prd-000`, `milestone:milestone-001`, `feature:some-feature`), milestone associations, and cross-reference links in issue/PR bodies. The dashboard needs a reliable engine that can reconstruct this tree from GitHub's flat data, compute roll-up statuses at each level, and serve it to downstream consumers. Per the PRD, GitHub is the sole source of truth — there is no database.

## Requirements

1. Create a module `backend/app/services/hierarchy.py` containing the hierarchy data engine.
2. The engine must use `httpx.AsyncClient` to call the GitHub REST API (issues, pull requests, milestones, labels endpoints) using a `GITHUB_TOKEN` environment variable for authentication and a `GITHUB_REPO` environment variable (format `owner/repo`) to identify the target repository.
3. If `GITHUB_TOKEN` or `GITHUB_REPO` is not set, the application must fail fast at startup with a clear error message.
4. The engine must identify PRDs by parsing issue or repo-level labels matching the pattern `prd:<prd-id>` (e.g., `prd:prd-000`).
5. The engine must identify milestones by reading GitHub milestones and correlating them with issues that carry a `milestone:<milestone-id>` label.
6. The engine must identify feature plans by parsing labels matching the pattern `feature:<feature-slug>` on issues.
7. The engine must identify task issues as any issue that is associated with a feature (via the `feature:` label) and is not itself a feature-plan-level issue. The distinction is made by the presence of a `task` label or the absence of a `feature-plan` label.
8. The engine must parse issue and PR bodies for cross-references (e.g., `#123`, `owner/repo#123`) to associate PRs with their originating task issues.
9. The engine must compute a roll-up status for each level of the hierarchy:
   - **done**: all children are closed/merged
   - **in-progress**: at least one child is open and has an assignee or linked PR
   - **blocked**: at least one child carries a `blocked` label
   - **open**: default when none of the above apply
10. The engine must return a well-typed data structure (Pydantic models) representing the nested tree: a list of PRD nodes, each containing milestone nodes, each containing feature nodes, each containing task nodes.
11. Define Pydantic models in `backend/app/models/hierarchy.py`: `PrdNode`, `MilestoneNode`, `FeatureNode`, `TaskNode`, each with fields for `id`, `title`, `status`, `html_url`, and `children` (where applicable).
12. The engine must handle GitHub API pagination (follow `Link` headers or use `per_page=100` with page iteration) to avoid missing data in repos with many issues.
13. The engine must handle GitHub API rate-limit responses (HTTP 403 with `X-RateLimit-Remaining: 0`) by raising a descriptive error, not silently returning partial data.
14. All functions must have full type hints and pass `mypy --strict`.
15. Write tests in `backend/app/services/test_hierarchy.py` that mock GitHub API responses using `httpx` transport mocking (no real network calls). Tests must cover:
    - Correct tree construction from a representative set of issues/labels
    - Status roll-up logic for each status type
    - Handling of pagination (simulated multi-page response)
    - Handling of missing `GITHUB_TOKEN` env var

## Out of Scope

- HTTP endpoint exposure (covered by `hierarchy-view-endpoint`)
- Frontend rendering (covered by `hierarchy-tree-ui`)
- Caching or memoization of GitHub API responses (may be added later)
- Database persistence of hierarchy data
- Write operations to GitHub
- Support for multiple repositories simultaneously

## Definition of Done

- [ ] `backend/app/services/hierarchy.py` exists and contains the hierarchy reconstruction logic
- [ ] `backend/app/models/hierarchy.py` exists with `PrdNode`, `MilestoneNode`, `FeatureNode`, `TaskNode` Pydantic models
- [ ] The engine correctly builds a nested tree from mocked GitHub API data in tests
- [ ] Roll-up status computation is correct for done, in-progress, blocked, and open states
- [ ] GitHub API pagination is handled
- [ ] Rate-limit errors raise a descriptive exception
- [ ] Missing `GITHUB_TOKEN` or `GITHUB_REPO` causes a startup failure with a clear message
- [ ] All code passes `ruff check`, `ruff format --check`, and `mypy --strict`
- [ ] All tests pass via `pytest`
- [ ] `API_CONTRACTS.md` is not modified (no endpoint in this feature)
- [ ] `CURRENT_TECH_STACK.md` is updated if any new dependency is added
