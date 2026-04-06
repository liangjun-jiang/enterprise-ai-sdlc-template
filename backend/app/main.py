import os

from fastapi import FastAPI

from app.models.ai_metrics import validate_github_env
from app.routers.ai_metrics import router as ai_metrics_router

# Validate required environment variables at import time so the application
# refuses to start (not just at first request) when configuration is missing.
if os.environ.get("SKIP_ENV_VALIDATION") != "1":
    validate_github_env()

app = FastAPI(title="Enterprise AI-SDLC Template")

app.include_router(ai_metrics_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
