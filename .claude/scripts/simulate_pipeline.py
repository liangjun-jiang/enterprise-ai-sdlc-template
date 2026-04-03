#!/usr/bin/env python3
"""
simulate_pipeline.py

Local end-to-end simulation of the AI-SDLC pipeline, from PRD to GitHub Issues.
Each step pauses for the named human role to review and approve before proceeding.

Usage (from repo root):
    uv run --project .claude/scripts python .claude/scripts/simulate_pipeline.py
    uv run --project .claude/scripts python .claude/scripts/simulate_pipeline.py --from-step 3
    uv run --project .claude/scripts python .claude/scripts/simulate_pipeline.py --reset

Steps:
    1  Setup            — Create pipeline branches
    2  PRD              — Product Owner: James Smith
    3  Roadmap          — Project Manager: Heather Williams
    4  Milestones       — Project Manager: Heather Williams
    5  Feature Plans    — Tech Lead: Liangjun Jiang
    6  Execution Plans  — Tech Lead: Liangjun Jiang
    7  GitHub Issues    — Tech Lead: Liangjun Jiang  (requires GITHUB_TOKEN + GITHUB_REPO)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# ── Constants ──────────────────────────────────────────────────────────────────

ROLES = {
    "product_owner": "James Smith",
    "project_manager": "Heather Williams",
    "tech_lead": "Liangjun Jiang",
    "developer": "Vincent Cao",
    "tester": "Sindhu Kandula",
}

SCRIPTS_DIR = Path(__file__).parent
STATE_FILE = ".simulate_state.json"

# ANSI colours
R = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RED = "\033[31m"


# ── Repo root ──────────────────────────────────────────────────────────────────

def find_repo_root() -> Path:
    p = Path(__file__).resolve()
    while p != p.parent:
        if (p / ".git").exists():
            return p
        p = p.parent
    raise RuntimeError("Not inside a git repo")


REPO_ROOT = find_repo_root()


# ── Environment ────────────────────────────────────────────────────────────────

def load_env() -> None:
    env_path = SCRIPTS_DIR / ".env"
    if not env_path.exists():
        print(f"{RED}ERROR: {env_path} not found.\nCopy .env.example → .env and fill in values.{R}")
        sys.exit(1)
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


# ── Git helpers ────────────────────────────────────────────────────────────────

def git(args: list[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    kwargs: dict[str, Any] = {"cwd": REPO_ROOT}
    if capture:
        kwargs["capture_output"] = True
        kwargs["text"] = True
    result = subprocess.run(["git"] + args, **kwargs)
    if check and result.returncode != 0:
        print(f"{RED}git {' '.join(args)} failed{R}")
        sys.exit(1)
    return result


def current_branch() -> str:
    return git(["rev-parse", "--abbrev-ref", "HEAD"], capture=True).stdout.strip()


def branch_exists(name: str) -> bool:
    r = git(["show-ref", "--verify", "--quiet", f"refs/heads/{name}"], check=False)
    return r.returncode == 0


def _sanitize_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().lower()).strip("-")
    return slug or "work"


def start_feature_branch(target_branch: str, step_key: str, context: str | None = None) -> tuple[str, str, bool]:
    """Checkout target branch and create a feature branch for this step."""
    orig = current_branch()

    stash_out = git(["stash", "push", "-u", "-m", "sim_stash"], check=False, capture=True).stdout
    stashed = "No local changes" not in stash_out

    git(["checkout", target_branch])

    base = f"sim/{_sanitize_slug(step_key)}"
    if context:
        base = f"{base}-{_sanitize_slug(context)}"
    feature_branch = base
    suffix = 2
    while branch_exists(feature_branch):
        feature_branch = f"{base}-{suffix}"
        suffix += 1

    git(["checkout", "-b", feature_branch])
    print(f"  {CYAN}→ Working in feature branch: {feature_branch}{R}")
    return orig, feature_branch, stashed


def restore_original_branch(orig: str, stashed: bool) -> None:
    git(["checkout", orig])
    if stashed:
        git(["stash", "pop"])


def commit_and_merge_feature_branch(
    target_branch: str,
    feature_branch: str,
    changed_paths: list[str],
    commit_msg: str,
    author_name: str,
) -> None:
    """Commit approved changes on feature branch, then merge into target branch."""
    for rel in changed_paths:
        git(["add", rel], check=False)

    nothing_staged = git(["diff", "--cached", "--quiet"], check=False).returncode == 0
    if nothing_staged:
        print(f"  {DIM}(nothing new to commit on '{feature_branch}'){R}")
        return

    email = author_name.lower().replace(" ", ".") + "@team.local"
    env = {**os.environ, "GIT_AUTHOR_NAME": author_name, "GIT_AUTHOR_EMAIL": email,
           "GIT_COMMITTER_NAME": author_name, "GIT_COMMITTER_EMAIL": email}
    subprocess.run(["git", "commit", "-m", commit_msg], cwd=REPO_ROOT, env=env, check=True)
    print(f"  {GREEN}✓ Committed on '{feature_branch}'{R}")

    git(["checkout", target_branch])
    git(["merge", "--no-ff", feature_branch, "-m", f"merge: {feature_branch} into {target_branch}"])
    print(f"  {GREEN}✓ Merged '{feature_branch}' -> '{target_branch}'{R}")
    git(["branch", "-d", feature_branch], check=False)


# ── Script runner ──────────────────────────────────────────────────────────────

def run_script(script_name: str, extra_args: list[str]) -> bool:
    cmd = ["uv", "run", "--project", str(SCRIPTS_DIR),
           "python", str(SCRIPTS_DIR / script_name)] + extra_args
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    return result.returncode == 0


# ── State ──────────────────────────────────────────────────────────────────────

def load_state() -> dict[str, Any]:
    p = REPO_ROOT / STATE_FILE
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {"completed": [], "data": {}}


def stamp_approval_frontmatter(content: str, approver_name: str) -> str:
    """Set/replace frontmatter approver and approved_at timestamp."""
    approved_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    fm_match = re.match(r"^---\n(.*?)\n---\n?", content, flags=re.DOTALL)

    if fm_match:
        fm = fm_match.group(1)
        body = content[fm_match.end() :]

        if re.search(r"(?m)^approvers:\s*$", fm):
            fm = re.sub(
                r"(?ms)^approvers:\s*\n(?:[ \t]+-[ \t]*[^\n]*\n)*",
                f'approvers:\n  - "{approver_name}"\n',
                fm,
                count=1,
            )
        else:
            fm += f'\napprovers:\n  - "{approver_name}"\n'

        if re.search(r"(?m)^approved_at:\s*", fm):
            fm = re.sub(r'(?m)^approved_at:\s*.*$', f'approved_at: "{approved_at}"', fm, count=1)
        else:
            fm += f'\napproved_at: "{approved_at}"\n'

        return f"---\n{fm.strip()}\n---\n{body.lstrip()}"

    return (
        f'---\napprovers:\n  - "{approver_name}"\napproved_at: "{approved_at}"\n---\n\n'
        f"{content}"
    )


def save_state(state: dict[str, Any]) -> None:
    (REPO_ROOT / STATE_FILE).write_text(json.dumps(state, indent=2))


# ── Display helpers ────────────────────────────────────────────────────────────

def header(title: str) -> None:
    bar = "═" * 62
    print(f"\n{BOLD}{CYAN}{bar}{R}")
    print(f"{BOLD}{CYAN}  {title}{R}")
    print(f"{BOLD}{CYAN}{bar}{R}")


def show_file(path: Path, max_lines: int = 55) -> None:
    if not path.exists():
        print(f"  {RED}(file not found: {path}){R}")
        return
    lines = path.read_text().splitlines()
    rel = path.relative_to(REPO_ROOT)
    print(f"\n{DIM}── {rel} {'─' * max(0, 56 - len(str(rel)))}─{R}")
    for line in lines[:max_lines]:
        print(f"  {line}")
    if len(lines) > max_lines:
        print(f"  {DIM}... ({len(lines) - max_lines} more lines — open the file to see all){R}")
    print(f"{DIM}{'─' * 60}{R}")


def gate(role_key: str, artifact: str) -> bool:
    """Print a review gate prompt; return True if approved."""
    name = ROLES[role_key]
    label = role_key.replace("_", " ").title()
    print(f"\n{YELLOW}┌─ Review gate {'─' * 44}┐{R}")
    print(f"{YELLOW}│  Role:     {BOLD}{label}{R}{YELLOW}  ({name}){R}")
    print(f"{YELLOW}│  Artifact: {artifact}{R}")
    print(f"{YELLOW}└{'─' * 58}┘{R}")
    ans = input(f"  {BOLD}[{name}] Approve? [Y/n] {R}").strip().lower()
    return ans in ("", "y", "yes")


# ── Steps ──────────────────────────────────────────────────────────────────────

def step_setup(state: dict[str, Any]) -> None:
    if "setup" in state["completed"]:
        print(f"  {DIM}[skip] branches already created{R}")
        return

    header("STEP 1 — Create pipeline branches")
    for branch in ["prd", "roadmap", "milestone", "plan", "plan-execution", "dev"]:
        if branch_exists(branch):
            print(f"  {DIM}'{branch}' already exists{R}")
        else:
            git(["checkout", "-b", branch])
            git(["checkout", "main"])
            print(f"  {GREEN}✓ Created '{branch}'{R}")

    state["completed"].append("setup")
    save_state(state)


def step_prd(state: dict[str, Any]) -> None:
    if "prd" in state["completed"]:
        print(f"  {DIM}[skip] PRD already approved{R}")
        return

    default_prd = state["data"].get("prd_file", "docs/prd/prd-000-dashboard.md")
    entered = input(f"  Enter PRD path [default: {default_prd}]: ").strip()
    prd_rel = entered or default_prd
    prd_file = REPO_ROOT / prd_rel
    if not prd_file.exists():
        print(f"{RED}  PRD file not found: {prd_rel}{R}")
        sys.exit(1)

    header(f"STEP 2 — PRD Review  [{ROLES['product_owner']}]")
    orig, feature_branch, stashed = start_feature_branch("prd", "prd", prd_file.stem)
    show_file(prd_file)

    if not gate("product_owner", prd_rel):
        restore_original_branch(orig, stashed)
        print(f"{RED}  PRD rejected — stopping.{R}")
        sys.exit(0)

    approved_prd = stamp_approval_frontmatter(prd_file.read_text(), ROLES["product_owner"])
    prd_file.write_text(approved_prd)
    print(f"  {GREEN}✓ Stamped approver + approved_at: {ROLES['product_owner']}{R}")

    commit_and_merge_feature_branch(
        "prd",
        feature_branch,
        [prd_rel],
        f"feat: add {Path(prd_rel).name} (approved by James Smith)",
        ROLES["product_owner"],
    )
    restore_original_branch(orig, stashed)
    state["completed"].append("prd")
    state["data"]["prd_file"] = prd_rel
    save_state(state)


def step_roadmap(state: dict[str, Any]) -> None:
    if "roadmap" in state["completed"]:
        print(f"  {DIM}[skip] roadmap already approved{R}")
        return

    prd_rel = state["data"].get("prd_file", "docs/prd/prd-000-dashboard.md")
    prd_stem = Path(prd_rel).stem
    m = re.match(r"prd-(\d+)-", prd_stem)
    seq = m.group(1) if m else "000"
    roadmap_name = f"roadmap-{seq}-for-{prd_stem}.md"
    roadmap_path = REPO_ROOT / "docs" / "roadmap" / roadmap_name
    default_path = REPO_ROOT / "docs" / "roadmap" / "ROADMAP.md"

    header(f"STEP 3 — Roadmap  [{ROLES['project_manager']}]")
    orig, feature_branch, stashed = start_feature_branch("roadmap", "roadmap", prd_stem)

    if roadmap_path.exists():
        print(f"  {YELLOW}{roadmap_name} already exists — using existing file (skip LLM call).{R}")
        print(f"  To regenerate, delete docs/roadmap/{roadmap_name} and re-run.")
    else:
        print(f"  Generating {roadmap_name} from {Path(prd_rel).name} ...")
        if not run_script("prd_to_roadmap.py", [
            "--prd-file", prd_rel,
            "--context-dir", "docs/context",
            "--local",
        ]):
            restore_original_branch(orig, stashed)
            print(f"{RED}  prd_to_roadmap.py failed — stopping.{R}")
            sys.exit(1)
        # prd_to_roadmap.py writes a hardcoded ROADMAP.md in local mode.
        # Move it into our deterministic simulation naming convention.
        if not roadmap_path.exists() and default_path.exists():
            roadmap_path.parent.mkdir(parents=True, exist_ok=True)
            default_path.replace(roadmap_path)
            print(f"  {GREEN}✓ Renamed ROADMAP.md -> {roadmap_name}{R}")

    show_file(roadmap_path)
    if not gate("project_manager", f"docs/roadmap/{roadmap_name}"):
        restore_original_branch(orig, stashed)
        print(f"{RED}  Roadmap rejected — stopping.{R}")
        sys.exit(0)

    approved = stamp_approval_frontmatter(roadmap_path.read_text(), ROLES["project_manager"])
    roadmap_path.write_text(approved)
    print(f"  {GREEN}✓ Stamped approver + approved_at: {ROLES['project_manager']}{R}")

    commit_and_merge_feature_branch(
        "roadmap",
        feature_branch,
        [f"docs/roadmap/{roadmap_name}"],
        f"feat: AI-generated {roadmap_name} from {prd_stem}",
        ROLES["project_manager"],
    )
    restore_original_branch(orig, stashed)
    state["completed"].append("roadmap")
    state["data"]["roadmap_file"] = f"docs/roadmap/{roadmap_name}"
    save_state(state)


def step_milestones(state: dict[str, Any]) -> None:
    if "milestones" in state["completed"]:
        print(f"  {DIM}[skip] milestones already approved{R}")
        return

    header(f"STEP 4 — Milestones  [{ROLES['project_manager']}]")
    orig, feature_branch, stashed = start_feature_branch("milestone", "milestone")
    ms_dir = REPO_ROOT / "docs" / "milestones"
    existing = sorted(ms_dir.glob("milestone-*.md"))
    roadmap_file = state["data"].get("roadmap_file", "docs/roadmap/ROADMAP.md")

    if existing:
        print(f"  {YELLOW}{len(existing)} milestone file(s) already exist — using them (skip LLM call).{R}")
        for f in existing:
            print(f"    • {f.name}")
        print(f"  To regenerate, delete docs/milestones/milestone-*.md and re-run.")
    else:
        print(f"  Generating milestone files from {Path(roadmap_file).name} ...")
        if not run_script("roadmap_to_milestones.py", [
            "--roadmap-file", roadmap_file,
            "--context-dir", "docs/context",
            "--local",
        ]):
            restore_original_branch(orig, stashed)
            print(f"{RED}  roadmap_to_milestones.py failed — stopping.{R}")
            sys.exit(1)
        existing = sorted(ms_dir.glob("milestone-*.md"))

    if not existing:
        restore_original_branch(orig, stashed)
        print(f"{RED}  No milestone files found after generation.{R}")
        sys.exit(1)

    for f in existing:
        show_file(f, max_lines=30)

    if not gate("project_manager", f"{len(existing)} milestone file(s) in docs/milestones/"):
        restore_original_branch(orig, stashed)
        print(f"{RED}  Milestones rejected — stopping.{R}")
        sys.exit(0)

    changed_paths: list[str] = []
    for f in existing:
        f.write_text(stamp_approval_frontmatter(f.read_text(), ROLES["project_manager"]))
        changed_paths.append(f"docs/milestones/{f.name}")
    print(f"  {GREEN}✓ Stamped approver + approved_at: {ROLES['project_manager']}{R}")

    commit_and_merge_feature_branch(
        "milestone",
        feature_branch,
        changed_paths,
        f"feat: AI-generated {len(existing)} milestone(s)",
        ROLES["project_manager"],
    )
    restore_original_branch(orig, stashed)
    state["completed"].append("milestones")
    state["data"]["milestone_files"] = [f.name for f in existing]
    save_state(state)


def step_plans(state: dict[str, Any]) -> None:
    if "plans" in state["completed"]:
        print(f"  {DIM}[skip] feature plans already approved{R}")
        return

    header(f"STEP 5 — Feature Plans  [{ROLES['tech_lead']}]")
    orig, feature_branch, stashed = start_feature_branch("plan", "plan")
    plans_dir = REPO_ROOT / "docs" / "plans"
    existing = sorted(plans_dir.glob("PLAN-[0-9]*.md"))

    if existing:
        print(f"  {YELLOW}{len(existing)} plan file(s) already exist — using them (skip LLM call).{R}")
        for f in existing:
            print(f"    • {f.name}")
        print(f"  To regenerate, delete docs/plans/PLAN-[0-9]*.md and re-run.")
    else:
        ms_files = state["data"].get("milestone_files") or \
            [f.name for f in sorted((REPO_ROOT / "docs" / "milestones").glob("milestone-*.md"))]
        for ms_name in ms_files:
            print(f"\n  Generating plans from {ms_name} ...")
            run_script("milestone_to_plans.py", [
                "--milestone-file", f"docs/milestones/{ms_name}",
                "--context-dir", "docs/context",
                "--local",
            ])
        existing = sorted(plans_dir.glob("PLAN-[0-9]*.md"))

    if not existing:
        restore_original_branch(orig, stashed)
        print(f"{RED}  No plan files found.{R}")
        sys.exit(1)

    for f in existing:
        show_file(f, max_lines=25)

    if not gate("tech_lead", f"{len(existing)} feature plan(s) in docs/plans/"):
        restore_original_branch(orig, stashed)
        print(f"{RED}  Plans rejected — stopping.{R}")
        sys.exit(0)

    changed_paths: list[str] = []
    for f in existing:
        f.write_text(stamp_approval_frontmatter(f.read_text(), ROLES["tech_lead"]))
        changed_paths.append(f"docs/plans/{f.name}")
    print(f"  {GREEN}✓ Stamped approver + approved_at: {ROLES['tech_lead']}{R}")

    commit_and_merge_feature_branch(
        "plan",
        feature_branch,
        changed_paths,
        f"feat: AI-generated {len(existing)} feature plan(s)",
        ROLES["tech_lead"],
    )
    restore_original_branch(orig, stashed)
    state["completed"].append("plans")
    state["data"]["plan_files"] = [f.name for f in existing]
    save_state(state)


def step_execution_plans(state: dict[str, Any]) -> None:
    if "execution_plans" in state["completed"]:
        print(f"  {DIM}[skip] execution plans already approved{R}")
        return

    plan_files: list[str] = state["data"].get("plan_files") or \
        [f.name for f in sorted((REPO_ROOT / "docs" / "plans").glob("PLAN-[0-9]*.md"))]

    header(f"STEP 6 — Execution Plans  [{ROLES['tech_lead']}]")
    orig, feature_branch, stashed = start_feature_branch("plan-execution", "plan-execution")
    print(f"  {len(plan_files)} plan(s) available:\n")
    for i, name in enumerate(plan_files, 1):
        slug = re.sub(r"^PLAN-\d+-", "", name[:-3]).strip()
        ep_name = f"EXECUTION-PLAN-{slug}.md"
        ep = REPO_ROOT / "docs" / "execution-plans" / ep_name
        marker = f" {DIM}(exists){R}" if ep.exists() else ""
        print(f"    {i:2d}. {name}{marker}")

    print(f"\n  Which plans to generate execution plans for?")
    print(f"  Enter numbers (e.g. 1,3,5), {BOLD}all{R}, or {BOLD}new{R} (skip existing): ", end="")
    sel = input().strip().lower()

    if sel in ("all", ""):
        selected = plan_files
    elif sel == "new":
        selected = [
            n for n in plan_files
            if not (REPO_ROOT / "docs" / "execution-plans" /
                    f"EXECUTION-PLAN-{re.sub(r'^PLAN-\\d+-', '', n[:-3]).strip()}.md").exists()
        ]
    else:
        idxs = [int(x.strip()) - 1 for x in sel.split(",") if x.strip().isdigit()]
        selected = [plan_files[i] for i in idxs if 0 <= i < len(plan_files)]

    if not selected:
        restore_original_branch(orig, stashed)
        print(f"{RED}  Nothing selected — stopping.{R}")
        sys.exit(0)

    print(f"\n  Will process {len(selected)} plan(s).")
    generated: list[Path] = []
    exec_to_plan: dict[str, str] = {}

    for plan_name in selected:
        slug = re.sub(r"^PLAN-\d+-", "", plan_name[:-3]).strip()
        plan_path = f"docs/plans/{plan_name}"
        output_path = f"docs/execution-plans/EXECUTION-PLAN-{slug}.md"
        abs_output = REPO_ROOT / output_path

        if abs_output.exists():
            print(f"\n  {YELLOW}Execution plan for '{slug}' already exists — using it.{R}")
        else:
            print(f"\n  {BOLD}Generating execution plan for '{slug}'...{R}")
            if not run_script("generate_execution_plan.py", [
                "--plan-file", plan_path,
                "--context-dir", "docs/context",
                "--output-file", output_path,
            ]):
                print(f"  {RED}  Failed for {plan_name} — skipping.{R}")
                continue

        show_file(abs_output, max_lines=35)
        if not gate("tech_lead", output_path):
            print(f"  {YELLOW}  Rejected — skipping {plan_name}.{R}")
            continue

        abs_output.write_text(stamp_approval_frontmatter(abs_output.read_text(), ROLES["tech_lead"]))
        generated.append(abs_output)
        exec_to_plan[output_path] = plan_path

    if not generated:
        restore_original_branch(orig, stashed)
        print(f"{RED}  No execution plans approved.{R}")
        sys.exit(0)

    commit_and_merge_feature_branch(
        "plan-execution",
        feature_branch,
        [str(p.relative_to(REPO_ROOT)) for p in generated],
        f"feat: AI-generated {len(generated)} execution plan(s)",
        ROLES["tech_lead"],
    )
    restore_original_branch(orig, stashed)
    state["completed"].append("execution_plans")
    state["data"]["execution_plans"] = [str(p.relative_to(REPO_ROOT)) for p in generated]
    state["data"]["exec_to_plan"] = exec_to_plan
    save_state(state)


def step_issues(state: dict[str, Any]) -> None:
    if "issues" in state["completed"]:
        print(f"  {DIM}[skip] issues already created{R}")
        return

    repo = os.environ.get("GITHUB_REPO", "")
    if not repo:
        print(f"{RED}  GITHUB_REPO not set in .env{R}")
        sys.exit(1)

    exec_plans: list[str] = state["data"].get("execution_plans") or [
        str(p.relative_to(REPO_ROOT))
        for p in sorted((REPO_ROOT / "docs" / "execution-plans").glob("EXECUTION-PLAN-*.md"))
    ]
    exec_to_plan: dict[str, str] = state["data"].get("exec_to_plan", {})

    header(f"STEP 7 — Create GitHub Issues  [{ROLES['tech_lead']}]")
    print(f"  Repository : {repo}")
    print(f"  Execution plans to process: {len(exec_plans)}")
    for ep in exec_plans:
        print(f"    • {ep}")

    if not gate("tech_lead", f"create issues on github.com/{repo}"):
        print(f"{RED}  Cancelled.{R}")
        sys.exit(0)

    for ep_path in exec_plans:
        print(f"\n  {BOLD}Creating issues from {ep_path}...{R}")
        extra: list[str] = []
        if ep_path in exec_to_plan:
            extra = ["--plan-file", exec_to_plan[ep_path]]
        if not run_script("parse_plan_to_issues.py", [
            "--execution-plan-file", ep_path,
            "--repo", repo,
        ] + extra):
            print(f"  {YELLOW}Warning: issue creation failed for {ep_path}{R}")

    state["completed"].append("issues")
    save_state(state)
    print(f"\n{GREEN}{BOLD}✓ All issues created.{R}")
    print(f"  → https://github.com/{repo}/issues")


# ── Main ───────────────────────────────────────────────────────────────────────

STEPS = [
    ("setup",           step_setup,           "Create pipeline branches"),
    ("prd",             step_prd,             f"PRD review  [{ROLES['product_owner']}]"),
    ("roadmap",         step_roadmap,         f"Roadmap  [{ROLES['project_manager']}]"),
    ("milestones",      step_milestones,      f"Milestones  [{ROLES['project_manager']}]"),
    ("plans",           step_plans,           f"Feature plans  [{ROLES['tech_lead']}]"),
    ("execution_plans", step_execution_plans, f"Execution plans  [{ROLES['tech_lead']}]"),
    ("issues",          step_issues,          f"GitHub issues  [{ROLES['tech_lead']}]"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="AI-SDLC pipeline simulation")
    parser.add_argument("--from-step", type=int, default=1, metavar="N",
                        help="Start from step N (default: 1). Completed steps are always skipped.")
    parser.add_argument("--reset", action="store_true", help="Clear saved state and restart from scratch")
    args = parser.parse_args()

    load_env()
    state = load_state()

    if args.reset:
        state = {"completed": [], "data": {}}
        save_state(state)
        print(f"{GREEN}State reset.{R}")

    print(f"\n{BOLD}AI-SDLC Pipeline Simulation{R}")
    print(f"  Repo:    {REPO_ROOT}")
    print(f"  GitHub:  {os.environ.get('GITHUB_REPO', '(not set — needed for Step 7)')}")
    print(f"\n  Team:")
    for role, name in ROLES.items():
        print(f"    {role.replace('_', ' ').title():22s}→  {name}")
    print(f"\n  Steps:")
    for i, (key, _, label) in enumerate(STEPS, 1):
        done = "✓" if key in state["completed"] else " "
        print(f"    {done} {i}. {label}")

    start = max(1, args.from_step) - 1
    for i, (key, fn, label) in enumerate(STEPS):
        if i < start:
            continue
        print(f"\n{DIM}─── Step {i+1}/{len(STEPS)}: {label}{R}")
        fn(state)

    print(f"\n{GREEN}{BOLD}Simulation complete.{R}")
    if "issues" in state["completed"]:
        repo = os.environ.get("GITHUB_REPO", "")
        if repo:
            print(f"  Issues: https://github.com/{repo}/issues")


if __name__ == "__main__":
    main()
