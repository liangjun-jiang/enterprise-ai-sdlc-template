#!/usr/bin/env python3
"""simulate_pipeline.py

Local GitHub-centric simulation:
1. Read issue file
2. Generate implementation plan
3. Generate code proposal JSON
4. Generate AI review JSON

Every step writes local artifacts so subsequent steps can reuse them.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _shared import (
    anthropic_client,
    call_claude,
    find_repo_root,
    load_context_docs,
    load_pipeline_config,
    load_system_prompt,
    parse_llm_json_dict,
)
from generate_implementation_plan import PLAN_SYSTEM_PROMPT
from review_code import REVIEW_SYSTEM_PROMPT


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Local issue->plan->code->review simulation")
    p.add_argument("--issue-file", required=True, help="Markdown file containing issue text")
    p.add_argument(
        "--output-dir",
        default="",
        help="Optional output directory (default: .simulate-output/run-<timestamp>)",
    )
    return p.parse_args()


def output_dir(repo_root: Path, custom: str) -> Path:
    if custom:
        out = (repo_root / custom).resolve()
    else:
        out = repo_root / ".simulate-output" / f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    out.mkdir(parents=True, exist_ok=True)
    return out


def run() -> None:
    args = parse_args()
    repo_root = find_repo_root()
    config = load_pipeline_config(repo_root)
    context_dir = repo_root / "ai-sdlc-docs" / "context"
    issue_path = (repo_root / args.issue_file).resolve()
    if not issue_path.exists():
        raise SystemExit(f"Issue file not found: {issue_path}")

    out = output_dir(repo_root, args.output_dir)
    issue_text = issue_path.read_text().strip()
    if not issue_text:
        raise SystemExit("Issue file is empty")
    (out / "01_issue.md").write_text(issue_text + "\n")
    print(f"[sim] Wrote {out / '01_issue.md'}")

    context_docs = load_context_docs(
        context_dir,
        filenames=["CODING_STANDARDS.md", "SECURITY_CHECKLIST.md"],
    )
    max_context = config["token_budget"]["max_context_tokens"]
    max_output = config["token_budget"]["max_output_tokens"]
    client = anthropic_client()

    plan_user = (
        f"# Issue\n\n{issue_text}\n\n"
        f"## Project Context\n{context_docs}"
    )
    plan_markdown = call_claude(
        client=client,
        model=config["models"]["planner"],
        system=PLAN_SYSTEM_PROMPT,
        user=plan_user[: max_context * 4],
        max_tokens=max_output,
    ).strip()
    plan_markdown = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", plan_markdown)
    plan_markdown = re.sub(r"\n```$", "", plan_markdown).strip()
    (out / "02_implementation_plan.md").write_text(plan_markdown + "\n")
    print(f"[sim] Wrote {out / '02_implementation_plan.md'}")

    coder_system = load_system_prompt(context_dir, "SYSTEM_PROMPT_CODER.md")
    coder_user = (
        f"# Task to Implement\n\n"
        f"## Issue\n{issue_text}\n\n"
        f"## Approved Implementation Plan\n<!-- ai-implementation-plan -->\n{plan_markdown}\n\n"
        "## Current File Contents\n_No affected files listed._\n\n"
        f"## Project Context\n{context_docs}"
    )
    code_raw = call_claude(
        client=client,
        model=config["models"]["coder"],
        system=coder_system,
        user=coder_user[: max_context * 4],
        max_tokens=max_output,
    )
    code_json = parse_llm_json_dict(code_raw)
    (out / "03_codegen.json").write_text(json.dumps(code_json, indent=2) + "\n")
    print(f"[sim] Wrote {out / '03_codegen.json'}")

    files = code_json.get("files", [])
    diff_parts = []
    if isinstance(files, list):
        for item in files:
            if not isinstance(item, dict):
                continue
            path = item.get("path", "unknown")
            action = item.get("action", "modify")
            content = str(item.get("content", ""))
            diff_parts.append(f"### {path} ({action})\n```diff\n{content[:4000]}\n```")
    diff_text = "\n\n".join(diff_parts) if diff_parts else "_No generated files to review._"

    review_user = (
        "# PR: local simulation\n\n"
        "## Diff\n\n"
        f"{diff_text}\n\n"
        "## Coding Standards\n\n"
        f"{(context_dir / 'CODING_STANDARDS.md').read_text()}\n\n"
        "## Security Checklist\n\n"
        f"{(context_dir / 'SECURITY_CHECKLIST.md').read_text()}"
    )
    review_raw = call_claude(
        client=client,
        model=config["models"]["reviewer"],
        system=REVIEW_SYSTEM_PROMPT,
        user=review_user[: max_context * 4],
        max_tokens=max_output,
    )
    review_json = parse_llm_json_dict(review_raw)
    (out / "04_review.json").write_text(json.dumps(review_json, indent=2) + "\n")
    print(f"[sim] Wrote {out / '04_review.json'}")
    print(f"[sim] Complete: {out}")


if __name__ == "__main__":
    run()
