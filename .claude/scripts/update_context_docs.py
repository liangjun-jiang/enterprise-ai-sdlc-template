#!/usr/bin/env python3
"""
update_context_docs.py

After a PR merges to dev, reads the diff and uses Claude Sonnet to determine
which context docs need updating, then commits the changes back to dev.

Usage:
    python update_context_docs.py \\
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
    check_circuit_breaker,
    die,
    find_repo_root,
    get_repo,
    github_client,
    load_context_docs,
    load_pipeline_config,
    parse_llm_json_dict,
    try_parse_llm_json,
)

UPDATE_SYSTEM_PROMPT = """\
You are a technical writer maintaining living documentation for a software project.
You will be given:
1. A merged PR diff
2. The current contents of all context documentation files

Your job is to identify which context docs need to be updated to stay accurate,
and return the updated content.

Respond with a JSON object where:
- Keys are relative file paths (e.g. "ai-sdlc-docs/context/CURRENT_TECH_STACK.md")
- Values are the complete updated file contents (as strings)

Only include files that actually need changes. If nothing needs updating, return {}.
Do not add explanatory prose — just the file contents.
Output ONLY the JSON object. No markdown fences.

Context docs you may update:
- ai-sdlc-docs/context/ARCHITECTURE.md
- ai-sdlc-docs/context/CURRENT_TECH_STACK.md
- ai-sdlc-docs/context/CODING_STANDARDS.md
- ai-sdlc-docs/context/DATA_MODELS.md
- ai-sdlc-docs/context/API_CONTRACTS.md

Do NOT update SYSTEM_PROMPT_PLANNER.md, SYSTEM_PROMPT_CODER.md, SECURITY_CHECKLIST.md,
GLOSSARY.md, or AI_PIPELINE_CONFIG.json — those require deliberate human changes.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update context docs after a PR merges.")
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--context-dir", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = find_repo_root()

    config = load_pipeline_config(repo_root)
    check_circuit_breaker(config)

    gh = github_client()
    repo = get_repo(gh, args.repo)
    pr = repo.get_pull(args.pr_number)

    if not pr.merged:
        die(f"PR #{args.pr_number} is not merged. This script only runs post-merge.")

    print(f"[info] Updating context docs after merge of PR #{args.pr_number}: {pr.title}")

    context_dir = Path(args.context_dir)
    current_docs = load_context_docs(context_dir)

    diff_parts: list[str] = []
    for f in pr.get_files():
        patch = getattr(f, "patch", None) or ""
        diff_parts.append(f"### {f.filename} ({f.status})\n```diff\n{patch}\n```")
    diff_text = "\n\n".join(diff_parts)

    model = config["models"]["context_updater"]
    max_context = config["token_budget"]["max_context_tokens"]
    max_output = config["token_budget"]["max_output_tokens"]

    user_message = apply_token_budget(
        f"# Merged PR: {pr.title}\n\n{pr.body or ''}\n\n"
        f"## Diff\n\n{diff_text}\n\n"
        f"## Current Context Docs\n\n{current_docs}",
        max_context,
    )

    print(f"[info] Calling {model} to identify doc updates...", flush=True)
    client = anthropic_client()

    raw = call_claude(
        client=client,
        model=model,
        system=UPDATE_SYSTEM_PROMPT,
        user=user_message,
        max_tokens=max_output,
    )

    parsed = try_parse_llm_json(raw)
    if not isinstance(parsed, dict):
        print(
            "[warn] Invalid JSON from context updater; retrying with JSON-only instruction...",
            flush=True,
        )
        raw = call_claude(
            client=client,
            model=model,
            system=UPDATE_SYSTEM_PROMPT,
            user=user_message
            + "\n\nIMPORTANT: Output ONLY a single valid JSON object. "
            "Keys are file paths, values are full file contents. "
            "No markdown fences, no commentary.",
            max_tokens=max_output,
        )
        updates = parse_llm_json_dict(raw)
    else:
        updates = parsed

    if not updates:
        print("[info] No context doc updates needed.")
        return

    dev_branch = config["branches"]["dev"]

    for file_path, new_content in updates.items():
        try:
            existing = repo.get_contents(file_path, ref=dev_branch)
            repo.update_file(
                file_path,
                f"docs: update {file_path} after PR #{args.pr_number}",
                new_content,
                existing.sha,  # type: ignore[union-attr]
                branch=dev_branch,
            )
            print(f"[info] Updated: {file_path}")
        except Exception as e:
            print(f"[warn] Could not update {file_path}: {e}", file=sys.stderr)

    print(f"[info] Done. Updated {len(updates)} context doc(s).")


if __name__ == "__main__":
    main()
