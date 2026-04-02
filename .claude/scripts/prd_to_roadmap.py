#!/usr/bin/env python3
"""
prd_to_roadmap.py

Reads a PRD file and calls Claude Opus to generate a ROADMAP.md —
a high-level timeline of phases and feature groupings.
Opens a PR to the roadmap branch for human review.

Usage:
    python prd_to_roadmap.py \\
        --prd-file docs/prd/prd-000-dashboard.md \\
        --repo owner/repo-name \\
        --context-dir docs/context

    # Local dry-run (no GitHub):
    python prd_to_roadmap.py \\
        --dry-run \\
        --prd-file docs/prd/prd-000-dashboard.md \\
        --context-dir docs/context
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))

from _shared import (
    anthropic_client,
    apply_token_budget,
    call_claude,
    check_circuit_breaker,
    die,
    find_repo_root,
    get_repo,
    github_client,
    list_git_tracked_files,
    load_context_docs,
    load_pipeline_config,
)

SYSTEM_PROMPT = """\
You are a senior product strategist. You will be given a Product Requirements Document (PRD)
and project context. Your job is to generate a ROADMAP.md — a phased delivery plan that
groups the PRD requirements into logical milestones (MVP, Beta, GA, etc.).

Output a single JSON object:
{
  "roadmap_content": "<full ROADMAP.md as a markdown string>"
}

The ROADMAP.md must begin with YAML frontmatter:
---
id: roadmap-<prd id, e.g. 000>
title: "<Product Name> Roadmap"
prd_ref: <path to the PRD file>
status: draft
authors:
  - AI-generated
approvers:
  - ""
---

Followed by:
- `# Roadmap: <Product Name>`
- `## Overview` — 2-3 sentences on the overall delivery strategy
- One `## Phase N: <Name>` section per milestone, each containing:
  - `**Target:** <rough quarter or date range>`
  - `**Goal:** <one sentence>`
  - `### Features` — bullet list of feature slugs with one-line descriptions
  - `### Out of Scope` — what is explicitly deferred to a later phase

Rules:
- Prefer 2-4 phases. Do not create a phase for every feature.
- MVP should be the smallest useful thing. Defer everything non-essential.
- Feature slugs must be kebab-case (e.g. github-api-client).
- Flag any PRD requirements that are ambiguous or missing detail with [ASSUMPTION: ...].
- Output ONLY the JSON object. No markdown fences, no explanation.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a ROADMAP.md from a PRD using Claude Opus.")
    parser.add_argument("--prd-file", required=True, help="Path to the PRD markdown file")
    parser.add_argument("--repo", help="owner/repo-name (required unless --dry-run or --local)")
    parser.add_argument("--context-dir", required=True)
    parser.add_argument("--dry-run", action="store_true", help="Skip GitHub; print raw LLM response to stdout")
    parser.add_argument("--local", action="store_true", help="Skip GitHub; write output files to local disk")
    args = parser.parse_args()
    if not args.dry_run and not args.local and not args.repo:
        parser.error("--repo is required unless --dry-run or --local is set")
    return args


def build_user_message(prd_content: str, context_docs: str, prd_path: str, existing_milestones: list[str], max_context: int) -> str:
    parts = [
        f"## PRD file path\n\n{prd_path}",
        f"## PRD Content\n\n{prd_content}",
    ]
    if existing_milestones:
        ms_list = "\n".join(f"- {m}" for m in existing_milestones)
        parts.append(
            f"## Already existing milestones — do not re-plan these\n\n"
            f"{ms_list}\n\n"
            f"The roadmap phases you generate must not duplicate any milestone listed above."
        )
    parts.append(f"## Project Context\n\n{context_docs}")
    return apply_token_budget("\n\n---\n\n".join(parts), max_context)


def create_roadmap_pr(
    repo_name: str,
    prd_stem: str,
    roadmap_filename: str,
    roadmap_content: str,
    config: dict,  # type: ignore[type-arg]
) -> None:
    gh = github_client()
    repo = get_repo(gh, repo_name)
    roadmap_branch = config["branches"]["roadmap"]
    base_sha = repo.get_branch(roadmap_branch).commit.sha
    branch_name = f"roadmap-draft/{prd_stem}"

    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_sha)

    file_path = f"docs/roadmap/{roadmap_filename}"
    try:
        existing = repo.get_contents(file_path, ref=branch_name)
        repo.update_file(
            file_path,
            f"feat: AI-generated roadmap from {prd_stem}",
            roadmap_content,
            existing.sha,
            branch=branch_name,
        )
    except Exception:
        repo.create_file(
            file_path,
            f"feat: AI-generated roadmap from {prd_stem}",
            roadmap_content,
            branch=branch_name,
        )

    print(f"[info] Written {file_path}")

    pr = repo.create_pull(
        title=f"Roadmap: AI-generated from {prd_stem}",
        body=(
            f"AI-generated roadmap based on `{prd_stem}`.\n\n"
            "Review the phase breakdown and feature groupings.\n"
            "Merge to trigger `roadmap-to-milestones.yml` which generates individual milestone files."
        ),
        head=branch_name,
        base=roadmap_branch,
    )
    try:
        pr.add_to_labels(config["labels"]["ai_generated"])
    except Exception:
        pass
    print(f"[info] PR created: {pr.html_url}")


def main() -> None:
    args = parse_args()
    repo_root = find_repo_root()

    config = load_pipeline_config(repo_root)
    check_circuit_breaker(config)

    prd_path = Path(args.prd_file)
    if not prd_path.exists():
        die(f"PRD file not found: {prd_path}")

    prd_content = prd_path.read_text()
    context_dir = Path(args.context_dir)
    context_docs = load_context_docs(context_dir)
    model = config["models"]["planner"]
    max_context = config["token_budget"]["max_context_tokens"]
    max_output = config["token_budget"]["max_output_tokens"]

    existing_ms_files = list_git_tracked_files(repo_root, "docs/milestones")
    existing_milestones = [Path(f).stem for f in existing_ms_files if Path(f).name.startswith("milestone-")]
    if existing_milestones:
        print(f"[info] Existing milestones (will not duplicate): {existing_milestones}")

    user_message = build_user_message(prd_content, context_docs, str(prd_path), existing_milestones, max_context)

    print(f"[info] Calling {model} to generate roadmap from {prd_path.name!r}...", flush=True)
    raw = call_claude(
        client=anthropic_client(),
        model=model,
        system=SYSTEM_PROMPT,
        user=user_message,
        max_tokens=max_output,
    )

    if args.dry_run:
        print("\n[dry-run] === LLM RESPONSE ===")
        print(raw)
        print("[dry-run] === END ===")
        return

    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    try:
        result: dict[str, str] = json.loads(text)
    except json.JSONDecodeError as e:
        die(f"Claude returned invalid JSON: {e}\n\nRaw:\n{raw[:500]}")

    roadmap_content = result.get("roadmap_content", "")
    if not roadmap_content:
        die("Claude response missing 'roadmap_content' key")

    roadmap_filename = f"ROADMAP-for-{prd_path.stem}.md"

    if args.local:
        out_path = repo_root / "docs" / "roadmap" / roadmap_filename
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(roadmap_content)
        print(f"[local] Written {out_path}")
        return

    create_roadmap_pr(args.repo, prd_path.stem, roadmap_filename, roadmap_content, config)


if __name__ == "__main__":
    main()
