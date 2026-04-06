#!/usr/bin/env python3
"""
write_code.py

Reads a GitHub Issue (title, body, comments, + affected files) and calls Claude Sonnet
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
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from github.GithubException import GithubException, UnknownObjectException

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
    parse_llm_json_dict,
    read_file_safe,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate code for a GitHub Issue using Claude Sonnet.")
    parser.add_argument("--issue-number", type=int, help="GitHub issue number (required unless --dry-run)")
    parser.add_argument("--repo", help="owner/repo-name (required unless --dry-run)")
    parser.add_argument("--context-dir", required=True)
    # Dry-run mode: skip all GitHub operations, accept issue inline for local LLM testing
    parser.add_argument("--dry-run", action="store_true", help="Skip GitHub; print LLM response to stdout")
    parser.add_argument("--issue-title", default="Add health check endpoint", help="Issue title (dry-run only)")
    parser.add_argument(
        "--issue-body",
        default=(
            "Implement a GET /health endpoint that returns {\"status\": \"ok\"}.\n\n"
            "Affected files:\n- `backend/app/main.py` (modify)"
        ),
        help="Issue body text (dry-run only)",
    )
    parser.add_argument(
        "--issue-comments",
        default="",
        help="Issue comments text, same shape as format_issue_comments output (dry-run only)",
    )
    args = parser.parse_args()
    if not args.dry_run and (not args.issue_number or not args.repo):
        parser.error("--issue-number and --repo are required unless --dry-run is set")
    if args.issue_comments and not args.dry_run:
        parser.error("--issue-comments is only valid with --dry-run")
    return args


def extract_affected_files(issue_body: str) -> list[str]:
    """Parse affected file paths from the issue body (lines under 'Affected files:')."""
    paths: list[str] = []
    in_section = False
    seen: set[str] = set()
    for line in issue_body.splitlines():
        if "affected files" in line.lower():
            in_section = True
            continue
        if in_section:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#") or (stripped.endswith(":") and not stripped.startswith("-")):
                in_section = False
                continue

            content = stripped.lstrip("-").strip()
            backtick_match = re.search(r"`([^`]+)`", content)
            candidate = backtick_match.group(1).strip() if backtick_match else content
            candidate = candidate.split("(")[0].strip()

            # Accept nested and root-level paths (e.g., README.md).
            if candidate and " " not in candidate and not candidate.startswith("#"):
                if candidate not in seen:
                    seen.add(candidate)
                    paths.append(candidate)
    return paths


def format_issue_comments(issue: Any) -> tuple[str, int]:
    """Build markdown for all issue comments (oldest first). Returns (text, count)."""
    try:
        comments = list(issue.get_comments())
    except Exception as e:
        print(f"[warn] Could not load issue comments: {e}", file=sys.stderr)
        return "", 0
    parts: list[str] = []
    for c in comments:
        author = getattr(c.user, "login", None) or "unknown"
        when = getattr(c, "created_at", None)
        when_s = when.isoformat() if when is not None else ""
        body = (c.body or "").strip()
        header = f"### @{author}"
        if when_s:
            header += f" ({when_s})"
        parts.append(f"{header}\n{body}")
    text = "\n\n".join(parts) if parts else ""
    return text, len(comments)


def build_user_message(
    issue_title: str,
    issue_body: str,
    issue_comments_markdown: str,
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

    comments_section = (
        issue_comments_markdown.strip()
        if issue_comments_markdown.strip()
        else "_No comments on this issue._"
    )

    message = f"""# Task to Implement

## Title
{issue_title}

## Description & Acceptance Criteria
{issue_body}

## Issue discussion (comments)
{comments_section}

## Current File Contents
{files_section}

## Project Context
{context_docs}
"""
    return apply_token_budget(message, max_context)


def parse_code_response(raw: str) -> dict[str, Any]:
    """Extract JSON object from Claude's response (handles fences, prose, split blocks)."""
    return parse_llm_json_dict(raw)


def apply_files_to_branch(
    repo: Any,
    branch_name: str,
    files: list[dict[str, str]],
    base_sha: str,
    pr_title: str,
) -> None:
    """Create or reset branch, then commit all file changes."""
    ref_name = f"heads/{branch_name}"
    try:
        existing_ref = repo.get_git_ref(ref_name)
        # Re-run safe: reset branch to current dev head so regeneration is idempotent.
        existing_ref.edit(sha=base_sha, force=True)
        print(f"[info] Reusing existing branch {branch_name!r} (reset to base)", flush=True)
    except UnknownObjectException:
        repo.create_git_ref(ref=f"refs/{ref_name}", sha=base_sha)
        print(f"[info] Created new branch {branch_name!r}", flush=True)

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


