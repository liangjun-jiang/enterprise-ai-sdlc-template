#!/usr/bin/env python3
"""
write_code.py

Reads a GitHub Issue (title, body, comments, + affected files) and calls Claude Sonnet
to generate code. Creates/resets a branch and commits files.

Usage:
    python write_code.py \\
        --issue-number 42 \\
        --repo owner/repo-name \\
        --context-dir ai-sdlc-docs/context
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

from github.GithubException import UnknownObjectException

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
    load_system_prompt,
    parse_llm_json_dict_prefer_keys,
    read_file_safe,
)

FILE_PLAN_SYSTEM_PROMPT = """\
Return ONLY valid JSON with this exact shape:
{
  "files": [
    { "path": "repo/relative/path.ext", "action": "create|modify|delete" }
  ]
}

Rules:
- No prose, no markdown fences.
- Keep scope minimal and aligned to the implementation plan.
- Include tests for new behavior.
- For delete actions, only include when explicitly required.
"""

FILE_CONTENT_SYSTEM_PROMPT = """\
Return ONLY valid JSON with this exact shape:
{
  "content": "<full file content>"
}

Rules:
- No prose, no markdown fences.
- Output full final file content for the target file.
- Follow coding and security standards.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate code for a GitHub Issue using Claude Sonnet.")
    parser.add_argument("--issue-number", type=int, help="GitHub issue number (required unless --dry-run)")
    parser.add_argument("--repo", help="owner/repo-name (required unless --dry-run)")
    parser.add_argument("--context-dir", required=True)
    parser.add_argument("--branch-name", default="", help="Deterministic branch name from workflow")
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
    implementation_plan_markdown: str,
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
    plan_section = (
        implementation_plan_markdown.strip()
        if implementation_plan_markdown.strip()
        else "_No approved implementation plan found in issue thread._"
    )

    message = f"""# Task to Implement

## Title
{issue_title}

## Description & Acceptance Criteria
{issue_body}

## Issue discussion (comments)
{comments_section}

## Approved Implementation Plan
{plan_section}

## Current File Contents
{files_section}

## Project Context
{context_docs}
"""
    return apply_token_budget(message, max_context)


def parse_code_response(raw: str) -> dict[str, Any]:
    """Extract JSON object from Claude's response, preferring codegen-shaped objects."""
    return parse_llm_json_dict_prefer_keys(
        raw, preferred_keys=["files", "branch_name", "pr_title", "pr_body"]
    )


def _normalize_file_plan(result: dict[str, Any]) -> list[dict[str, str]]:
    files_raw = result.get("files")
    if not isinstance(files_raw, list) or not files_raw:
        die("Model output must include a non-empty 'files' array.")

    files: list[dict[str, str]] = []
    seen_paths: set[str] = set()
    for i, item in enumerate(files_raw, start=1):
        if not isinstance(item, dict):
            die(f"Model output files[{i}] is not an object.")
        path = str(item.get("path") or "").strip()
        action = str(item.get("action") or "").strip().lower()
        if not path:
            die(f"Model output files[{i}] is missing 'path'.")
        if action not in {"create", "modify", "delete"}:
            die(f"Model output files[{i}] has invalid 'action': {action!r}.")
        if path in seen_paths:
            continue
        seen_paths.add(path)
        files.append({"path": path, "action": action})
    return files


def _normalize_codegen_result(
    result: dict[str, Any],
    *,
    issue_number: int | None,
    issue_title: str,
) -> tuple[str, str, str, list[dict[str, str]]]:
    """Normalize model JSON and provide safe fallbacks for optional fields."""
    issue_slug = re.sub(r"[^a-z0-9]+", "-", issue_title.lower()).strip("-")[:48] or "work-item"
    default_branch = f"ai/issue-{issue_number or 'local'}-{issue_slug}"
    branch_name = str(result.get("branch_name") or default_branch).strip() or default_branch
    pr_title = str(result.get("pr_title") or f"Implement issue #{issue_number or 'local'}: {issue_title}").strip()
    pr_body = str(result.get("pr_body") or "Automated update generated by AI Code Writer.").strip()

    files_raw = result.get("files")
    if not isinstance(files_raw, list) or not files_raw:
        die("Model output must include a non-empty 'files' array.")

    files: list[dict[str, str]] = []
    for i, item in enumerate(files_raw, start=1):
        if not isinstance(item, dict):
            die(f"Model output files[{i}] is not an object.")
        path = str(item.get("path") or "").strip()
        action = str(item.get("action") or "").strip().lower()
        content = str(item.get("content") or "")
        if not path:
            die(f"Model output files[{i}] is missing 'path'.")
        if action not in {"create", "modify", "delete"}:
            die(f"Model output files[{i}] has invalid 'action': {action!r}.")
        files.append({"path": path, "action": action, "content": content})

    return branch_name, pr_title, pr_body, files


