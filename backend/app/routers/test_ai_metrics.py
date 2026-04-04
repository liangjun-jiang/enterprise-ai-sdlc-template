import os
from datetime import date
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import HTTPException

from app.main import app
from app.models.ai_metrics import AiMetricsResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(period: str = "this_week") -> AiMetricsResponse:
    return AiMetricsResponse(
        period=period,
        period_start=date(2024, 1, 15),
        period_end=date(2024, 1, 21),
        plans_generated=5,
        issues_created_by_ai=12,
        ai_prs_opened=8,
        ai_prs_merged=6,
        ai_prs_rejected_closed=2,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@patch.dict(
    os.environ,
    {"GITHUB_TOKEN": "ghp_test", "GITHUB_REPO": "owner/repo"},
)
async def test_get_ai_metrics_this_week_returns_200() -> None:
    mock_fetch = AsyncMock(return_value=_make_response("this_week"))
    with patch("app.routers.ai_metrics.fetch_ai_metrics", mock_fetch):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/ai-metrics?period=this_week")

    assert response.status_code == 200
    body = response.json()
    assert body["period"] == "this_week"
    assert body["plans_generated"] == 5
    assert body["issues_created_by_ai"] == 12
    assert body["ai_prs_opened"] == 8
    assert body["ai_prs_merged"] == 6
    assert body["ai_prs_rejected_closed"] == 2
    mock_fetch.assert_awaited_once_with("this_week")


@patch.dict(
    os.environ,
    {"GITHUB_TOKEN": "ghp_test", "GITHUB_REPO": "owner/repo"},
)
async def test_get_ai_metrics_this_month_returns_200() -> None:
    mock_fetch = AsyncMock(return_value=_make_response("this_month"))
    with patch("app.routers.ai_metrics.fetch_ai_metrics", mock_fetch):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/ai-metrics?period=this_month")

    assert response.status_code == 200
    assert response.json()["period"] == "this_month"


@patch.dict(
    os.environ,
    {"GITHUB_TOKEN": "ghp_test", "GITHUB_REPO": "owner/repo"},
)
async def test_get_ai_metrics_missing_period_returns_422() -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/ai-metrics")

    assert response.status_code == 422


@patch.dict(
    os.environ,
    {"GITHUB_TOKEN": "ghp_test", "GITHUB_REPO": "owner/repo"},
)
async def test_get_ai_metrics_invalid_period_returns_422() -> None:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/ai-metrics?period=last_year")

    assert response.status_code == 422


@patch.dict(
    os.environ,
    {"GITHUB_TOKEN": "ghp_test", "GITHUB_REPO": "owner/repo"},
)
async def test_get_ai_metrics_github_error_returns_502() -> None:
    mock_fetch = AsyncMock(
        side_effect=HTTPException(status_code=502, detail="GitHub API error: 403")
    )
    with patch("app.routers.ai_metrics.fetch_ai_metrics", mock_fetch):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/ai-metrics?period=this_week")

    assert response.status_code == 502
    body = response.json()
    assert "detail" in body
    assert "GitHub API error" in body["detail"]