def find_existing_open_pr(repo: Any, branch_name: str, base_branch: str) -> Any | None:
    """Return an existing open PR for head branch -> base branch, if any."""
    owner = repo.owner.login
    pulls = repo.get_pulls(state="open", head=f"{owner}:{branch_name}", base=base_branch)
    for pr in pulls:
        return pr
    return None


def _is_backend_touched(files: list[dict[str, str]]) -> bool:
    return any((f.get("path") or "").startswith("backend/") for f in files)


def _is_frontend_touched(files: list[dict[str, str]]) -> bool:
    return any((f.get("path") or "").startswith("frontend/") for f in files)


def _run_check(cmd: list[str], cwd: Path) -> tuple[bool, str]:
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode == 0, output


def _apply_generated_files_locally(
    repo_root: Path, files: list[dict[str, str]]
) -> list[tuple[Path, bool, str]]:
    """Apply generated files to local checkout and return restore state."""
    backups: list[tuple[Path, bool, str]] = []
    for file_change in files:
        rel = file_change["path"]
        action = file_change["action"]
        content = file_change.get("content", "")
        target = (repo_root / rel).resolve()
        repo_resolved = repo_root.resolve()
        if repo_resolved not in [target, *target.parents]:
            die(f"Refusing to write outside repo: {rel}")

        existed = target.exists()
        old_content = target.read_text() if existed else ""
        backups.append((target, existed, old_content))

        if action == "delete":
            if existed:
                target.unlink()
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
    return backups


def _restore_local_files(backups: list[tuple[Path, bool, str]]) -> None:
    for target, existed, old_content in reversed(backups):
        if existed:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(old_content)
        else:
            if target.exists():
                target.unlink()


def run_generated_code_checks(repo_root: Path, files: list[dict[str, str]]) -> str | None:
    """Run CI-like checks on generated code before opening/updating PR.

    Returns:
        None when all checks pass, otherwise a compact error string.
    """
    backend_touched = _is_backend_touched(files)
    frontend_touched = _is_frontend_touched(files)
    if not backend_touched and not frontend_touched:
        print("[info] No backend/frontend files touched; skipping code checks.", flush=True)
        return None

    checks: list[tuple[list[str], Path, str]] = []
    if backend_touched:
        backend_dir = repo_root / "backend"
        checks += [
            (["uv", "sync", "--frozen"], backend_dir, "backend deps"),
            (["uv", "run", "ruff", "check", "."], backend_dir, "backend lint"),
            (["uv", "run", "mypy", "app"], backend_dir, "backend type-check"),
            (["uv", "run", "pytest"], backend_dir, "backend tests"),
        ]
    if frontend_touched:
        frontend_dir = repo_root / "frontend"
        checks += [
            (["npm", "ci"], frontend_dir, "frontend deps"),
            (["npm", "run", "lint"], frontend_dir, "frontend lint"),
            (["npm", "run", "test"], frontend_dir, "frontend tests"),
        ]

    for cmd, cwd, label in checks:
        print(f"[info] Running {label}: {' '.join(cmd)} (cwd={cwd})", flush=True)
        ok, output = _run_check(cmd, cwd)
        if not ok:
            tail = output[-4000:] if output else "(no output)"
            return f"{label} failed.\n\n{tail}"
    return None


