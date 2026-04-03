#!/usr/bin/env python3
"""
smoke_test.py

Minimal LLM connectivity test. Sends a single prompt to Claude and prints
the response. Use this to verify your API credentials and provider config
before running the full pipeline scripts.

Usage (direct Anthropic API):
    LLM_API_KEY=sk-... python smoke_test.py

Usage (AWS Bedrock):
    LLM_PROVIDER=bedrock AWS_DEFAULT_REGION=us-west-2 python smoke_test.py

Usage (custom model / prompt):
    LLM_API_KEY=sk-... python smoke_test.py \
        --model anthropic.claude-haiku-4-5-20251001 \
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
