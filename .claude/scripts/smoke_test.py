#!/usr/bin/env python3
"""
smoke_test.py

Minimal LLM connectivity test. Sends a single prompt to Claude and prints
the response. Use this to verify your API credentials and provider config
before running the full pipeline scripts.

Dependencies live in `.claude/scripts` (uv project). Do not use bare `python`;
use `uv run` so anthropic and other packages resolve.

Environment variables are read from the process environment. Importing `_shared`
also loads `.claude/scripts/.env` via python-dotenv (same as other pipeline scripts).

  LLM_API_KEY     — required for direct Anthropic API and for gateway mode
  LLM_BASE_URL    — gateway / OpenAI-compatible proxy base URL (optional if unset: direct API)
  LLM_API_URL     — alias for LLM_BASE_URL if you prefer that name
  LLM_PROVIDER    — optional: `direct`, `gateway`, or `bedrock` (inferred from URL when unset)
  Bedrock (API key) — LLM_PROVIDER=bedrock, AWS_DEFAULT_REGION, and one of:
                      AWS_BEARER_TOKEN_BEDROCK (AWS name), BEDROCK_API_KEY, or LLM_API_KEY
                      (only if AWS_ACCESS_KEY_ID is unset — avoids mixing with IAM keys)
  Bedrock (IAM)     — LLM_PROVIDER=bedrock plus AWS_ACCESS_KEY_ID / profile / default chain

From repo root:

    uv run --project .claude/scripts python .claude/scripts/smoke_test.py

From `.claude/scripts` (after `uv sync` if needed):

    uv run python smoke_test.py

Examples (direct Anthropic API):

    LLM_API_KEY=sk-... uv run --project .claude/scripts python .claude/scripts/smoke_test.py

Gateway (custom base URL):

    LLM_API_KEY=... LLM_BASE_URL=https://your-proxy/v1 uv run --project .claude/scripts python .claude/scripts/smoke_test.py

AWS Bedrock (Bedrock API key — put the key in .env as below, or export it):

    LLM_PROVIDER=bedrock AWS_DEFAULT_REGION=us-west-2 AWS_BEARER_TOKEN_BEDROCK=... \\
      uv run --project .claude/scripts python .claude/scripts/smoke_test.py

    # Equivalent: BEDROCK_API_KEY=... or LLM_API_KEY=... (with LLM_PROVIDER=bedrock, no AWS_ACCESS_KEY_ID)

Custom model / prompt:

    LLM_API_KEY=sk-... uv run --project .claude/scripts python .claude/scripts/smoke_test.py \\
        --model anthropic.claude-haiku-4-5-20251001 \\
        --prompt "What is 2+2? Reply in one sentence."
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _shared import anthropic_client, call_claude, find_repo_root, load_pipeline_config


DEFAULT_PROMPT = (
    "You are a helpful assistant. Reply in exactly one sentence: "
    "confirm you are working and state which model you are."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-test LLM connectivity.")
    parser.add_argument(
        "--model",
        default=None,
        help="Model ID override (defaults to 'coder' model from AI_PIPELINE_CONFIG.json)",
    )
    parser.add_argument(
        "--prompt",
        default=DEFAULT_PROMPT,
        help="Prompt text to send",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=256,
        help="Max output tokens (default: 256)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    repo_root = find_repo_root()
    config = load_pipeline_config(repo_root)

    model = args.model or config["models"]["coder"]
    print(f"[smoke] Prompt : {args.prompt!r}")
    print(f"[smoke] Model  : {model}")
    print(f"[smoke] Calling LLM...", flush=True)

    client = anthropic_client()
    response = call_claude(
        client=client,
        model=model,
        system="You are a helpful assistant.",
        user=args.prompt,
        max_tokens=args.max_tokens,
    )

    print(f"\n[smoke] === RESPONSE ===")
    print(response)
    print(f"[smoke] === END ===")
    print(f"\n[smoke] OK — LLM connectivity confirmed.")


if __name__ == "__main__":
    main()
