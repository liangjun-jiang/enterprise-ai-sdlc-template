#!/usr/bin/env python3
"""
write_code.py

Reads a GitHub Issue (task description + affected files) and calls Claude Sonnet
to generate code. Creates a branch, commits the files, and opens a PR.

Usage:
    python write_code.py \\
        --issue-number 42 \\
        --repo owner/repo-name \\
        --context-dir docs/context
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path
from typing import Any

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
    read_file_safe,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate code for a GitHub Issue using Claude Sonnet.")
    parser.add_argument("--issue-number", type=int, required=True)
    parser.add_argument("--repo", required=True, help="owner/repo-name")
    parser.add_argument("--context-dir", required=True)
    return parser.parse_args()


def extract_affected_files(issue_body: str) -> list[str]:
    """Parse affected file paths from the issue body (lines under 'Affected files:')."""
    paths: list[str] = []
    in_section = False
    for line in issue_body.splitlines():
        if "affected files" in line.lower():
            in_section = True
            continue
        if in_section:
            stripped = line.strip().lstrip("-").strip()
            if stripped.startswith("`") and stripped.endswith("`"):
                stripped = stripped[1:-1]
            # Remove action annotation like " (create)" or " (modify)"
            path_part = stripped.split("(")[0].strip()
            if path_part and "/" in path_part:
                paths.append(path_part)
            elif stripped.startswith("#") or (stripped and not stripped.startswith("`")):
                # Hit the next section or non-path line
                if not stripped.startswith("-"):
                    in_section = False
    return paths


def build_user_message(
    issue_title: str,
    issue_body: str,
    affected_files: list[str],
    repo_root: Path,
    context_docs: str,
    max_context: int,
) -> str:
    file_contents: list[str] = []
    for rel_path in affected_files:
        content = read_file_safe(repo_root / rel_path)
        file_contents.append(f"### {rel_path}\n```\n{content}\n```")

    files_section = "\n\n".join(file_contents) if file_contents else "_No affected files listed._"

    message = f"""# Task to Implement

## Title
{issue_title}

## Description & Acceptance Criteria
{issue_body}

## Current File Contents
{files_section}

## Project Context
{context_docs}
"""
    return apply_token_budget(message, max_context)


def parse_code_response(raw: str) -> dict[str, Any]:
    """Extract JSON from Claude's response, stripping markdown fences if present."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    try:
        result: dict[str, Any] = json.loads(text)
    except json.JSONDecodeError as e:
        die(f"Claude returned invalid JSON: {e}\n\nRaw:\n{raw[:500]}")
    return result


def apply_files_to_branch(
    repo: Any,
    branch_name: str,
    files: list[dict[str, str]],
    base_sha: str,
    pr_title: str,
) -> None:
    """Create branch and commit all file changes."""
    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_sha)

    for file_change in files:
        path = file_change["path"]
        action = file_change["action"]
        content = file_change.get("content", "")

        if action == "delete":
            try:
                existing = repo.get_contents(path, ref=branch_name)
                repo.delete_file(path, f"chore: remove {path}", existing.sha, branch=branch_name)
            except Exception:
                pass  # file already absent
        else:
            encoded = base64.b64encode(content.encode()).decode()
            try:
                existing = repo.get_contents(path, ref=branch_name)
                repo.update_file(
                    path,
                    f"{'feat' if action == 'create' else 'fix'}: {pr_title}",
                    content,
                    existing.sha,
                    branch=branch_name,
                )
            except Exception:
                repo.create_file(path, f"feat: {pr_title}", content, branch=branch_name)

        print(f"[info] {action}: {path}")


def main() -> None:
    args = parse_args()
    repo_root = find_repo_root()

    config = load_pipeline_config(repo_root)
    check_circuit_breaker(config)

    gh = github_client()
    repo = get_repo(gh, args.repo)
    issue = repo.get_issue(args.issue_number)

    print(f"[info] Processing issue #{args.issue_number}: {issue.title}")

    context_dir = Path(args.context_dir)
    context_docs = load_context_docs(context_dir)
    system_prompt = load_system_prompt(context_dir, "SYSTEM_PROMPT_CODER.md")
    model = config["models"]["coder"]
    max_context = config["token_budget"]["max_context_tokens"]
    max_output = config["token_budget"]["max_output_tokens"]

    affected_files = extract_affected_files(issue.body or "")
    print(f"[info] Affected files: {affected_files}")

    user_message = build_user_message(
        issue_title=issue.title,
        issue_body=issue.body or "",
        affected_files=affected_files,
        repo_root=repo_root,
        context_docs=context_docs,
        max_context=max_context,
    )

    print(f"[info] Calling {model} to generate code...", flush=True)
    raw_response = call_claude(
        client=anthropic_client(),
        model=model,
        system=system_prompt,
        user=user_message,
        max_tokens=max_output,
    )

    result = parse_code_response(raw_response)
    branch_name: str = result["branch_name"]
    pr_title: str = result["pr_title"]
    pr_body: str = result["pr_body"]
    files: list[dict[str, str]] = result["files"]

    dev_branch = config["branches"]["dev"]
    base = repo.get_branch(dev_branch)
    base_sha = base.commit.sha

    print(f"[info] Creating branch {branch_name!r} from {dev_branch}...")
    apply_files_to_branch(repo, branch_name, files, base_sha, pr_title)

    ai_label = config["labels"]["ai_generated"]
    pr = repo.create_pull(
        title=pr_title,
        body=pr_body + f"\n\nCloses #{args.issue_number}",
        head=branch_name,
        base=dev_branch,
    )
    try:
        pr.add_to_labels(ai_label)
    except Exception:
        pass

    print(f"[info] PR created: {pr.html_url}")


if __name__ == "__main__":
    main()
