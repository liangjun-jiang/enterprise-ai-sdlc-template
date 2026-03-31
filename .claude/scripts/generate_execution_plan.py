#!/usr/bin/env python3
"""
generate_execution_plan.py

Reads a Feature Plan (PLAN.md) + context docs and calls Claude Opus to
produce a structured Execution Plan (EXECUTION_PLAN.md).

Usage:
    python generate_execution_plan.py \\
        --plan-file docs/plans/feature-000-example/PLAN.md \\
        --context-dir docs/context \\
        --output-file docs/execution-plans/feature-000-example/EXECUTION_PLAN.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

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
    parser.add_argument("--context-dir", required=True, help="Path to docs/context/")
    parser.add_argument("--output-file", required=True, help="Path to write EXECUTION_PLAN.md")
    return parser.parse_args()


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
    context_docs = load_context_docs(context_dir)
    system_prompt = load_system_prompt(context_dir, "SYSTEM_PROMPT_PLANNER.md")
    model = config["models"]["planner"]
    max_context = config["token_budget"]["max_context_tokens"]
    max_output = config["token_budget"]["max_output_tokens"]

    user_message = apply_token_budget(
        f"# Feature Plan\n\n{plan_content}\n\n---\n\n# Context Documents\n\n{context_docs}",
        max_context,
    )

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
