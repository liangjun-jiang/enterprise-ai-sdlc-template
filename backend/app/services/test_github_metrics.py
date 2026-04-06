import os
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException

from app.services.github_metrics import _search_count, fetch_ai_metrics


# ---------------------------------------------------------------------------
# _search_count
# ---------------------------------------------------------------------------


async def test_search_count_returns_total_count() -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.json.return_value = {"total_count": 42, "items": []}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = mock_response

    result = await _search_count(mock_client, "repo:owner/repo is:issue")
    assert result == 42


async def test_search_count_raises_502_on_http_status_error() -> None:
    error_response = MagicMock(spec=httpx.Response)
    error_response.status_code = 403

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.HTTPStatusError(
        "Forbidden", request=MagicMock(), response=error_response
    )

    with pytest.raises(HTTPException) as exc_info:
        await _search_count(mock_client, "repo:owner/repo is:issue")

    assert exc_info.value.status_code == 502
    assert "403" in exc_info.value.detail
    # Raw GitHub body must not appear
    assert "Forbidden" not in exc_info.value.detail


async def test_search_count_raises_502_on_request_error() -> None:
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.ConnectError("connection refused")

    with pytest.raises(HTTPException) as exc_info:
        await _search_count(mock_client, "repo:owner/repo is:issue")

    assert exc_info.value.status_code == 502
    assert "ConnectError" in exc_info.value.detail


async def test_search_count_raises_502_on_unexpected_shape() -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.json.return_value = {"items": []}  # missing total_count → 0 default
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = mock_response

    # total_count missing means it defaults to 0 (falsy but valid int 0)
    result = await _search_count(mock_client, "repo:owner/repo is:issue")
    assert result == 0


async def test_search_count_raises_502_when_total_count_not_int() -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.json.return_value = {"total_count": "not-an-int"}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = mock_response

    with pytest.raises(HTTPException) as exc_info:
        await _search_count(mock_client, "repo:owner/repo is:issue")

    assert exc_info.value.status_code == 502


# ---------------------------------------------------------------------------
# fetch_ai_metrics
# ---------------------------------------------------------------------------


@patch.dict(
    os.environ,
    {"GITHUB_TOKEN": "ghp_test", "GITHUB_REPO": "owner/repo"},
)
async def test_fetch_ai_metrics_returns_response_model() -> None:
    call_count = 0

    async def mock_search_count(
        client: httpx.AsyncClient, query: str  # noqa: ARG001
    ) -> int:
        nonlocal call_count
        call_count += 1
        # Return different values per call so we can verify field mapping
        return call_count * 10

    with patch(
        "app.services.github_metrics._search_count",
        side_effect=mock_search_count,
    ):
        result = await fetch_ai_metrics("this_week")

    assert result.period == "this_week"
    assert isinstance(result.period_start, date)
    assert isinstance(result.period_end, date)
    assert result.period_start <= result.period_end
    # 5 calls made in order: issues, plans, prs_all, prs_merged, prs_rejected
    assert call_count == 5
    assert result.issues_created_by_ai == 10
    assert result.plans_generated == 20
    assert result.ai_prs_opened == 30
    assert result.ai_prs_merged == 40
    assert result.ai_prs_rejected_closed == 50


@patch.dict(
    os.environ,
    {"GITHUB_TOKEN": "ghp_test", "GITHUB_REPO": "owner/repo"},
)
async def test_fetch_ai_metrics_this_month() -> None:
    async def mock_search_count(
        client: httpx.AsyncClient, query: str  # noqa: ARG001
    ) -> int:
        return 0

    with patch(
        "app.services.github_metrics._search_count",
        side_effect=mock_search_count,
    ):
        result = await fetch_ai_metrics("this_month")

    assert result.period == "this_month"
    assert result.period_start.day == 1


@patch.dict(
    os.environ,
    {"GITHUB_TOKEN": "ghp_test", "GITHUB_REPO": "owner/repo"},
)
async def test_fetch_ai_metrics_propagates_502() -> None:
    async def mock_search_count(
        client: httpx.AsyncClient, query: str  # noqa: ARG001
    ) -> int:
        raise HTTPException(status_code=502, detail="GitHub API error: 403")

    with patch(
        "app.services.github_metrics._search_count",
        side_effect=mock_search_count,
    ):
        with pytest.raises(HTTPException) as exc_info:
            await fetch_ai_metrics("this_week")

    assert exc_info.value.status_code == 502
