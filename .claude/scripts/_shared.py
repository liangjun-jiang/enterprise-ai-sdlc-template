"""Shared utilities for AI pipeline scripts."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import anthropic
from github import Auth, Github
from github.GithubException import GithubException


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_pipeline_config(repo_root: Path) -> dict[str, Any]:
    """Load AI_PIPELINE_CONFIG.json from docs/context/."""
    config_path = repo_root / "docs" / "context" / "AI_PIPELINE_CONFIG.json"
    if not config_path.exists():
        die(f"AI_PIPELINE_CONFIG.json not found at {config_path}")
    with config_path.open() as f:
        return json.load(f)  # type: ignore[no-any-return]


def check_circuit_breaker(config: dict[str, Any]) -> None:
    """Exit non-zero if circuit breaker is active."""
    if config.get("circuit_breaker_active", False):
        die("Circuit breaker is ACTIVE. Set circuit_breaker_active=false in AI_PIPELINE_CONFIG.json to resume.")


# ---------------------------------------------------------------------------
# Context assembly
# ---------------------------------------------------------------------------

CONTEXT_FILES = [
    "ARCHITECTURE.md",
    "CURRENT_TECH_STACK.md",
    "CODING_STANDARDS.md",
    "DATA_MODELS.md",
    "API_CONTRACTS.md",
    "SECURITY_CHECKLIST.md",
]


def load_context_docs(context_dir: Path, filenames: list[str] | None = None) -> str:
    """Load context docs and concatenate them with headers."""
    names = filenames or CONTEXT_FILES
    parts: list[str] = []
    for name in names:
        path = context_dir / name
        if path.exists():
            parts.append(f"## {name}\n\n{path.read_text()}")
        else:
            print(f"[warn] context file not found: {path}", file=sys.stderr)
    return "\n\n---\n\n".join(parts)


def load_system_prompt(context_dir: Path, filename: str) -> str:
    """Load a system prompt file from context_dir."""
    path = context_dir / filename
    if not path.exists():
        die(f"System prompt not found: {path}")
    return path.read_text()


def read_file_safe(path: Path) -> str:
    """Return file contents or a placeholder if the file does not exist."""
    if path.exists():
        return path.read_text()
    return f"[File does not exist yet: {path}]"


def apply_token_budget(text: str, max_tokens: int) -> str:
    """Rough truncation guard: ~4 chars per token."""
    max_chars = max_tokens * 4
    if len(text) > max_chars:
        print(f"[warn] truncating context from {len(text)} to {max_chars} chars", file=sys.stderr)
        return text[:max_chars] + "\n\n[... truncated due to token budget ...]"
    return text


# ---------------------------------------------------------------------------
# GitHub client
# ---------------------------------------------------------------------------

def github_client() -> Github:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        die("GITHUB_TOKEN environment variable is required")
    return Github(auth=Auth.Token(token))


def get_repo(gh: Github, repo_name: str) -> Any:
    try:
        return gh.get_repo(repo_name)
    except GithubException as e:
        die(f"Could not access repo {repo_name!r}: {e}")


# ---------------------------------------------------------------------------
# Claude client
# ---------------------------------------------------------------------------

def anthropic_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        die("ANTHROPIC_API_KEY environment variable is required")
    return anthropic.Anthropic(api_key=api_key)


def call_claude(
    client: anthropic.Anthropic,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 8192,
) -> str:
    """Call Claude and return the text of the first content block."""
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    block = response.content[0]
    if block.type != "text":
        die(f"Unexpected response content type: {block.type}")
    return block.text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def die(message: str) -> None:
    """Print error to stderr and exit non-zero."""
    print(f"[error] {message}", file=sys.stderr)
    sys.exit(1)


def find_repo_root() -> Path:
    """Walk up from cwd to find the repo root (contains .git)."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists():
            return parent
    die("Could not find repo root (no .git directory found)")
    return Path()  # unreachable, satisfies mypy
