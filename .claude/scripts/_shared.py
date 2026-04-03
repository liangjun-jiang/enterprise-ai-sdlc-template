"""Shared utilities for AI pipeline scripts."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import anthropic
from dotenv import load_dotenv
from github import Auth, Github
from github.GithubException import GithubException

# Auto-load .env from the scripts directory if present (local dev convenience)
load_dotenv(Path(__file__).parent / ".env")


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

_ALWAYS_INCLUDED = ["ARCHITECTURE.md", "SECURITY_CHECKLIST.md"]

_BACKEND_FILES = ["CODING_STANDARDS.md", "DATA_MODELS.md", "API_CONTRACTS.md", "CURRENT_TECH_STACK.md"]
_FRONTEND_FILES = ["CODING_STANDARDS.md", "API_CONTRACTS.md", "CURRENT_TECH_STACK.md"]

# Fallback when no affected paths are provided
CONTEXT_FILES = _ALWAYS_INCLUDED + _BACKEND_FILES + ["CODING_STANDARDS.md"]


def context_files_for_paths(affected_paths: list[str]) -> list[str]:
    """Return the minimal set of context doc filenames relevant to the given file paths."""
    has_backend = any("backend/" in p for p in affected_paths)
    has_frontend = any("frontend/" in p for p in affected_paths)
    files = list(_ALWAYS_INCLUDED)
    if has_backend:
        files += _BACKEND_FILES
    if has_frontend:
        files += _FRONTEND_FILES
    if not has_backend and not has_frontend:
        files += _BACKEND_FILES  # safe default for scripts / unknown paths
    return list(dict.fromkeys(files))  # deduplicate, preserve order


def load_context_docs(
    context_dir: Path,
    filenames: list[str] | None = None,
    affected_paths: list[str] | None = None,
) -> str:
    """Load context docs and concatenate them with headers.

    Pass `affected_paths` for task-scoped loading (recommended).
    Pass `filenames` to load an explicit list.
    Falls back to CONTEXT_FILES when neither is provided.
    """
    if filenames is not None:
        names = filenames
    elif affected_paths is not None:
        names = context_files_for_paths(affected_paths)
    else:
        names = CONTEXT_FILES

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
# Claude client — supports direct Anthropic API, gateway, and AWS Bedrock
#
# Set LLM_PROVIDER to one of:
#   - direct  : direct Anthropic API
#   - gateway : Anthropic-compatible gateway (requires ANTHROPIC_BASE_URL)
#   - bedrock : AWS Bedrock
#
# Backward compatibility:
# - If LLM_PROVIDER is unset, provider is inferred:
#   - bedrock if LLM_PROVIDER=bedrock (legacy)
#   - gateway if ANTHROPIC_BASE_URL is set
#   - otherwise direct
#
# Bedrock uses standard AWS credential env vars:
#   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN (optional),
#   AWS_DEFAULT_REGION (default: us-east-1)
#
# Model IDs in AI_PIPELINE_CONFIG.json should use Bedrock format:
#   anthropic.claude-opus-4-6, anthropic.claude-sonnet-4-6
# When using direct Anthropic API the "anthropic." prefix is stripped automatically.
# ---------------------------------------------------------------------------

def llm_provider() -> str:
    """Resolve and validate the active LLM provider."""
    raw = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if raw:
        if raw not in {"direct", "gateway", "bedrock"}:
            die("LLM_PROVIDER must be one of: direct, gateway, bedrock")
        if raw == "gateway" and not os.environ.get("ANTHROPIC_BASE_URL"):
            die("LLM_PROVIDER=gateway requires ANTHROPIC_BASE_URL")
        return raw
    # Backward-compatible inference when LLM_PROVIDER is not set.
    if os.environ.get("ANTHROPIC_BASE_URL"):
        return "gateway"
    return "direct"


def anthropic_client() -> anthropic.Anthropic | anthropic.AnthropicBedrock:
    provider = llm_provider()
    if provider == "bedrock":
        region = os.environ.get("AWS_DEFAULT_REGION", "us-west-2")
        print(f"[info] Using AWS Bedrock (region: {region})", flush=True)
        return anthropic.AnthropicBedrock(aws_region=region)
    else:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            die("ANTHROPIC_API_KEY is required for direct/gateway providers")
        base_url = os.environ.get("ANTHROPIC_BASE_URL")
        kwargs: dict[str, str] = {"api_key": api_key}
        if provider == "gateway" and base_url:
            kwargs["base_url"] = base_url
            print(f"[info] Using Anthropic-compatible gateway: {base_url}", flush=True)
        return anthropic.Anthropic(**kwargs)  # type: ignore[arg-type]


def normalize_model_id(model: str) -> str:
    """Resolve the model ID for the active provider.

    Config stores Bedrock-format IDs (e.g. 'anthropic.claude-sonnet-4-6').

    - Bedrock (LLM_PROVIDER=bedrock): keep as-is
    - LiteLLM gateway (ANTHROPIC_BASE_URL set): keep as-is — gateway is
      deployed on Bedrock and expects Bedrock model IDs
    - Direct Anthropic API: strip the 'anthropic.' prefix
    """
    provider = llm_provider()
    if provider in {"bedrock", "gateway"}:
        return model
    if model.startswith("anthropic."):
        return model[len("anthropic."):]
    return model


def call_claude(
    client: anthropic.Anthropic | anthropic.AnthropicBedrock,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 8192,
) -> str:
    """Call Claude and return the text of the first content block."""
    provider = llm_provider()
    resolved_model = normalize_model_id(model)
    print(f"[info] Provider: {provider} | Model: {resolved_model}", flush=True)
    response = client.messages.create(
        model=resolved_model,
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


def list_git_tracked_files(repo_root: Path, path: str) -> list[str]:
    """Return repo-relative paths of all git-tracked files under the given path.

    Uses `git ls-files` so only committed/staged files are returned —
    not untracked local artifacts. Falls back to an empty list if git
    is unavailable or the path does not exist.
    """
    import subprocess
    result = subprocess.run(
        ["git", "ls-files", path],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]
