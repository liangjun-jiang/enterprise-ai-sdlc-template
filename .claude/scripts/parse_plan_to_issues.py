#!/usr/bin/env python3
"""
parse_plan_to_issues.py

Reads an Execution Plan and creates GitHub Issues for each task.
Uses Claude Sonnet to extract structured issue payloads from the Markdown.

Usage:
    python parse_plan_to_issues.py \\
        --execution-plan-file docs/execution-plans/feature-000-example/EXECUTION_PLAN.md \\
        --repo owner/repo-name \\
        --project-id 1
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).parent))

from _shared import (
    anthropic_client,
    call_claude,
    check_circuit_breaker,
    die,
    find_repo_root,
    get_repo,
    github_client,
    load_pipeline_config,
)

EXTRACTION_SYSTEM_PROMPT = """\
You are a precise JSON extractor. Given a Markdown Execution Plan, output a JSON array of GitHub Issue objects.
Each object must have exactly these fields:
- "title": string — the task title (imperative mood)
- "body": string — full Markdown body including description, acceptance criteria, and affected files
- "labels": [] (ignored by caller; keep as empty list)
- "task_id": string — e.g. "TASK-001"
- "depends_on": list of task_id strings this task depends on (empty list if none)
- "assignee": string — the assignee name/username from the task's Assignee field, or "" if unset

Output ONLY the JSON array. No prose, no markdown fences, no explanation.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse an Execution Plan into GitHub Issues.")
    parser.add_argument("--execution-plan-file", required=True, help="Path to EXECUTION_PLAN.md")
    parser.add_argument("--plan-file", default=None, help="Path to original PLAN.md (for frontmatter attribution)")
    parser.add_argument("--repo", required=True, help="GitHub repo in owner/name format")
    parser.add_argument("--project-id", type=int, default=None, help="GitHub Project number (optional)")
    return parser.parse_args()


def read_plan_frontmatter(plan_file: str | None) -> dict[str, Any]:
    """Parse YAML frontmatter from PLAN.md if provided."""
    if not plan_file:
        return {}
    path = Path(plan_file)
    if not path.exists():
        return {}
    content = path.read_text()
    if not content.startswith("---"):
        return {}
    end = content.find("---", 3)
    if end == -1:
        return {}
    try:
        result: dict[str, Any] = yaml.safe_load(content[3:end]) or {}
        return result
    except yaml.YAMLError:
        return {}


def extract_issues(plan_content: str, model: str, max_tokens: int) -> list[dict[str, Any]]:
    client = anthropic_client()
    raw = call_claude(
        client=client,
        model=model,
        system=EXTRACTION_SYSTEM_PROMPT,
        user=f"Extract GitHub Issues from this Execution Plan:\n\n{plan_content}",
        max_tokens=max_tokens,
    )
    try:
        issues: list[dict[str, Any]] = json.loads(raw)
    except json.JSONDecodeError as e:
        die(f"Claude returned invalid JSON: {e}\n\nRaw output:\n{raw}")
    return issues


def create_github_issues(
    repo_name: str,
    issues: list[dict[str, Any]],
    config: dict[str, Any],
    frontmatter: dict[str, Any],
) -> list[int]:
    gh = github_client()
    repo = get_repo(gh, repo_name)
    ai_label = config["labels"]["ai_generated"]

    # Ensure labels exist
    existing_labels = {lb.name for lb in repo.get_labels()}
    for label_name, color in [(ai_label, "0075ca")]:
        if label_name not in existing_labels:
            repo.create_label(name=label_name, color=color)

    # Attribution from frontmatter
    raw_authors = frontmatter.get("authors", [])
    author = ", ".join(str(a) for a in raw_authors if a)
    feature = frontmatter.get("feature", "")
    fm_assignees: dict[str, str] = frontmatter.get("assignees", {}) or {}
    default_dev_assignee = fm_assignees.get("development", "")

    created_numbers: list[int] = []
    task_id_to_number: dict[str, int] = {}

    for issue_data in issues:
        task_id = issue_data["task_id"]
        depends_on = issue_data.get("depends_on", [])

        body = issue_data["body"]

        # Attribution footer
        meta_lines: list[str] = []
        if author:
            meta_lines.append(f"**Plan author:** {author}")
        if feature:
            meta_lines.append(f"**Feature:** `{feature}`")
        if depends_on:
            dep_refs = ", ".join(f"`{d}`" for d in depends_on)
            meta_lines.append(f"**Depends on:** {dep_refs}")
        if meta_lines:
            body += "\n\n---\n" + "\n\n".join(meta_lines)

        # Assignee: prefer per-task assignee from extraction, fall back to frontmatter development assignee
        assignee = issue_data.get("assignee", "").strip() or default_dev_assignee

        create_kwargs: dict[str, Any] = {
            "title": issue_data["title"],
            "body": body,
            "labels": [ai_label],
        }
        if assignee:
            create_kwargs["assignee"] = assignee

        issue = repo.create_issue(**create_kwargs)
        task_id_to_number[task_id] = issue.number
        created_numbers.append(issue.number)
        print(f"[info] Created issue #{issue.number}: {issue_data['title']}" + (f" (assigned: {assignee})" if assignee else ""))

    return created_numbers


def main() -> None:
    args = parse_args()
    repo_root = find_repo_root()

    config = load_pipeline_config(repo_root)
    check_circuit_breaker(config)

    plan_path = Path(args.execution_plan_file)
    if not plan_path.exists():
        die(f"Execution plan not found: {plan_path}")

    plan_content = plan_path.read_text()
    model = config["models"]["issue_parser"]
    max_tokens = config["token_budget"]["max_output_tokens"]

    print(f"[info] Extracting issues from execution plan using {model}...", flush=True)
    issues = extract_issues(plan_content, model, max_tokens)
    print(f"[info] Extracted {len(issues)} issue(s)")

    frontmatter = read_plan_frontmatter(args.plan_file)
    if frontmatter:
        print(f"[info] Plan authors: {frontmatter.get('authors', '(unknown)')}")

    created = create_github_issues(args.repo, issues, config, frontmatter)
    print(f"[info] Done. Created issues: {created}")


if __name__ == "__main__":
    main()
