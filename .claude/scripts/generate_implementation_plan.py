#!/usr/bin/env python3
"""
generate_implementation_plan.py

Reads a GitHub issue thread (body + comments), generates an implementation plan,
and upserts a single canonical planning comment on the issue.
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from _shared import (
    anthropic_client,
    apply_token_budget,
    call_claude,
    die,
    find_repo_root,
    get_repo,
    github_client,
    load_context_docs,
    load_pipeline_config,
)

PLAN_MARKER = "<!-- ai-implementation-plan -->"
MAX_DIFF_LINES = 200

PLAN_SYSTEM_PROMPT = """\
You are a senior software engineer preparing implementation plans for GitHub issues.

Return ONLY markdown (no JSON) with the exact sections below:

## Implementation Plan
- Scope
- Assumptions
- Proposed changes (3-7 concrete steps)
- Test plan
- Risks
- Out of scope

## Ready for Coding Checklist
- [ ] Requirements are clear
- [ ] Acceptance criteria are testable
- [ ] Dependencies/risks are identified
- [ ] Scope is bounded for one PR

## Open Questions
- List unresolved questions, or write "None."

Rules:
- Be concrete and actionable.
- Keep it concise.
- If issue details are vague, write assumptions explicitly.
- Do not use markdown code fences.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate/upsert an implementation plan on a GitHub issue.")
    parser.add_argument("--issue-number", type=int, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--context-dir", required=True)
    return parser.parse_args()


def format_issue_comments(issue: Any) -> str:
    parts: list[str] = []
    for c in issue.get_comments():
        author = getattr(c.user, "login", None) or "unknown"
        when = getattr(c, "created_at", None)
        when_s = when.isoformat() if when is not None else ""
        body = (c.body or "").strip()
        parts.append(f"### @{author} ({when_s})\n{body}")
    return "\n\n".join(parts)


def _strip_marker(text: str) -> str:
    return text.replace(PLAN_MARKER, "", 1).strip()


def _latest_plan_comment(issue: Any) -> Any | None:
    latest = None
    for c in issue.get_comments():
        if PLAN_MARKER in (c.body or ""):
            latest = c
    return latest


def _plan_version_number(issue: Any) -> int:
    n = 0
    for c in issue.get_comments():
        if PLAN_MARKER in (c.body or ""):
            n += 1
    return n + 1


def _build_plan_diff(previous: str, current: str) -> str:
    diff_lines = list(
        difflib.unified_diff(
            previous.splitlines(),
            current.splitlines(),
            fromfile="before",
            tofile="after",
            lineterm="",
        )
    )
    if not diff_lines:
        return "_No textual changes from previous plan._"
    trimmed = diff_lines[:MAX_DIFF_LINES]
    clipped = len(diff_lines) > MAX_DIFF_LINES
    header = "```diff\n" + "\n".join(trimmed)
    if clipped:
        header += "\n... (diff truncated)"
    header += "\n```"
    return header


def create_plan_comment(issue: Any, plan_markdown: str) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    latest = _latest_plan_comment(issue)
    version = _plan_version_number(issue)
    normalized_new = plan_markdown.strip()

    sections = [
        PLAN_MARKER,
        f"## AI Implementation Plan (v{version})",
        f"_Generated at {now}_",
        "",
        normalized_new,
    ]

    if latest:
        previous_text = _strip_marker(latest.body or "")
        sections.extend(
            [
                "",
                "### Plan Delta (Before vs After)",
                "<details>",
                "<summary>Show markdown diff from previous plan</summary>",
                "",
                _build_plan_diff(previous_text, normalized_new),
                "",
                "</details>",
            ]
        )

    issue.create_comment("\n".join(sections).strip() + "\n")
    print(f"[info] Created plan comment version v{version}")


def main() -> None:
    args = parse_args()
    repo_root = find_repo_root()
    config = load_pipeline_config(repo_root)

    gh = github_client()
    repo = get_repo(gh, args.repo)
    issue = repo.get_issue(args.issue_number)

    issue_title = issue.title
    issue_body = issue.body or ""
    issue_comments = format_issue_comments(issue)
    if not issue_body.strip() and not issue_comments.strip():
        die("Issue has no body/comments; cannot build implementation plan.")

    context_docs = load_context_docs(
        Path(args.context_dir),
        filenames=["CODING_STANDARDS.md", "SECURITY_CHECKLIST.md"],
    )
    model = config["models"]["planner"]
    max_context = config["token_budget"]["max_context_tokens"]
    max_output = config["token_budget"]["max_output_tokens"]

    user_prompt = apply_token_budget(
        f"# Issue\n\n## Title\n{issue_title}\n\n## Body\n{issue_body}\n\n"
        f"## Discussion (comments)\n{issue_comments or '_No comments._'}\n\n"
        f"## Project Context\n{context_docs}",
        max_context,
    )

    client = anthropic_client()
    plan_markdown = call_claude(
        client=client,
        model=model,
        system=PLAN_SYSTEM_PROMPT,
        user=user_prompt,
        max_tokens=max_output,
    ).strip()

    # Defensive cleanup for accidental code fences.
    plan_markdown = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", plan_markdown)
    plan_markdown = re.sub(r"\n```$", "", plan_markdown).strip()

    create_plan_comment(issue, plan_markdown)
    print("[info] Implementation plan comment posted.")


if __name__ == "__main__":
    main()
