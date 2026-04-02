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


def commit_files_to_branch(
    target_branch: str,
    file_map: dict[str, str],   # repo-relative path → content
    commit_msg: str,
    author_name: str,
) -> None:
    """Write file_map as a commit on target_branch without leaving the current branch."""
    orig = current_branch()

    # Stash all changes + untracked files so switching is clean
    stash_out = git(["stash", "push", "-u", "-m", "sim_stash"], check=False, capture=True).stdout
    stashed = "No local changes" not in stash_out

    git(["checkout", target_branch])

    for rel, content in file_map.items():
        abs_p = REPO_ROOT / rel
        abs_p.parent.mkdir(parents=True, exist_ok=True)
        abs_p.write_text(content)
        git(["add", rel])

    email = author_name.lower().replace(" ", ".") + "@team.local"
    env = {**os.environ, "GIT_AUTHOR_NAME": author_name, "GIT_AUTHOR_EMAIL": email,
           "GIT_COMMITTER_NAME": author_name, "GIT_COMMITTER_EMAIL": email}
    subprocess.run(["git", "commit", "-m", commit_msg], cwd=REPO_ROOT, env=env, check=True)
    print(f"  {GREEN}✓ Committed to branch '{target_branch}'{R}")

    git(["checkout", orig])
    if stashed:
        git(["stash", "pop"])


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

    prd_file = REPO_ROOT / "docs" / "prd" / "prd-000-dashboard.md"
    header(f"STEP 2 — PRD Review  [{ROLES['product_owner']}]")
    show_file(prd_file)

    if not gate("product_owner", "docs/prd/prd-000-dashboard.md"):
        print(f"{RED}  PRD rejected — stopping.{R}")
        sys.exit(0)

    commit_files_to_branch(
        "prd",
        {"docs/prd/prd-000-dashboard.md": prd_file.read_text()},
        "feat: add prd-000-dashboard (approved by James Smith)",
        ROLES["product_owner"],
    )
    state["completed"].append("prd")
    save_state(state)


def step_roadmap(state: dict[str, Any]) -> None:
    if "roadmap" in state["completed"]:
        print(f"  {DIM}[skip] roadmap already approved{R}")
        return

    header(f"STEP 3 — Roadmap  [{ROLES['project_manager']}]")
    roadmap_path = REPO_ROOT / "docs" / "roadmap" / "ROADMAP.md"

    if roadmap_path.exists():
        print(f"  {YELLOW}ROADMAP.md already exists — using existing file (skip LLM call).{R}")
        print(f"  To regenerate, delete docs/roadmap/ROADMAP.md and re-run.")
    else:
        print("  Generating ROADMAP.md from prd-000-dashboard.md ...")
        if not run_script("prd_to_roadmap.py", [
            "--prd-file", "docs/prd/prd-000-dashboard.md",
            "--context-dir", "docs/context",
            "--local",
        ]):
            print(f"{RED}  prd_to_roadmap.py failed — stopping.{R}")
            sys.exit(1)

    show_file(roadmap_path)
    if not gate("project_manager", "docs/roadmap/ROADMAP.md"):
        print(f"{RED}  Roadmap rejected — stopping.{R}")
        sys.exit(0)

    commit_files_to_branch(
        "roadmap",
        {"docs/roadmap/ROADMAP.md": roadmap_path.read_text()},
        "feat: AI-generated ROADMAP.md from prd-000-dashboard",
        ROLES["project_manager"],
    )
    state["completed"].append("roadmap")
    save_state(state)


