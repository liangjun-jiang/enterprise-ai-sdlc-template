---
authors:
  - AI-generated
approvers:
  - ""
feature: hierarchy-tree-ui
priority: medium
milestone: milestone-002-hierarchy-and-analytics
prd_ref: docs/prd/prd-000-dashboard.md
assignees:
  planning: ""
  development: ""
  review: ""
  qa: ""
---

# Feature Plan: Hierarchy Tree UI

## Summary

Build a frontend collapsible tree component that fetches and renders the PRD → Milestone → Feature Plan → Task hierarchy from `GET /api/v1/hierarchy`, with color-coded status badges and click-through links to GitHub. This is the primary visualization for Product Owners to trace work back to PRD requirements.

## Background

The PRD states that a Product Owner must be able to trace any merged PR back to its originating PRD requirement. The hierarchy view endpoint provides the nested data; this feature renders it as an interactive tree. GitHub Projects has no concept of this multi-level hierarchy, so the dashboard fills a critical gap. The tree must be intuitive — expand/collapse nodes, see status at a glance, and click through to GitHub for details.

## Requirements

1. Create a page component `frontend/src/pages/HierarchyPage.tsx` that serves as the container for the hierarchy view.
2. Create a reusable tree component `frontend/src/components/HierarchyTree.tsx` that recursively renders the nested hierarchy.
3. On mount, `HierarchyPage` must fetch `GET /api/v1/hierarchy` (relative URL) and pass the response data to `HierarchyTree`.
4. Each tree node must display:
   - The node title (PRD title, milestone title, feature title, or task title)
   - A color-coded status badge:
     - **open**: grey
     - **in-progress**: blue
     - **done**: green
     - **blocked**: red
   - An expand/collapse toggle (chevron icon or similar) for nodes with children
5. Task-level nodes must also display:
   - The assignee login (if any)
   - Linked PR numbers with their status (open/merged/closed)
6. Every node title must be a clickable link that opens the corresponding `html_url` in a new browser tab (`target="_blank"` with `rel="noopener noreferrer"`).
7. The tree must start fully collapsed (only PRD-level nodes visible) and allow the user to expand any level.
8. While data is loading, display a loading indicator with `data-testid="hierarchy-loading"`.
9. If the fetch fails, display an error message with `data-testid="hierarchy-error"` and the error detail.
10. Define TypeScript types for the hierarchy response in `frontend/src/types/hierarchy.ts` matching the API contract.
11. Add `data-testid` attributes to key elements:
    - `hierarchy-tree` on the tree container
    - `hierarchy-node-{id}` on each node
    - `status-badge-{id}` on each status badge
12. Write tests in `frontend/src/pages/HierarchyPage.test.tsx` and `frontend/src/components/HierarchyTree.test.tsx`:
    - Test that loading state is shown initially
    - Test that the tree renders PRD nodes after successful fetch
    - Test that expanding a node reveals its children
    - Test that error state is shown on fetch failure
    - Test that status badges have correct CSS classes/colors
13. Use no external UI library (no MUI, no Tailwind) — plain CSS or CSS modules for styling, consistent with the current tech stack.
14. All components must be functional components with explicit prop types.

## Out of Scope

- Search or filter within the tree (Phase 3)
- Drag-and-drop reordering
- Inline editing of statuses
- Keyboard navigation beyond default browser behavior
- Routing integration (the page is rendered as a standalone component for now; router integration can come later)
- Any write operations back to the API

## Definition of Done

- [ ] `HierarchyPage.tsx` fetches from `/api/v1/hierarchy` and renders the tree
- [ ] `HierarchyTree.tsx` recursively renders PRD → Milestone → Feature → Task nodes
- [ ] Status badges are color-coded (grey/blue/green/red) per status
- [ ] All node titles link to their GitHub `html_url` in a new tab
- [ ] Tree starts collapsed; expanding reveals children
- [ ] Loading and error states are displayed with appropriate `data-testid` attributes
- [ ] TypeScript types match the API contract
- [ ] All tests pass via `vitest`
- [ ] ESLint passes with `--max-warnings 0`
- [ ] `tsc --noEmit` passes with no errors
- [ ] No `any` types used
- [ ] No hardcoded backend URLs
