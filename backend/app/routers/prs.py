from typing import Any, Literal

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.config import GITHUB_OWNER, GITHUB_REPO_NAME, GITHUB_TOKEN
from app.models.pr import PRItem, PRListResponse

router = APIRouter()

GITHUB_API_BASE = "https://api.github.com"


@router.get("/prs", response_model=PRListResponse)
async def list_prs(
    state: Literal["open", "merged"] = Query(..., description="Filter PRs by state: 'open' or 'merged'"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(30, ge=1, le=100, description="Number of PRs per page"),
) -> PRListResponse:
    """Return a paginated list of open or merged pull requests from the configured GitHub repo."""
    github_state = "open" if state == "open" else "closed"

    url = (
        f"{GITHUB_API_BASE}/repos/{GITHUB_OWNER}/{GITHUB_REPO_NAME}/pulls"
        f"?state={github_state}&sort=created&direction=desc&page={page}&per_page={per_page}"
    )

    headers: dict[str, str] = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=15.0)
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Error contacting GitHub API: {exc}") from exc

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"GitHub API returned {response.status_code}: {response.text}",
        )

    raw_items: list[dict[str, Any]] = response.json()

    pr_items: list[PRItem] = []
    for item in raw_items:
        merged_at: str | None = item.get("merged_at")
        item_state: str = item.get("state", "")

        # For merged state, only include PRs that are actually merged
        if state == "merged" and merged_at is None:
            continue

        pr_items.append(
            PRItem(
                number=item["number"],
                title=item["title"],
                url=item["html_url"],
                created_at=item["created_at"],
                merged_at=merged_at,
                state=item_state,
            )
        )

    return PRListResponse(
        prs=pr_items,
        total=len(pr_items),
        page=page,
        per_page=per_page,
    )
