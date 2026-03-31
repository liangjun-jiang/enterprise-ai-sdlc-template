#!/usr/bin/env python3
"""
milestone_to_plans.py

Reads a milestone file (and optionally its referenced PRD) and calls Claude Opus
to generate one PLAN.md per feature listed in the milestone.
Opens a PR to the plan branch with all generated plans.

Usage:
    python milestone_to_plans.py \\
        --milestone-file docs/roadmap/milestone-001-mvp-dashboard.md \\
        --repo owner/repo-name \\
        --context-dir docs/context
"""

from __future__ import annotations

import argparse
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
    load_context_docs,
    load_pipeline_config,
    load_system_prompt,
)

MILESTONE_TO_PLANS_PROMPT = """\
You are a senior product engineer. You will be given:
1. A milestone file describing a set of features to build
2. Optionally, the PRD the milestone belongs to
3. Project context documents

Your job is to generate one Feature Plan (PLAN.md) per feature listed in the milestone.

Output a JSON array where each element has:
- "feature_slug": string — kebab-case identifier, e.g. "github-api-client"
- "plan_content": string — the full PLAN.md content (Markdown)

Each plan must include YAML frontmatter:
```
---
author: AI-generated
approver: ""
feature: <feature_slug>
priority: medium
milestone: <milestone id from frontmatter>
prd_ref: <prd_ref from milestone frontmatter, or "">
assignees:
  planning: ""
  development: ""
  review: ""
  qa: ""
---
```

Followed by:
- `# Feature Plan: <Feature Title>`
- `## Summary` — 2-3 sentences
- `## Background` — why this feature is needed (draw from PRD if available)
- `## Requirements` — numbered, concrete, testable
- `## Out of Scope` — what this plan explicitly does not cover
- `## Definition of Done` — bullet list of verifiable completion criteria

Keep each plan focused on ONE feature. If a feature is too large, split it into two plans.
Output ONLY the JSON array. No markdown fences, no explanation.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Feature Plans from a milestone file.")
    parser.add_argument("--milestone-file", required=True)
    parser.add_argument("--repo", required=True, help="owner/repo-name")
    parser.add_argument("--context-dir", required=True)
    return parser.parse_args()


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


def load_prd(prd_ref: str, repo_root: Path) -> str:
    if not prd_ref:
        return ""
    prd_path = repo_root / prd_ref
    if not prd_path.exists():
        print(f"[warn] prd_ref points to missing file: {prd_path}", file=sys.stderr)
        return ""
    return f"## Referenced PRD\n\n{prd_path.read_text()}"


def build_user_message(
    milestone_content: str,
    prd_content: str,
    context_docs: str,
    max_context: int,
) -> str:
    parts = [f"## Milestone\n\n{milestone_content}"]
    if prd_content:
        parts.append(prd_content)
    parts.append(f"## Project Context\n\n{context_docs}")
    return apply_token_budget("\n\n---\n\n".join(parts), max_context)


def create_plans_pr(
    repo_name: str,
    milestone_id: str,
    plans: list[dict[str, str]],
    config: dict[str, Any],
    repo_root: Path,
) -> None:
    import base64
    import json

    gh = github_client()
    repo = get_repo(gh, repo_name)
    plan_branch = config["branches"]["plan"]
    base_sha = repo.get_branch(plan_branch).commit.sha
    branch_name = f"milestone-plans/{milestone_id}"

    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_sha)

    for plan in plans:
        slug = plan["feature_slug"]
        content = plan["plan_content"]
        file_path = f"docs/plans/{slug}/PLAN.md"
        try:
            repo.create_file(
                file_path,
                f"feat: AI-generated plan for {slug}",
                content,
                branch=branch_name,
            )
            print(f"[info] Created {file_path}")
        except Exception as e:
            print(f"[warn] Could not create {file_path}: {e}", file=sys.stderr)

    feature_list = "\n".join(f"- `{p['feature_slug']}`" for p in plans)
    pr = repo.create_pull(
        title=f"Feature Plans: {milestone_id} ({len(plans)} features)",
        body=(
            f"AI-generated Feature Plans for milestone `{milestone_id}`.\n\n"
            f"**Plans included:**\n{feature_list}\n\n"
            f"Review each `PLAN.md` and merge to trigger `plan-to-execution.yml`."
        ),
        head=branch_name,
        base=plan_branch,
    )
    try:
        pr.add_to_labels(config["labels"]["ai_generated"])
    except Exception:
        pass
    print(f"[info] PR created: {pr.html_url}")


def main() -> None:
    import json
    from typing import Any

    args = parse_args()
    repo_root = find_repo_root()

    config = load_pipeline_config(repo_root)
    check_circuit_breaker(config)

    milestone_path = Path(args.milestone_file)
    if not milestone_path.exists():
        die(f"Milestone file not found: {milestone_path}")

    frontmatter = read_frontmatter(milestone_path)
    milestone_id = frontmatter.get("id", milestone_path.stem)
    prd_ref = frontmatter.get("prd_ref", "")

    milestone_content = milestone_path.read_text()
    prd_content = load_prd(prd_ref, repo_root)
    context_dir = Path(args.context_dir)
    context_docs = load_context_docs(context_dir)
    system_prompt = load_system_prompt(context_dir, "SYSTEM_PROMPT_PLANNER.md")
    model = config["models"]["planner"]
    max_context = config["token_budget"]["max_context_tokens"]
    max_output = config["token_budget"]["max_output_tokens"]

    user_message = build_user_message(milestone_content, prd_content, context_docs, max_context)

    print(f"[info] Calling {model} to generate plans for milestone {milestone_id!r}...", flush=True)
    raw = call_claude(
        client=anthropic_client(),
        model=model,
        system=system_prompt,
        user=user_message,
        max_tokens=max_output,
    )

    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    try:
        plans: list[dict[str, str]] = json.loads(text)
    except json.JSONDecodeError as e:
        die(f"Claude returned invalid JSON: {e}\n\nRaw:\n{raw[:500]}")

    print(f"[info] Generated {len(plans)} plan(s)")
    create_plans_pr(args.repo, milestone_id, plans, config, repo_root)


if __name__ == "__main__":
    main()
