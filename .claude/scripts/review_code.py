#!/usr/bin/env python3
"""
review_code.py

Reads a PR diff and calls Claude Sonnet to post an automated code review
(APPROVE or REQUEST_CHANGES) on the GitHub PR.

Usage:
    python review_code.py \\
        --pr-number 17 \\
        --repo owner/repo-name \\
        --context-dir ai-sdlc-docs/context
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
    die,
    find_repo_root,
    get_repo,
    github_client,
    load_pipeline_config,
    load_system_prompt,
)

REVIEW_SYSTEM_PROMPT = """\
You are a senior software engineer performing a code review. You will be given:
1. A PR diff

Your response must be a JSON object with exactly two fields:
- "verdict": either "APPROVE" or "REQUEST_CHANGES"
- "body": a Markdown string with your review comments

Approve only if:
- All acceptance criteria appear to be met (infer from the diff)
- The implementation logic appears correct and consistent with intended behavior
- No obvious regressions, broken flows, or risky edge-case handling gaps

Request changes otherwise. Be specific and actionable in your comments.
Output ONLY the JSON object. No markdown fences.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Post an AI code review on a GitHub PR.")
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--context-dir", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = find_repo_root()

    config = load_pipeline_config(repo_root)

    gh = github_client()
    repo = get_repo(gh, args.repo)
    pr = repo.get_pull(args.pr_number)

    print(f"[info] Reviewing PR #{args.pr_number}: {pr.title}")

    context_dir = Path(args.context_dir)

    # Collect diff from PR files
    diff_parts: list[str] = []
    for f in pr.get_files():
        patch = getattr(f, "patch", None) or ""
        diff_parts.append(f"### {f.filename} ({f.status})\n```diff\n{patch}\n```")
    diff_text = "\n\n".join(diff_parts)

    model = config["models"]["reviewer"]
    max_context = config["token_budget"]["max_context_tokens"]
    max_output = config["token_budget"]["max_output_tokens"]

    user_message = apply_token_budget(
        f"# PR: {pr.title}\n\n{pr.body or ''}\n\n"
        f"## Diff\n\n{diff_text}",
        max_context,
    )

    print(f"[info] Calling {model} for review...", flush=True)
    import json

    raw = call_claude(
        client=anthropic_client(),
        model=model,
        system=REVIEW_SYSTEM_PROMPT,
        user=user_message,
        max_tokens=max_output,
    )

    try:
        review_data = json.loads(raw.strip())
    except json.JSONDecodeError as e:
        die(f"Claude returned invalid JSON: {e}\n\nRaw:\n{raw[:500]}")

    verdict: str = review_data["verdict"]
    body: str = review_data["body"]

    if verdict not in ("APPROVE", "REQUEST_CHANGES"):
        die(f"Unexpected verdict: {verdict!r}")

    review_body = f"**AI verdict:** `{verdict}`\n\n{body}"
    pr.create_review(body=review_body, event="COMMENT")

    ai_reviewed_label = config["labels"]["ai_reviewed"]
    needs_human_label = config["labels"]["needs_human_review"]
    try:
        pr.add_to_labels(ai_reviewed_label)
        if verdict == "REQUEST_CHANGES":
            pr.add_to_labels(needs_human_label)
    except Exception:
        pass

    print(f"[info] Review posted as COMMENT (verdict: {verdict})")


if __name__ == "__main__":
    main()