def extract_implementation_plan(issue_body: str, issue_comments_markdown: str) -> str:
    """Extract latest planner-authored implementation plan from issue body/comments."""
    text = f"{issue_body}\n\n{issue_comments_markdown}".strip()
    if not text:
        return ""
    pattern = re.compile(
        r"(<!--\s*ai-implementation-plan\s*-->.*?)(?=\n<!--\s*ai-implementation-plan\s*-->|$)",
        re.IGNORECASE | re.DOTALL,
    )
    matches = pattern.findall(text)
    if matches:
        return matches[-1].strip()
    return ""


def _call_json_with_repair(
    *,
    client: Any,
    model: str,
    system: str,
    user: str,
    max_tokens: int,
    preferred_keys: list[str],
    repair_suffix: str,
) -> dict[str, Any]:
    raw = call_claude(
        client=client,
        model=model,
        system=system,
        user=user,
        max_tokens=max_tokens,
    )
    try:
        return parse_llm_json_dict_prefer_keys(raw, preferred_keys=preferred_keys)
    except SystemExit:
        repaired_user = user + "\n\n" + repair_suffix
        repaired_raw = call_claude(
            client=client,
            model=model,
            system=system,
            user=repaired_user,
            max_tokens=max_tokens,
        )
        return parse_llm_json_dict_prefer_keys(repaired_raw, preferred_keys=preferred_keys)


def _allows_empty_file(path: str) -> bool:
    name = Path(path).name
    return name in {"__init__.py", ".gitkeep", ".keep"}


