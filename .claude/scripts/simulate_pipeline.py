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
    parse_llm_json_dict_prefer_keys,
)
from generate_implementation_plan import PLAN_SYSTEM_PROMPT
from review_code import REVIEW_SYSTEM_PROMPT

FILE_PLAN_SYSTEM_PROMPT = """\
Return ONLY valid JSON with this exact shape:
{
  "files": [
    { "path": "repo/relative/path.ext", "action": "create|modify|delete" }
  ]
}
No prose. No markdown fences.
"""

FILE_CONTENT_SYSTEM_PROMPT = """\
Return ONLY valid JSON with this exact shape:
{
  "content": "<full file content>"
}
No prose. No markdown fences.
"""


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


def validate_codegen_payload(payload: dict[str, object]) -> None:
    required = ("files",)
    missing = [k for k in required if k not in payload]
    if missing:
        raise SystemExit(
            "Codegen JSON missing required key(s): "
            + ", ".join(missing)
            + ". See 03_codegen.raw.txt for full model response."
        )
    files = payload.get("files")
    if not isinstance(files, list) or not files:
        raise SystemExit("Codegen JSON 'files' must be a non-empty list.")
    for i, item in enumerate(files, start=1):
        if not isinstance(item, dict):
            raise SystemExit(f"Codegen JSON files[{i}] must be an object.")
        path = str(item.get("path", "")).strip()
        action = str(item.get("action", "")).strip().lower()
        if not path:
            raise SystemExit(f"Codegen JSON files[{i}] missing 'path'.")
        if action not in {"create", "modify", "delete"}:
            raise SystemExit(
                f"Codegen JSON files[{i}] has invalid 'action': {action!r}. "
                "Expected one of create|modify|delete."
            )


def normalize_file_plan(payload: dict[str, object]) -> list[dict[str, str]]:
    files = payload.get("files")
    if not isinstance(files, list) or not files:
        raise SystemExit("File plan must contain non-empty `files` array.")
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for i, item in enumerate(files, start=1):
        if not isinstance(item, dict):
            raise SystemExit(f"File plan files[{i}] must be an object.")
        path = str(item.get("path", "")).strip()
        action = str(item.get("action", "")).strip().lower()
        if not path:
            raise SystemExit(f"File plan files[{i}] missing `path`.")
        if action not in {"create", "modify", "delete"}:
            raise SystemExit(f"File plan files[{i}] invalid action {action!r}.")
        if path in seen:
            continue
        seen.add(path)
        out.append({"path": path, "action": action})
    return out


def allows_empty_file(path: str) -> bool:
    name = Path(path).name
    return name in {"__init__.py", ".gitkeep", ".keep"}


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
    plan_raw = call_claude(
        client=client,
        model=config["models"]["coder"],
        system=FILE_PLAN_SYSTEM_PROMPT,
        user=(coder_user + "\n\nOutput only JSON with key `files` and each item with `path`,`action`.")[
            : max_context * 4
        ],
        max_tokens=max_output,
    )
    (out / "03_codegen.raw.txt").write_text(plan_raw)
    try:
        file_plan_json = parse_llm_json_dict_prefer_keys(plan_raw, preferred_keys=["files"])
        file_plan = normalize_file_plan(file_plan_json)
    except SystemExit:
        print("[sim][warn] Invalid/incomplete file plan; retrying with strict JSON-only response...", flush=True)
        repair_user = (
            coder_user
            + "\n\nIMPORTANT: Re-output your previous answer as valid JSON only. "
            + "No prose, no markdown fences, no explanation. "
            + "Top-level JSON must include key `files` (non-empty list of {path, action})."
        )
        repair_plan_raw = call_claude(
            client=client,
            model=config["models"]["coder"],
            system=FILE_PLAN_SYSTEM_PROMPT,
            user=repair_user[: max_context * 4],
            max_tokens=max_output,
        )
        (out / "03_codegen.repair.raw.txt").write_text(repair_plan_raw)
        file_plan_json = parse_llm_json_dict_prefer_keys(repair_plan_raw, preferred_keys=["files"])
        file_plan = normalize_file_plan(file_plan_json)

    generated_files: list[dict[str, str]] = []
    for item in file_plan:
        path = item["path"]
        action = item["action"]
        if action == "delete":
            generated_files.append({"path": path, "action": action, "content": ""})
            continue
        content_user = (
            f"{coder_user}\n\n"
            f"## Target File\nPath: {path}\nAction: {action}\n\n"
            "Return full final file content only in JSON."
        )
        content_raw = call_claude(
            client=client,
            model=config["models"]["coder"],
            system=FILE_CONTENT_SYSTEM_PROMPT,
            user=content_user[: max_context * 4],
            max_tokens=max_output,
        )
        content_json = parse_llm_json_dict_prefer_keys(content_raw, preferred_keys=["content"])
        content = str(content_json.get("content", ""))
        if action in {"create", "modify"} and not content.strip() and not allows_empty_file(path):
            retry_user = (
                f"{content_user}\n\n"
                'Your previous response had empty `content`. Return non-empty JSON only: {"content":"<full file content>"}'
            )
            retry_raw = call_claude(
                client=client,
                model=config["models"]["coder"],
                system=FILE_CONTENT_SYSTEM_PROMPT,
                user=retry_user[: max_context * 4],
                max_tokens=max_output,
            )
            retry_json = parse_llm_json_dict_prefer_keys(retry_raw, preferred_keys=["content"])
            content = str(retry_json.get("content", ""))
            if not content.strip():
                raise SystemExit(
                    f"Model returned empty content for {action} action on {path}."
                )
        generated_files.append({"path": path, "action": action, "content": content})

    code_json: dict[str, object] = {"files": generated_files}
    validate_codegen_payload(code_json)
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
    review_json = parse_llm_json_dict_prefer_keys(review_raw)
    (out / "04_review.json").write_text(json.dumps(review_json, indent=2) + "\n")
    print(f"[sim] Wrote {out / '04_review.json'}")
    print(f"[sim] Complete: {out}")


if __name__ == "__main__":
    run()
