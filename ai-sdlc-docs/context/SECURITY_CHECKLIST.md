# Security Checklist

Use this checklist when writing or reviewing any code in this repository.

---

## Secrets & Credentials

- [ ] No secrets, API keys, tokens, or passwords in source code
- [ ] No secrets in comments or docstrings
- [ ] Secrets are read from environment variables only (`os.environ.get("KEY")`)
- [ ] `.env` files are listed in `.gitignore` — never committed
- [ ] GitHub Actions secrets accessed via `${{ secrets.SECRET_NAME }}` — never echoed to logs
- [ ] `detect-private-key` pre-commit hook is enabled and passing

## Environment Variables

- [ ] All required env vars are documented in repository docs or `.env.example`
- [ ] Missing env vars cause a startup error (fail fast), not a runtime error later
- [ ] Default values for env vars are safe for development, not production (e.g., `APP_ENV=development`, not `APP_ENV=production` as a default)

## Backend (FastAPI)

- [ ] CORS: when configured, `allow_origins` is an explicit allowlist — never `["*"]` in production
- [ ] No `DEBUG=true` or equivalent in production Dockerfile or docker-compose
- [ ] User input is never passed to `shell=True` subprocess calls
- [ ] User input is never interpolated into file paths without sanitization
- [ ] No `eval()` or `exec()` on user-supplied data
- [ ] Pydantic models validate all external input at API boundaries

## Frontend (React)

- [ ] No API keys or tokens in frontend source code (they would be exposed to the browser)
- [ ] User-supplied content is never rendered via `dangerouslySetInnerHTML`
- [ ] External URLs are not opened via `window.open` with user-supplied values without validation

## Docker

- [ ] Both images run as non-root users
- [ ] Runtime images do not contain build tools (`uv`, `npm`, compilers)
- [ ] No `--privileged` flags in docker-compose
- [ ] Base images are pinned to specific versions (not `:latest`)

## Dependencies

- [ ] `uv lock` and `npm ci` use pinned lockfiles — no floating versions in CI
- [ ] New dependencies are reviewed for known vulnerabilities before adding
- [ ] `npm audit` warnings are reviewed (moderate+ severity)

## AI-Generated Code

- [ ] All AI-generated PRs pass the same CI checks as human PRs
- [ ] AI-generated code is reviewed by a human before merging to `main`
- [ ] AI scripts never commit directly to `main` — always open a PR