def apply_files_to_branch(
    repo: Any,
    branch_name: str,
    files: list[dict[str, str]],
    base_sha: str,
    commit_subject: str,
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
            try:
                existing = repo.get_contents(path, ref=branch_name)
                repo.update_file(
                    path,
                    f"{'feat' if action == 'create' else 'fix'}: {commit_subject}",
                    content,
                    existing.sha,
                    branch=branch_name,
                )
            except Exception:
                repo.create_file(path, f"feat: {commit_subject}", content, branch=branch_name)

        print(f"[info] {action}: {path}")


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

    context_dir = Path(args.context_dir)
    system_prompt = load_system_prompt(context_dir, "SYSTEM_PROMPT_CODER.md")
    model = config["models"]["coder"]
    max_context = config["token_budget"]["max_context_tokens"]
    max_output = config["token_budget"]["max_output_tokens"]

    issue_comments_markdown = ""
    implementation_plan_markdown = ""

    if args.dry_run:
        issue_title = args.issue_title
        issue_body = args.issue_body
        issue_comments_markdown = args.issue_comments or ""
        implementation_plan_markdown = extract_implementation_plan(issue_body, issue_comments_markdown)
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
        implementation_plan_markdown = extract_implementation_plan(issue_body, issue_comments_markdown)
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
        implementation_plan_markdown=implementation_plan_markdown,
        affected_files=affected_files,
        repo_root=repo_root,
        context_docs=context_docs,
        max_context=max_context,
    )

    print(f"[info] Calling {model} to generate file plan...", flush=True)
    client = anthropic_client()
    plan_user_message = (
        user_message
        + "\n\nOutput only JSON with key `files` and each item containing `path` and `action`."
    )
    file_plan_result = _call_json_with_repair(
        client=client,
        model=model,
        system=FILE_PLAN_SYSTEM_PROMPT,
        user=plan_user_message,
        max_tokens=max_output,
        preferred_keys=["files"],
        repair_suffix=(
            "IMPORTANT: Re-output your previous answer as valid JSON only. "
            "No prose, no markdown fences, no explanation. "
            "Top-level JSON must include key `files`."
        ),
    )
    file_plan = _normalize_file_plan(file_plan_result)
    print(f"[info] Planned file changes: {len(file_plan)}", flush=True)

    if args.dry_run:
        print("\n[dry-run] === FILE PLAN ===")
        print(file_plan_result)
        print("[dry-run] === END FILE PLAN ===")
        rendered_files: list[dict[str, str]] = []
        for file_change in file_plan:
            path = file_change["path"]
            action = file_change["action"]
            if action == "delete":
                rendered_files.append({"path": path, "action": action, "content": ""})
                continue
            existing_content = read_file_safe(repo_root / path)
            file_user = (
                f"{user_message}\n\n"
                f"## Target File\nPath: {path}\nAction: {action}\n\n"
                f"## Existing Content\n```\n{existing_content}\n```"
            )
            content_obj = _call_json_with_repair(
                client=client,
                model=model,
                system=FILE_CONTENT_SYSTEM_PROMPT,
                user=file_user,
                max_tokens=max_output,
                preferred_keys=["content"],
                repair_suffix=(
                    "IMPORTANT: Re-output as valid JSON only: "
                    '{"content":"<full file content>"}'
                ),
            )
            rendered_files.append(
                {"path": path, "action": action, "content": str(content_obj.get("content") or "")}
            )
        print("\n[dry-run] === GENERATED FILES ===")
        print({"files": rendered_files})
        print("[dry-run] === END ===")
        return

    generated_files: list[dict[str, str]] = []
    for file_change in file_plan:
        path = file_change["path"]
        action = file_change["action"]
        if action == "delete":
            generated_files.append({"path": path, "action": action, "content": ""})
            continue

        existing_content = read_file_safe(repo_root / path)
        file_user_message = (
            f"{user_message}\n\n"
            f"## Target File\nPath: {path}\nAction: {action}\n\n"
            f"## Existing Content\n```\n{existing_content}\n```"
        )
        content_result = _call_json_with_repair(
            client=client,
            model=model,
            system=FILE_CONTENT_SYSTEM_PROMPT,
            user=file_user_message,
            max_tokens=max_output,
            preferred_keys=["content"],
            repair_suffix=(
                "IMPORTANT: Re-output as valid JSON only: "
                '{"content":"<full file content>"}'
            ),
        )
        content = str(content_result.get("content") or "")
        if action in {"create", "modify"} and not content.strip():
            if _allows_empty_file(path):
                content = ""
            else:
                # Semantic retry: JSON was valid, but content was empty for a file that
                # should generally have implementation text.
                semantic_retry_user = (
                    file_user_message
                    + "\n\nYour previous response had empty `content`. "
                    + "Return non-empty full file content in JSON: "
                    + '{"content":"<full file content>"}'
                )
                semantic_retry = _call_json_with_repair(
                    client=client,
                    model=model,
                    system=FILE_CONTENT_SYSTEM_PROMPT,
                    user=semantic_retry_user,
                    max_tokens=max_output,
                    preferred_keys=["content"],
                    repair_suffix=(
                        "IMPORTANT: Re-output as valid JSON only: "
                        '{"content":"<full file content>"}'
                    ),
                )
                content = str(semantic_retry.get("content") or "")
                if not content.strip():
                    die(f"Model returned empty content for {action} action on {path}")
        generated_files.append({"path": path, "action": action, "content": content})

    parsed_branch_name = f"ai/issue-{args.issue_number or 'local'}-{re.sub(r'[^a-z0-9]+', '-', issue_title.lower()).strip('-')[:48] or 'work-item'}"
    branch_name: str = args.branch_name.strip() or parsed_branch_name
    pr_title = f"Implement issue #{args.issue_number or 'local'}: {issue_title}"
    pr_body = "Automated update generated by AI Code Writer."
    files = generated_files

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
        parsed_branch_name, pr_title, pr_body, files = _normalize_codegen_result(
            repaired,
            issue_number=args.issue_number,
            issue_title=issue_title,
        )
        branch_name = args.branch_name.strip() or parsed_branch_name
        check_error = validate_files(files)
        if check_error:
            die(f"Generated code failed checks after repair attempt.\n\n{check_error}")

    dev_branch = config["branches"]["dev"]
    base = repo.get_branch(dev_branch)
    base_sha = base.commit.sha

    print(f"[info] Creating branch {branch_name!r} from {dev_branch}...")
    apply_files_to_branch(repo, branch_name, files, base_sha, pr_title)

    print(f"[info] Code committed to branch: {branch_name}")


if __name__ == "__main__":
    main()
