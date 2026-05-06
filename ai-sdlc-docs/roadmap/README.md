# Roadmap

This directory holds `ROADMAP.md` — the high-level phased delivery plan generated from a PRD.

Milestone files (`milestone-*.md`) live in [`docs/milestones/`](../milestones/).

## How the pipeline uses this

When `ROADMAP.md` is merged to the `roadmap` branch, `roadmap-to-milestones.yml` fires:
1. Reads `ROADMAP.md` and identifies phases
2. Calls Claude Opus to generate one `milestone-NNN-*.md` per phase
3. Opens a PR to the `milestone` branch with all generated milestone files for human review
