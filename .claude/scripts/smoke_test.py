#!/usr/bin/env python3
"""smoke_test.py

Minimal LLM connectivity test plus an optional local Issue->Plan->Code->Review
artifact smoke run.
"""

from __future__ import annotations

import argparse
import json
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


DEFAULT_PROMPT = (
    "You are a helpful assistant. Reply in exactly one sentence: "
    "confirm you are working and state which model you are."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-test LLM connectivity.")
    parser.add_argument(
        "--model",
        default=None,
        help="Model ID override (defaults to 'coder' model from AI_PIPELINE_CONFIG.json)",
    )
    parser.add_argument(
        "--prompt",
        default=DEFAULT_PROMPT,
        help="Prompt text to send",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=256,
        help="Max output tokens (default: 256)",
    )
    parser.add_argument(
        "--issue-file",
        default="",
        help="Run local Issue->Plan->Code->Review smoke using this markdown issue file",
    )
    return parser.parse_args()


def _artifact_dir(repo_root: Path) -> Path:
    d = repo_root / ".simulate-output" / f"smoke-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def run_local_pipeline_smoke(repo_root: Path, config: dict, issue_file: Path) -> None:
    issue_text = issue_file.read_text()
    out_dir = _artifact_dir(repo_root)
    (out_dir / "01_issue.md").write_text(issue_text)

    context_dir = repo_root / "ai-sdlc-docs" / "context"
    context_docs = load_context_docs(context_dir, filenames=["CODING_STANDARDS.md", "SECURITY_CHECKLIST.md"])
    client = anthropic_client()
    max_output = config["token_budget"]["max_output_tokens"]
    max_context = config["token_budget"]["max_context_tokens"]

    plan_user = f"# Issue\n\n{issue_text}\n\n## Project Context\n{context_docs}"
    plan_markdown = call_claude(
        client=client,
        model=config["models"]["planner"],
        system=PLAN_SYSTEM_PROMPT,
        user=plan_user[: max_context * 4],
        max_tokens=max_output,
    ).strip()
    (out_dir / "02_implementation_plan.md").write_text(plan_markdown + "\n")

    coder_system = load_system_prompt(context_dir, "SYSTEM_PROMPT_CODER.md")
    coder_user = (
        f"# Task to Implement\n\n## Issue\n{issue_text}\n\n"
        f"## Approved Implementation Plan\n{plan_markdown}\n\n"
        f"## Current File Contents\n_No affected files listed._\n\n"
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
    (out_dir / "03_codegen.json").write_text(json.dumps(code_json, indent=2) + "\n")

    files = code_json.get("files", [])
    diff_lines = []
    for f in files if isinstance(files, list) else []:
        if not isinstance(f, dict):
            continue
        path = f.get("path", "unknown")
        action = f.get("action", "modify")
        content = str(f.get("content", ""))
        diff_lines.append(f"### {path} ({action})\n```diff\n{content[:2000]}\n```")
    review_user = (
        f"# PR: local smoke generated PR\n\n"
        f"## Diff\n\n{chr(10).join(diff_lines) or '_No files generated._'}\n\n"
        f"## Coding Standards\n\n{(context_dir / 'CODING_STANDARDS.md').read_text()}\n\n"
        f"## Security Checklist\n\n{(context_dir / 'SECURITY_CHECKLIST.md').read_text()}"
    )
    review_raw = call_claude(
        client=client,
        model=config["models"]["reviewer"],
        system=REVIEW_SYSTEM_PROMPT,
        user=review_user[: max_context * 4],
        max_tokens=max_output,
    )
    review_json = parse_llm_json_dict(review_raw)
    (out_dir / "04_review.json").write_text(json.dumps(review_json, indent=2) + "\n")

    print(f"[smoke] Local pipeline artifacts written to: {out_dir}")


def main() -> None:
    args = parse_args()

    repo_root = find_repo_root()
    config = load_pipeline_config(repo_root)

    model = args.model or config["models"]["coder"]
    print(f"[smoke] Prompt : {args.prompt!r}")
    print(f"[smoke] Model  : {model}")
    print(f"[smoke] Calling LLM...", flush=True)

    client = anthropic_client()
    response = call_claude(
        client=client,
        model=model,
        system="You are a helpful assistant.",
        user=args.prompt,
        max_tokens=args.max_tokens,
    )

    print(f"\n[smoke] === RESPONSE ===")
    print(response)
    print(f"[smoke] === END ===")
    print(f"\n[smoke] OK — LLM connectivity confirmed.")

    if args.issue_file:
        issue_path = (repo_root / args.issue_file).resolve()
        if not issue_path.exists():
            raise SystemExit(f"[smoke] issue file not found: {issue_path}")
        print(f"[smoke] Running local Issue->Plan->Code->Review artifact test...")
        run_local_pipeline_smoke(repo_root, config, issue_path)


if __name__ == "__main__":
    main()
