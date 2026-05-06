#!/usr/bin/env python3
"""
build_code_context.py

Builds a lightweight, deterministic codebase summary for planning/coding context.
Writes ai-sdlc-docs/context/CODEBASE_OVERVIEW.md.
"""

from __future__ import annotations

import ast
from datetime import UTC, datetime
from pathlib import Path

from _shared import find_repo_root


def _python_symbols(path: Path) -> tuple[list[str], list[str]]:
    classes: list[str] = []
    functions: list[str] = []
    try:
        tree = ast.parse(path.read_text())
    except Exception:
        return classes, functions
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, ast.FunctionDef):
            functions.append(node.name)
    return classes, functions


def _router_endpoints(path: Path) -> list[str]:
    endpoints: list[str] = []
    lines = path.read_text().splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("@router.") and "(" in stripped:
            # Keep the decorator and next function signature line for readability.
            snippet = stripped
            if i + 1 < len(lines) and lines[i + 1].strip().startswith("async def "):
                snippet = f"{snippet} -> {lines[i + 1].strip().split('(')[0]}"
            endpoints.append(snippet)
    return endpoints


def _list_files(root: Path, base: Path, suffix: str) -> list[Path]:
    if not base.exists():
        return []
    return sorted(p for p in base.rglob(f"*{suffix}") if p.is_file())


def build_overview(repo_root: Path) -> str:
    backend_app = repo_root / "backend" / "app"
    frontend_src = repo_root / "frontend" / "src"

    backend_py = _list_files(repo_root, backend_app, ".py")
    frontend_ts = _list_files(repo_root, frontend_src, ".ts")
    frontend_tsx = _list_files(repo_root, frontend_src, ".tsx")

    routers: list[str] = []
    model_files: list[str] = []
    service_files: list[str] = []
    symbol_lines: list[str] = []

    for py_file in backend_py:
        rel = py_file.relative_to(repo_root).as_posix()
        if "/routers/" in rel:
            routers.append(rel)
        if "/models/" in rel:
            model_files.append(rel)
        if "/services/" in rel:
            service_files.append(rel)

        classes, functions = _python_symbols(py_file)
        if classes or functions:
            class_part = f"classes: {', '.join(classes[:6])}" if classes else ""
            fn_part = f"functions: {', '.join(functions[:6])}" if functions else ""
            joined = " | ".join(part for part in [class_part, fn_part] if part)
            symbol_lines.append(f"- `{rel}` - {joined}")

    endpoint_lines: list[str] = []
    for router in routers[:20]:
        endpoints = _router_endpoints(repo_root / router)
        for ep in endpoints[:8]:
            endpoint_lines.append(f"- `{router}`: `{ep}`")

    ts_files = [p.relative_to(repo_root).as_posix() for p in frontend_ts + frontend_tsx]
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    parts = [
        "# Codebase Overview",
        "",
        f"_Auto-generated: {generated_at}_",
        "",
        "## Snapshot",
        f"- Backend Python files: {len(backend_py)}",
        f"- Frontend TS/TSX files: {len(ts_files)}",
        "",
        "## Backend Focus Areas",
        f"- Routers: {len(routers)}",
        f"- Services: {len(service_files)}",
        f"- Models: {len(model_files)}",
        "",
        "## Router Endpoints (sample)",
    ]
    parts.extend(endpoint_lines[:60] if endpoint_lines else ["- _(none detected)_"])
    parts.extend(["", "## Python Symbols (sample)"])
    parts.extend(symbol_lines[:120] if symbol_lines else ["- _(none detected)_"])
    parts.extend(["", "## Frontend Files (sample)"])
    parts.extend([f"- `{f}`" for f in ts_files[:120]] if ts_files else ["- _(none detected)_"])
    parts.extend(
        [
            "",
            "## Notes",
            "- This document is intentionally compact and deterministic.",
            "- Use it as orientation context; rely on task-specific files for implementation details.",
        ]
    )
    return "\n".join(parts) + "\n"


def main() -> None:
    repo_root = find_repo_root()
    out_path = repo_root / "ai-sdlc-docs" / "context" / "CODEBASE_OVERVIEW.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(build_overview(repo_root))
    print(f"[info] Wrote {out_path}")


if __name__ == "__main__":
    main()
