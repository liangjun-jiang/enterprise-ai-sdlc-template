#!/usr/bin/env python3
"""
bedrock_model_api_test.py

Minimal Bedrock Converse API test using boto3.
Useful for validating model ID / inference profile ARN + AWS auth settings.

Auth (pick one):
  - Amazon Bedrock API key: set AWS_BEARER_TOKEN_BEDROCK, or --api-key, or paste a key in
    PASTE_BEDROCK_API_KEY_HERE below (boto3 uses Bearer auth; do not pass --profile).
  - IAM: omit API key and use --profile / default credential chain.

Run from repo root (boto3 comes from the .claude/scripts uv project):

  uv run --project .claude/scripts python bedrock_model_api_test.py \\
    --model-id us.anthropic.claude-3-5-haiku-20241022-v1:0 \\
    --region us-west-2 \\
    --api-key "$AWS_BEARER_TOKEN_BEDROCK"

IAM example:

  uv run --project .claude/scripts python bedrock_model_api_test.py \\
    --model-id arn:aws:bedrock:us-west-2:ACCOUNT:inference-profile/us.anthropic.claude-sonnet-4-6 \\
    --region us-west-2 \\
    --profile your-profile
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

# Paste your Amazon Bedrock API key here for quick local checks (optional).
PASTE_BEDROCK_API_KEY_HERE = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test Bedrock Converse API model access.")
    parser.add_argument(
        "--model-id",
        default=os.environ.get("AWS_BEDROCK_MODEL_ID", ""),
        help="Model ID or inference profile ARN (or set AWS_BEDROCK_MODEL_ID)",
    )
    parser.add_argument(
        "--prompt",
        default="Hello from Bedrock Converse API test.",
        help="User prompt to send",
    )
    parser.add_argument(
        "--region",
        default=os.environ.get("AWS_DEFAULT_REGION", "us-west-2"),
        help="AWS region (default: AWS_DEFAULT_REGION or us-west-2)",
    )
    parser.add_argument(
        "--profile",
        default=os.environ.get("AWS_PROFILE"),
        help="AWS profile name (optional; ignored when using a Bedrock API key)",
    )
    parser.add_argument(
        "--api-key",
        default="",
        metavar="KEY",
        help="Amazon Bedrock API key (Bearer). If empty, uses PASTE_BEDROCK_API_KEY_HERE, "
        "then AWS_BEARER_TOKEN_BEDROCK / BEDROCK_API_KEY env vars.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=32000,
        help="maxTokens for inferenceConfig (default: 32000)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=250,
        help="top_k for additionalModelRequestFields (default: 250)",
    )
    parser.add_argument(
        "--latency",
        default="standard",
        choices=["standard", "optimized"],
        help="performance latency mode (default: standard)",
    )
    args = parser.parse_args()
    if not args.model_id:
        parser.error("--model-id is required (or set AWS_BEDROCK_MODEL_ID)")
    return args


def extract_text(resp: dict[str, Any]) -> str:
    output = resp.get("output", {})
    message = output.get("message", {})
    content = message.get("content", [])
    for item in content:
        text = item.get("text")
        if isinstance(text, str) and text.strip():
            return text
    return ""


def _resolve_bedrock_api_key(args: argparse.Namespace) -> str:
    for candidate in (
        (args.api_key or "").strip(),
        (PASTE_BEDROCK_API_KEY_HERE or "").strip(),
        (os.environ.get("AWS_BEARER_TOKEN_BEDROCK") or "").strip(),
        (os.environ.get("BEDROCK_API_KEY") or "").strip(),
    ):
        if candidate:
            return candidate
    return ""


def main() -> None:
    args = parse_args()

    api_key = _resolve_bedrock_api_key(args)
    use_bearer = bool(api_key)

    print(f"[info] region   : {args.region}")
    print(f"[info] auth     : {'Bedrock API key (Bearer)' if use_bearer else 'IAM / profile / default chain'}")
    if not use_bearer:
        print(f"[info] profile  : {args.profile or '(default chain)'}")
    print(f"[info] model_id : {args.model_id}")
    print(f"[info] prompt   : {args.prompt!r}")
    print("[info] calling bedrock-runtime.converse ...", flush=True)

    try:
        if use_bearer:
            os.environ["AWS_BEARER_TOKEN_BEDROCK"] = api_key
            session = boto3.Session(region_name=args.region)
        else:
            session_kwargs: dict[str, str] = {"region_name": args.region}
            if args.profile:
                session_kwargs["profile_name"] = args.profile
            session = boto3.Session(**session_kwargs)
        client = session.client("bedrock-runtime", region_name=args.region)

        response = client.converse(
            modelId=args.model_id,
            messages=[{"role": "user", "content": [{"text": args.prompt}]}],
            inferenceConfig={"maxTokens": args.max_tokens, "stopSequences": []},
            additionalModelRequestFields={"top_k": args.top_k},
            performanceConfig={"latency": args.latency},
        )
    except (BotoCoreError, ClientError) as e:
        print(f"[error] Bedrock call failed: {e}", file=sys.stderr)
        sys.exit(1)

    text = extract_text(response)
    if not text:
        print("[warn] No text content found in response.")
        print(json.dumps(response, indent=2, default=str))
        return

    print("\n[response]")
    print(text)
    print("\n[ok] Bedrock Converse call succeeded.")


if __name__ == "__main__":
    main()
