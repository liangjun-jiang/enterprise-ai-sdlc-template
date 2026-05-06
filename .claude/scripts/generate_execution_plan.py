#!/usr/bin/env python3
"""
generate_execution_plan.py

Reads a Feature Plan (PLAN.md) + context docs and calls Claude Opus to
produce a structured Execution Plan (EXECUTION_PLAN.md).

Usage:
    python generate_execution_plan.py \\
        --plan-file ai-sdlc-docs/plans/PLAN-000-feature-example.md \\
        --context-dir ai-sdlc-docs/context \\
        --output-file ai-sdlc-docs/execution-plans/feature-example/EXECUTION_PLAN.md
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
    load_context_docs,
    load_pipeline_config,
    load_system_prompt,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an Execution Plan from a Feature Plan using Claude Opus.")
    parser.add_argument("--plan-file", required=True, help="Path to PLAN.md")
    parser.add_argument("--context-dir", required=True, help="Path to ai-sdlc-docs/context/")
    parser.add_argument("--output-file", required=True, help="Path to write EXECUTION_PLAN.md")
    return parser.parse_args()


def read_plan_frontmatter(plan_content: str) -> dict[str, str]:
    if not plan_content.startswith("---"):
        return {}
    end = plan_content.find("---", 3)
    if end == -1:
        return {}
    try:
        result: dict[str, str] = yaml.safe_load(plan_content[3:end]) or {}
        return result
    except yaml.YAMLError:
        return {}


def load_upstream_context(frontmatter: dict[str, str], repo_root: Path) -> str:
    """Optionally load PRD and milestone files referenced in plan frontmatter."""
    parts: list[str] = []

    prd_ref = frontmatter.get("prd_ref", "")
    if prd_ref:
        prd_path = repo_root / prd_ref
        if prd_path.exists():
            parts.append(f"## Product Requirements Document\n\n{prd_path.read_text()}")
            print(f"[info] Loaded PRD: {prd_ref}")
        else:
            print(f"[warn] prd_ref points to missing file: {prd_path}", file=sys.stderr)

    milestone_id = frontmatter.get("milestone", "")
    if milestone_id and milestone_id != "ad-hoc":
        milestones_dir = repo_root / "ai-sdlc-docs" / "milestones"
        matches = list(milestones_dir.glob(f"{milestone_id}*.md")) if milestones_dir.exists() else []
        if matches:
            parts.append(f"## Milestone\n\n{matches[0].read_text()}")
            print(f"[info] Loaded milestone: {matches[0].name}")

    return "\n\n---\n\n".join(parts)


def load_codebase_overview(repo_root: Path) -> str:
    overview_path = repo_root / "ai-sdlc-docs" / "context" / "CODEBASE_OVERVIEW.md"
    if not overview_path.exists():
        return ""
    return overview_path.read_text()


def main() -> None:
    args = parse_args()
    repo_root = find_repo_root()

    config = load_pipeline_config(repo_root)
    check_circuit_breaker(config)

    plan_path = Path(args.plan_file)
    context_dir = Path(args.context_dir)
    output_path = Path(args.output_file)

    if not plan_path.exists():
        die(f"Plan file not found: {plan_path}")

    plan_content = plan_path.read_text()
    frontmatter = read_plan_frontmatter(plan_content)
    upstream_context = load_upstream_context(frontmatter, repo_root)
    codebase_overview = load_codebase_overview(repo_root)

    context_docs = load_context_docs(context_dir)
    system_prompt = load_system_prompt(context_dir, "SYSTEM_PROMPT_PLANNER.md")
    model = config["models"]["planner"]
    max_context = config["token_budget"]["max_context_tokens"]
    max_output = config["token_budget"]["max_output_tokens"]

    sections = [f"# Feature Plan\n\n{plan_content}"]
    if upstream_context:
        sections.append(f"# Upstream Context (PRD / Milestone)\n\n{upstream_context}")
    if codebase_overview:
        sections.append(f"# Current Codebase Overview\n\n{codebase_overview}")
    sections.append(f"# Project Context\n\n{context_docs}")

    user_message = apply_token_budget("\n\n---\n\n".join(sections), max_context)

    print(f"[info] Calling {model} to generate execution plan...", flush=True)
    execution_plan = call_claude(
        client=anthropic_client(),
        model=model,
        system=system_prompt,
        user=user_message,
        max_tokens=max_output,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(execution_plan)
    print(f"[info] Execution plan written to {output_path}")


if __name__ == "__main__":
    main()
