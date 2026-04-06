"""
GitHub Metrics Service
======================

Fetches AI pipeline activity metrics from the GitHub Search API.

Heuristics
----------
- **plans_generated**: Issues that carry *both* the ``ai-generated`` and
  ``ai-plan`` labels.  The ``ai-plan`` label is applied by the
  ``plan-to-execution`` workflow immediately after a plan document is
  committed, so this count approximates the number of execution plans that
  were produced by the AI pipeline in the period.
- **issues_created_by_ai**: All issues carrying ``ai-generated``.
- **ai_prs_opened**: All pull requests carrying ``ai-generated``.
- **ai_prs_merged**: Subset that GitHub reports as ``is:merged``.
- **ai_prs_rejected_closed**: Subset that are ``is:closed is:unmerged``
  (closed without being merged — i.e. explicitly rejected or abandoned).
"""

import os

import httpx
from fastapi import HTTPException

from app.models.ai_metrics import AiMetricsResponse, compute_period_range

_GITHUB_SEARCH_URL = "https://api.github.com/search/issues"


async def _search_count(client: httpx.AsyncClient, query: str) -> int:
    """Execute one GitHub Search API query and return ``total_count``."""
    try:
        response = await client.get(
            _GITHUB_SEARCH_URL,
            params={"q": query, "per_page": 1},
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"GitHub API error: {exc.response.status_code}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"GitHub API error: {type(exc).__name__}",
        ) from exc

    data: dict[str, object] = response.json()
    total = data.get("total_count", 0)
    if not isinstance(total, int):
        raise HTTPException(
            status_code=502,
            detail="GitHub API error: unexpected response shape",
        )
    return total


async def fetch_ai_metrics(period: str) -> AiMetricsResponse:
    """Fetch AI pipeline metrics from the GitHub Search API.

    Parameters
    ----------
    period:
        One of ``'this_week'`` or ``'this_month'``.

    Returns
    -------
    AiMetricsResponse
        Populated response model.

    Raises
    ------
    HTTPException(502)
        When the GitHub API is unreachable or returns a non-2xx status.
    """
    period_start, period_end = compute_period_range(period)
    start_str = period_start.isoformat()

    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["GITHUB_REPO"]

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient(headers=headers, timeout=15.0) as client:
        issues_count = await _search_count(
            client,
            f"repo:{repo} is:issue label:ai-generated created:>={start_str}",
        )
        plans_count = await _search_count(
            client,
            f"repo:{repo} is:issue label:ai-generated label:ai-plan created:>={start_str}",
        )
        prs_all_count = await _search_count(
            client,
            f"repo:{repo} is:pr label:ai-generated created:>={start_str}",
        )
        prs_merged_count = await _search_count(
            client,
            f"repo:{repo} is:pr label:ai-generated is:merged created:>={start_str}",
        )
        prs_rejected_count = await _search_count(
            client,
            f"repo:{repo} is:pr label:ai-generated is:closed is:unmerged created:>={start_str}",
        )

    return AiMetricsResponse(
        period=period,
        period_start=period_start,
        period_end=period_end,
        plans_generated=plans_count,
        issues_created_by_ai=issues_count,
        ai_prs_opened=prs_all_count,
        ai_prs_merged=prs_merged_count,
        ai_prs_rejected_closed=prs_rejected_count,
    )
