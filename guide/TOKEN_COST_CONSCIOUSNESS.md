# Token Cost Consciousness

A living record of how this project manages context size and token costs in Claude API calls.

---

## Task-Scoped Context Assembly

**Problem:** Every Claude call was loading all context docs regardless of what files the task touched. A frontend component task had no need for `DATA_MODELS.md`; a backend endpoint task had no need for frontend coding standards.

**Decision:** Extend `load_context_docs()` in `_shared.py` to accept the list of affected file paths and return only the docs relevant to those files. `ARCHITECTURE.md` and `SECURITY_CHECKLIST.md` are always included as a global baseline.

**Result:** Single-layer tasks (backend-only or frontend-only) load ~40–60% fewer context tokens.

**Implementation:** `_shared.py` → `load_context_docs()` and `context_files_for_paths()`