def main() -> None:
    args = parse_args()
    repo_root = find_repo_root()

    config = load_pipeline_config(repo_root)
    check_circuit_breaker(config)

    context_dir = Path(args.context_dir)
    system_prompt = load_system_prompt(context_dir, "SYSTEM_PROMPT_CODER.md")
    model = config["models"]["coder"]
    max_context = config["token_budget"]["max_context_tokens"]
    max_output = config["token_budget"]["max_output_tokens"]

    issue_comments_markdown = ""

    if args.dry_run:
        issue_title = args.issue_title
        issue_body = args.issue_body
        issue_comments_markdown = args.issue_comments or ""
        print(f"[dry-run] Using inline issue: {issue_title!r}")
        if issue_comments_markdown.strip():
            print("[dry-run] Including --issue-comments in prompt.", flush=True)
    else:
        gh = github_client()
        repo = get_repo(gh, args.repo)
        issue = repo.get_issue(args.issue_number)
        issue_title = issue.title
        issue_body = issue.body or ""
        issue_comments_markdown, n_comments = format_issue_comments(issue)
        print(f"[info] Processing issue #{args.issue_number}: {issue_title}")
        if issue_comments_markdown:
            print(f"[info] Loaded {n_comments} issue comment(s) into prompt.", flush=True)

    combined_for_paths = issue_body
    if issue_comments_markdown.strip():
        combined_for_paths = f"{issue_body}\n\n{issue_comments_markdown}"
    affected_files = extract_affected_files(combined_for_paths)
    print(f"[info] Affected files: {affected_files}")

    context_docs = load_context_docs(context_dir, affected_paths=affected_files)

    user_message = build_user_message(
        issue_title=issue_title,
        issue_body=issue_body,
        issue_comments_markdown=issue_comments_markdown,
        affected_files=affected_files,
        repo_root=repo_root,
        context_docs=context_docs,
        max_context=max_context,
    )

    print(f"[info] Calling {model} to generate code...", flush=True)
    client = anthropic_client()
    raw_response = call_claude(
        client=client,
        model=model,
        system=system_prompt,
        user=user_message,
        max_tokens=max_output,
    )

    if args.dry_run:
        print("\n[dry-run] === LLM RESPONSE ===")
        print(raw_response)
        print("[dry-run] === END ===")
        return

    try:
        result = parse_code_response(raw_response)
    except SystemExit:
        print("[warn] Invalid JSON response; retrying with strict JSON-only instruction...", flush=True)
        repair_user_message = (
            user_message
            + "\n\nIMPORTANT: Re-output your previous answer as valid JSON only. "
            + "No prose, no markdown fences, no explanation."
        )
        raw_response = call_claude(
            client=client,
            model=model,
            system=system_prompt,
            user=repair_user_message,
            max_tokens=max_output,
        )
        result = parse_code_response(raw_response)
    branch_name: str = result["branch_name"]
    pr_title: str = result["pr_title"]
    pr_body: str = result["pr_body"]
    files: list[dict[str, str]] = result["files"]

    # Validate generated code against CI-style checks before PR creation/update.
    def validate_files(candidate_files: list[dict[str, str]]) -> str | None:
        backups: list[tuple[Path, bool, str]] = []
        try:
            backups = _apply_generated_files_locally(repo_root, candidate_files)
            return run_generated_code_checks(repo_root, candidate_files)
        finally:
            if backups:
                _restore_local_files(backups)

    check_error = validate_files(files)
    if check_error:
        print("[warn] Generated code failed checks; attempting one LLM repair pass...", flush=True)
        repair_user_message = (
            user_message
            + "\n\nThe previous generated patch failed CI-style checks.\n"
            + "Regenerate the FULL JSON response (all fields and full file contents) with fixes.\n"
            + "Only output JSON.\n\n"
            + "Failed check output (trimmed):\n"
            + check_error
        )
        repair_raw = call_claude(
            client=client,
            model=model,
            system=system_prompt,
            user=repair_user_message,
            max_tokens=max_output,
        )
        repaired = parse_code_response(repair_raw)
        branch_name = repaired["branch_name"]
        pr_title = repaired["pr_title"]
        pr_body = repaired["pr_body"]
        files = repaired["files"]
        check_error = validate_files(files)
        if check_error:
            die(f"Generated code failed checks after repair attempt.\n\n{check_error}")

    dev_branch = config["branches"]["dev"]
    base = repo.get_branch(dev_branch)
    base_sha = base.commit.sha

    print(f"[info] Creating branch {branch_name!r} from {dev_branch}...")
    apply_files_to_branch(repo, branch_name, files, base_sha, pr_title)

    ai_label = config["labels"]["ai_generated"]
    existing_pr = find_existing_open_pr(repo, branch_name, dev_branch)
    if existing_pr:
        pr = existing_pr
        print(f"[info] Reusing existing open PR: {pr.html_url}")
        try:
            pr.edit(title=pr_title, body=pr_body + f"\n\nCloses #{args.issue_number}")
        except GithubException:
            pass
    else:
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