def step_milestones(state: dict[str, Any]) -> None:
    if "milestones" in state["completed"]:
        print(f"  {DIM}[skip] milestones already approved{R}")
        return

    header(f"STEP 4 — Milestones  [{ROLES['project_manager']}]")
    ms_dir = REPO_ROOT / "docs" / "milestones"
    existing = sorted(ms_dir.glob("milestone-*.md"))

    if existing:
        print(f"  {YELLOW}{len(existing)} milestone file(s) already exist — using them (skip LLM call).{R}")
        for f in existing:
            print(f"    • {f.name}")
        print(f"  To regenerate, delete docs/milestones/milestone-*.md and re-run.")
    else:
        print("  Generating milestone files from ROADMAP.md ...")
        if not run_script("roadmap_to_milestones.py", [
            "--roadmap-file", "docs/roadmap/ROADMAP.md",
            "--context-dir", "docs/context",
            "--local",
        ]):
            print(f"{RED}  roadmap_to_milestones.py failed — stopping.{R}")
            sys.exit(1)
        existing = sorted(ms_dir.glob("milestone-*.md"))

    if not existing:
        print(f"{RED}  No milestone files found after generation.{R}")
        sys.exit(1)

    for f in existing:
        show_file(f, max_lines=30)

    if not gate("project_manager", f"{len(existing)} milestone file(s) in docs/milestones/"):
        print(f"{RED}  Milestones rejected — stopping.{R}")
        sys.exit(0)

    commit_files_to_branch(
        "milestone",
        {f"docs/milestones/{f.name}": f.read_text() for f in existing},
        f"feat: AI-generated {len(existing)} milestone(s)",
        ROLES["project_manager"],
    )
    state["completed"].append("milestones")
    state["data"]["milestone_files"] = [f.name for f in existing]
    save_state(state)


def step_plans(state: dict[str, Any]) -> None:
    if "plans" in state["completed"]:
        print(f"  {DIM}[skip] feature plans already approved{R}")
        return

    header(f"STEP 5 — Feature Plans  [{ROLES['tech_lead']}]")
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
        print(f"{RED}  No plan files found.{R}")
        sys.exit(1)

    for f in existing:
        show_file(f, max_lines=25)

    if not gate("tech_lead", f"{len(existing)} feature plan(s) in docs/plans/"):
        print(f"{RED}  Plans rejected — stopping.{R}")
        sys.exit(0)

    commit_files_to_branch(
        "plan",
        {f"docs/plans/{f.name}": f.read_text() for f in existing},
        f"feat: AI-generated {len(existing)} feature plan(s)",
        ROLES["tech_lead"],
    )
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
    print(f"  {len(plan_files)} plan(s) available:\n")
    for i, name in enumerate(plan_files, 1):
        slug = re.sub(r"^PLAN-\d+-", "", name[:-3])
        # mark if execution plan already exists
        ep = REPO_ROOT / "docs" / "execution-plans" / slug / "EXECUTION_PLAN.md"
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
                    re.sub(r"^PLAN-\d+-", "", n[:-3]) / "EXECUTION_PLAN.md").exists()
        ]
    else:
        idxs = [int(x.strip()) - 1 for x in sel.split(",") if x.strip().isdigit()]
        selected = [plan_files[i] for i in idxs if 0 <= i < len(plan_files)]

    if not selected:
        print(f"{RED}  Nothing selected — stopping.{R}")
        sys.exit(0)

    print(f"\n  Will process {len(selected)} plan(s).")
    generated: list[Path] = []
    exec_to_plan: dict[str, str] = {}

    for plan_name in selected:
        slug = re.sub(r"^PLAN-\d+-", "", plan_name[:-3])
        plan_path = f"docs/plans/{plan_name}"
        output_path = f"docs/execution-plans/{slug}/EXECUTION_PLAN.md"
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

        generated.append(abs_output)
        exec_to_plan[output_path] = plan_path

    if not generated:
        print(f"{RED}  No execution plans approved.{R}")
        sys.exit(0)

    commit_files_to_branch(
        "plan-execution",
        {str(p.relative_to(REPO_ROOT)): p.read_text() for p in generated},
        f"feat: AI-generated {len(generated)} execution plan(s)",
        ROLES["tech_lead"],
    )
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
        for p in (REPO_ROOT / "docs" / "execution-plans").rglob("EXECUTION_PLAN.md")
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
