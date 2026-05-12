# Coding Standards

## Python (Backend)

### Type Hints
- All function signatures **must** have type hints — parameters and return types.
- Use `dict[str, str]` not `Dict[str, str]` (Python 3.10+ built-in generics).
- Use `list[str]` not `List[str]`.
- Use `X | None` not `Optional[X]`.
- Pydantic models are the contract layer for request/response bodies — always define them.

### Async
- All FastAPI route handlers must be `async def`.
- Use `httpx.AsyncClient` for outbound HTTP calls (never `requests`).
- Never use `time.sleep` — use `asyncio.sleep`.

### Ruff (linter + formatter)
- Line length: 120
- Selected rules: `E`, `F`, `I001` (isort)
- Run: `uvx ruff@0.7.4 check .` and `uvx ruff@0.7.4 format .`
- Pre-commit runs ruff automatically — do not bypass with `# noqa` without justification.

### Mypy
- Strict mode: `strict = true` in `pyproject.toml`
- No `type: ignore` comments without an inline explanation.

### Tests (pytest)
- Test file naming: `test_<module>.py` co-located with the module (e.g., `app/test_main.py`).
- One test file per module. Test functions: `test_<behavior>_<expected_outcome>`.
- Always use `httpx.ASGITransport(app=app)` — never the deprecated `app=` shorthand.
- `asyncio_mode = "auto"` is set — no need for `@pytest.mark.asyncio` unless overriding loop scope.
- Mock `httpx.AsyncClient` with `unittest.mock.AsyncMock` and `patch` — mock the `__aenter__`/`__aexit__` context manager methods.

### File Structure
```
backend/app/
├── __init__.py       # empty
├── main.py           # FastAPI app instance + route registration
├── config.py         # environment variable loading (GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO_NAME, etc.)
├── routers/          # one file per logical group of routes
│   └── __init__.py
├── models/           # Pydantic request/response models
└── test_<module>.py  # tests co-located with their module
```

### Routers
- Each logical group of endpoints lives in its own file under `app/routers/`.
- Routers are registered in `main.py` via `app.include_router(...)`.
- The `/api/v1` prefix is used for versioned endpoints (e.g., AI metrics); `/api` is used for unversioned endpoints (e.g., PRs).

### Anti-patterns
- No `print()` statements in production code — use `logging`.
- No mutable default arguments (`def f(x: list = [])`).
- No bare `except:` — always catch a specific exception type.
- No `os.system()` — use `subprocess.run()` with explicit args list.

---

## TypeScript / React (Frontend)

### TypeScript
- `strict: true` in `tsconfig.json` — no exceptions.
- No `any` type. If you need an escape hatch, use `unknown` and narrow.
- Always type component props explicitly — no implicit `{}` props.
- Prefer `type` over `interface` for object shapes (consistency).

### React
- Functional components only — no class components.
- No inline arrow functions in JSX props that create new references on every render (use `useCallback` if needed).
- `useEffect` must declare all dependencies in the dependency array.
- `data-testid` attributes are the primary selector in tests — add them to interactive/observable elements.
- Modal components must include `role="dialog"`, `aria-modal="true"`, and either `aria-label` or `aria-labelledby`.
- Modals must handle `Escape` key to close (add/remove `keydown` listener in `useEffect`).
- Use relative paths for all API calls — never hardcode backend URLs.

### ESLint
- Config: `eslint.config.js` (flat config, ESLint v9)
- Extends: `typescript-eslint` recommended
- `--max-warnings 0` in CI — no warnings allowed.

### Tests (vitest + @testing-library/react)
- Test file naming: `<Component>.test.tsx` co-located with component.
- Prefer `getByRole` over `getByTestId` for accessibility-sensitive assertions.
- Use `data-testid` for non-semantic observable state (e.g., loading status, error status, list container).
- Mock `fetch` with `vi.stubGlobal` in `beforeEach` or per-test, restore in `afterEach` with `vi.unstubAllGlobals()`.
- Wrap state updates triggered by user interactions in `act()` when asserting on async state changes.
- Test IDs to use for PR list component: `pr-list-loading`, `pr-list-error`, `pr-list`, `pr-list-prev`, `pr-list-next`.

### File Structure
```
frontend/src/
├── App.tsx           # root component
├── App.test.tsx      # root component tests
├── setupTests.ts     # @testing-library/jest-dom import
├── components/       # shared UI components
└── pages/            # route-level components (when router added)
```

### Anti-patterns
- No `console.log` in production code.
- No hardcoded backend URLs — always use relative paths.
- No direct DOM manipulation (`document.getElementById`).
- No `// @ts-ignore` without an inline explanation.

---

## Git / PR Standards

- Branch names: `feat/<short-description>`, `fix/<short-description>`, `chore/<short-description>`
- Commit messages: imperative mood, ≤72 chars subject line
- Every PR must pass CI (ruff + mypy + pytest + eslint + vitest) before merge
- PRs opened by AI workflows get the `ai-generated` label automatically
