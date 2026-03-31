# Token Cost Consciousness

## The Problem

Every Claude API call pays for the full context injected into the prompt — even parts irrelevant to the task. As the project grows (more endpoints, more patterns, more architectural decisions), context docs bloat and two problems emerge:

1. **Cost** — every call pays for the full context, used or not
2. **Noise** — a coder writing a frontend component doesn't need `DATA_MODELS.md`; diluted context produces worse output

The context docs in this repo are currently ~2–5K tokens — small enough not to matter today. This becomes a real concern at 20K+ tokens.

---

## How the Industry Addresses This

### 1. Retrieval-Augmented Generation (RAG)
Instead of dumping all context docs into every prompt, embed them into a vector store and retrieve only the chunks semantically similar to the current task. The coder writing a React component gets `CODING_STANDARDS.md#frontend` + `API_CONTRACTS.md`, not the full corpus.

Tools: pgvector, Pinecone, Chroma.

Best for: large projects with many context docs where static mapping becomes unwieldy.

### 2. Task-Scoped Context Assembly
Statically map task types to context subsets based on which files are being touched:
- Backend files (`backend/`) → Python standards + API contracts + data models
- Frontend files (`frontend/`) → TypeScript standards + API contracts
- Pipeline scripts (`.claude/scripts/`) → architecture + security checklist

No new infrastructure needed — just smarter logic in `_shared.py`'s `load_context_docs()`. **This is the highest-leverage improvement for this project specifically.**

### 3. Hierarchical Context (Global + Local)
Keep a lean global context (architecture, security rules) always included, and maintain per-module context files (e.g. `docs/context/modules/auth.md`) included only when that module is touched.

This is the pattern Cursor uses with `.cursorrules` files scoped per directory.

### 4. Context Compression / Summarization
Periodically run a summarization pass over context docs to keep them dense and prune stale content. `update_context_docs.py` already does a version of this after each merge — it could be extended to also compress verbose sections that have grown over time.

### 5. Structured Context (Not Prose)
Replace narrative prose with machine-readable schemas where possible. A 50-line OpenAPI spec conveys more precise information than 200 lines of `API_CONTRACTS.md` prose, and LLMs read both equally well. Schemas also version cleanly and diff readably.

---

## Recommended Progression for This Project

| Stage | Project size | Approach |
|-------|-------------|----------|
| Now | < 10 context docs | Full context on every call (current) |
| Growing | 10–30 context docs | Task-scoped assembly in `_shared.py` |
| Large | 30+ docs or 20K+ tokens | RAG with a vector store |
| Mature | Stable, well-structured | Structured context (OpenAPI, JSON Schema, type stubs) replacing prose |

---

## Quick Win: Task-Scoped Assembly

To implement task-scoped context in `_shared.py`, extend `load_context_docs()` to accept a list of affected file paths and return only relevant docs:

```python
def context_files_for_paths(affected_paths: list[str]) -> list[str]:
    has_backend = any("backend/" in p for p in affected_paths)
    has_frontend = any("frontend/" in p for p in affected_paths)
    files = ["ARCHITECTURE.md", "SECURITY_CHECKLIST.md"]  # always included
    if has_backend:
        files += ["CODING_STANDARDS.md", "DATA_MODELS.md", "API_CONTRACTS.md", "CURRENT_TECH_STACK.md"]
    if has_frontend:
        files += ["CODING_STANDARDS.md", "API_CONTRACTS.md", "CURRENT_TECH_STACK.md"]
    return list(dict.fromkeys(files))  # deduplicate, preserve order
```

This alone could cut context size by 40–60% for single-layer tasks.
