#!/usr/bin/env python3
"""
roadmap_to_milestones.py

Reads a ROADMAP.md file and calls Claude Opus to generate one
milestone-NNN-*.md file per phase. Opens a PR to the roadmap branch.

Usage:
    python roadmap_to_milestones.py \\
        --roadmap-file docs/roadmap/ROADMAP.md \\
        --repo owner/repo-name \\
        --context-dir docs/context

    # Local dry-run (no GitHub):
    python roadmap_to_milestones.py \\
        --dry-run \\
        --roadmap-file docs/roadmap/ROADMAP.md \\
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
You are a senior product engineer. You will be given a ROADMAP.md describing
delivery phases and a list of features per phase.

Your job is to generate one milestone file per phase.

Output a JSON array where each element has:
- "id": string — e.g. "milestone-001-mvp" (zero-padded, kebab-case)
- "filename": string — e.g. "milestone-001-mvp.md"
- "content": string — the full milestone markdown

Each milestone file must begin with YAML frontmatter:
---
id: <milestone id>
title: <human-readable title>
target_date: <YYYY-MM-DD or best estimate>
prd_ref: <prd_ref from roadmap frontmatter, or "">
status: planned
authors:
  - AI-generated
approvers:
  - ""
---

Followed by:
- `# Milestone: <Title>`
- `## Goal` — one sentence
- `## Features` — bullet list matching the roadmap phase, one feature per line:
  `- <feature-slug>: <one-line description>`
- `## Out of Scope for This Milestone` — what is explicitly deferred

Rules:
- Milestone IDs must be sequentially numbered starting from 001.
- Feature slugs must be kebab-case and match those in the roadmap.
- Keep each milestone file focused and concise.
- Output ONLY the JSON array. No markdown fences, no explanation.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate milestone files from a ROADMAP.md using Claude Opus.")
    parser.add_argument("--roadmap-file", required=True, help="Path to ROADMAP.md")
    parser.add_argument("--repo", help="owner/repo-name (required unless --dry-run or --local)")
    parser.add_argument("--context-dir", required=True)
    parser.add_argument("--dry-run", action="store_true", help="Skip GitHub; print raw LLM response to stdout")
    parser.add_argument("--local", action="store_true", help="Skip GitHub; write output files to local disk")
    args = parser.parse_args()
    if not args.dry_run and not args.local and not args.repo:
        parser.error("--repo is required unless --dry-run or --local is set")
    return args


def read_frontmatter(path: Path) -> dict[str, str]:
    content = path.read_text()
    if not content.startswith("---"):
        return {}
    end = content.find("---", 3)
    if end == -1:
        return {}
    try:
        result: dict[str, str] = yaml.safe_load(content[3:end]) or {}
        return result
    except yaml.YAMLError:
        return {}


def build_user_message(roadmap_content: str, context_docs: str, existing_milestones: list[str], max_context: int) -> str:
    parts = [f"## ROADMAP.md\n\n{roadmap_content}"]
    if existing_milestones:
        ms_list = "\n".join(f"- {m}" for m in existing_milestones)
        parts.append(
            f"## Already existing milestones — do not duplicate\n\n"
            f"{ms_list}\n\n"
            f"Only generate milestone files for phases that are NOT already listed above."
        )
    parts.append(f"## Project Context\n\n{context_docs}")
    return apply_token_budget("\n\n---\n\n".join(parts), max_context)


def create_milestones_pr(
    repo_name: str,
    roadmap_stem: str,
    milestones: list[dict[str, str]],
    config: dict,  # type: ignore[type-arg]
) -> None:
    gh = github_client()
    repo = get_repo(gh, repo_name)
    milestone_branch = config["branches"]["milestone"]
    base_sha = repo.get_branch(milestone_branch).commit.sha
    branch_name = f"milestones/{roadmap_stem}"

    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_sha)

    for m in milestones:
        file_path = f"docs/milestones/{m['filename']}"
        try:
            repo.create_file(
                file_path,
                f"feat: AI-generated {m['id']}",
                m["content"],
                branch=branch_name,
            )
            print(f"[info] Created {file_path}")
        except Exception as e:
            print(f"[warn] Could not create {file_path}: {e}", file=sys.stderr)

    milestone_list = "\n".join(f"- `{m['id']}`" for m in milestones)
    pr = repo.create_pull(
        title=f"Milestones: AI-generated from {roadmap_stem} ({len(milestones)} milestones)",
        body=(
            f"AI-generated milestone files from `docs/roadmap/ROADMAP.md`.\n\n"
            f"**Milestones included:**\n{milestone_list}\n\n"
            "Review each milestone file and merge. Each merged milestone file will "
            "trigger `milestone-to-plans.yml` to generate Feature Plans."
        ),
        head=branch_name,
        base=milestone_branch,
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

    roadmap_path = Path(args.roadmap_file)
    if not roadmap_path.exists():
        die(f"Roadmap file not found: {roadmap_path}")

    roadmap_content = roadmap_path.read_text()
    context_dir = Path(args.context_dir)
    context_docs = load_context_docs(context_dir)
    model = config["models"]["planner"]
    max_context = config["token_budget"]["max_context_tokens"]
    max_output = config["token_budget"]["max_output_tokens"]

    existing_ms_files = list_git_tracked_files(repo_root, "docs/milestones")
    existing_milestones = [Path(f).stem for f in existing_ms_files if Path(f).name.startswith("milestone-")]
    if existing_milestones:
        print(f"[info] Existing milestones (will skip): {existing_milestones}")

    user_message = build_user_message(roadmap_content, context_docs, existing_milestones, max_context)

    print(f"[info] Calling {model} to generate milestones from {roadmap_path.name!r}...", flush=True)
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
        milestones: list[dict[str, str]] = json.loads(text)
    except json.JSONDecodeError as e:
        die(f"Claude returned invalid JSON: {e}\n\nRaw:\n{raw[:500]}")

    print(f"[info] Generated {len(milestones)} milestone(s)")

    if args.local:
        out_dir = repo_root / "docs" / "milestones"
        out_dir.mkdir(parents=True, exist_ok=True)
        for m in milestones:
            out_path = out_dir / m["filename"]
            out_path.write_text(m["content"])
            print(f"[local] Written {out_path}")
        return

    create_milestones_pr(args.repo, roadmap_path.stem, milestones, config)


if __name__ == "__main__":
    main()
