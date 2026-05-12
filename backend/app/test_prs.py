import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

import os

os.environ.setdefault("GITHUB_TOKEN", "test-token")
os.environ.setdefault("GITHUB_REPO", "test-owner/test-repo")

from app.routers.prs import router  # noqa: E402

app = FastAPI()
app.include_router(router, prefix="/api")


OPEN_PR = {
    "number": 1,
    "title": "Add feature X",
    "html_url": "https://github.com/test-owner/test-repo/pull/1",
    "created_at": "2024-01-15T10:00:00Z",
    "merged_at": None,
    "state": "open",
}

MERGED_PR = {
    "number": 2,
    "title": "Fix bug Y",
    "html_url": "https://github.com/test-owner/test-repo/pull/2",
    "created_at": "2024-01-14T09:00:00Z",
    "merged_at": "2024-01-14T12:00:00Z",
    "state": "closed",
}

CLOSED_NOT_MERGED_PR = {
    "number": 3,
    "title": "Abandoned PR",
    "html_url": "https://github.com/test-owner/test-repo/pull/3",
    "created_at": "2024-01-13T08:00:00Z",
    "merged_at": None,
    "state": "closed",
}


def make_mock_response(data: list[dict], status_code: int = 200) -> MagicMock:  # type: ignore[type-arg]
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = data
    mock_resp.raise_for_status = MagicMock()
    if status_code >= 400:
        from httpx import HTTPStatusError, Request, Response

        mock_resp.raise_for_status.side_effect = HTTPStatusError(
            message="error",
            request=MagicMock(spec=Request),
            response=MagicMock(spec=Response),
        )
    return mock_resp


async def _get(url: str, **kwargs: object) -> AsyncClient:
    raise NotImplementedError


@pytest.fixture()
def mock_httpx_get():
    with patch("app.routers.prs.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        yield mock_client


async def test_get_open_prs_returns_open_prs(mock_httpx_get: AsyncMock) -> None:
    mock_httpx_get.get = AsyncMock(return_value=make_mock_response([OPEN_PR]))

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/prs?state=open")

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["per_page"] == 30
    assert len(body["prs"]) == 1
    pr = body["prs"][0]
    assert pr["number"] == 1
    assert pr["title"] == "Add feature X"
    assert pr["state"] == "open"
    assert pr["merged_at"] is None
    assert pr["url"] == "https://github.com/test-owner/test-repo/pull/1"


async def test_get_merged_prs_returns_only_merged(mock_httpx_get: AsyncMock) -> None:
    mock_httpx_get.get = AsyncMock(
        return_value=make_mock_response([MERGED_PR, CLOSED_NOT_MERGED_PR])
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/prs?state=merged")

    assert response.status_code == 200
    body = response.json()
    assert len(body["prs"]) == 1
    pr = body["prs"][0]
    assert pr["number"] == 2
    assert pr["title"] == "Fix bug Y"
    assert pr["merged_at"] == "2024-01-14T12:00:00Z"


async def test_get_merged_prs_excludes_closed_but_not_merged(mock_httpx_get: AsyncMock) -> None:
    mock_httpx_get.get = AsyncMock(
        return_value=make_mock_response([CLOSED_NOT_MERGED_PR])
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/prs?state=merged")

    assert response.status_code == 200
    body = response.json()
    assert len(body["prs"]) == 0


async def test_pagination_params_forwarded(mock_httpx_get: AsyncMock) -> None:
    mock_httpx_get.get = AsyncMock(return_value=make_mock_response([OPEN_PR]))

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/prs?state=open&page=2&per_page=10")

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 2
    assert body["per_page"] == 10

    call_kwargs = mock_httpx_get.get.call_args
    params = call_kwargs.kwargs.get("params") or call_kwargs.args[1] if len(call_kwargs.args) > 1 else call_kwargs.kwargs.get("params", {})
    assert params["page"] == 2
    assert params["per_page"] == 10


async def test_github_api_error_returns_502(mock_httpx_get: AsyncMock) -> None:
    from httpx import HTTPStatusError, Request, Response

    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.raise_for_status.side_effect = HTTPStatusError(
        message="Forbidden",
        request=MagicMock(spec=Request),
        response=MagicMock(spec=Response),
    )
    mock_httpx_get.get = AsyncMock(return_value=mock_resp)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/prs?state=open")

    assert response.status_code == 502
    assert "GitHub API error" in response.json()["detail"]


async def test_github_api_5xx_returns_502(mock_httpx_get: AsyncMock) -> None:
    from httpx import HTTPStatusError, Request, Response

    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.raise_for_status.side_effect = HTTPStatusError(
        message="Internal Server Error",
        request=MagicMock(spec=Request),
        response=MagicMock(spec=Response),
    )
    mock_httpx_get.get = AsyncMock(return_value=mock_resp)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/prs?state=merged")

    assert response.status_code == 502


async def test_open_prs_github_api_called_with_correct_params(mock_httpx_get: AsyncMock) -> None:
    mock_httpx_get.get = AsyncMock(return_value=make_mock_response([OPEN_PR]))

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.get("/api/prs?state=open&page=1&per_page=30")

    mock_httpx_get.get.assert_called_once()
    call_kwargs = mock_httpx_get.get.call_args
    params = call_kwargs.kwargs.get("params", {})
    assert params["state"] == "open"
    assert params["sort"] == "created"
    assert params["direction"] == "desc"


async def test_merged_prs_github_api_called_with_closed_state(mock_httpx_get: AsyncMock) -> None:
    mock_httpx_get.get = AsyncMock(return_value=make_mock_response([MERGED_PR]))

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.get("/api/prs?state=merged&page=1&per_page=30")

    mock_httpx_get.get.assert_called_once()
    call_kwargs = mock_httpx_get.get.call_args
    params = call_kwargs.kwargs.get("params", {})
    assert params["state"] == "closed"
    assert params["sort"] == "created"
    assert params["direction"] == "desc"


async def test_total_count_reflects_filtered_results(mock_httpx_get: AsyncMock) -> None:
    mock_httpx_get.get = AsyncMock(
        return_value=make_mock_response([MERGED_PR, CLOSED_NOT_MERGED_PR, MERGED_PR])
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/prs?state=merged")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["prs"]) == 2


async def test_invalid_state_returns_422() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/prs?state=invalid")

    assert response.status_code == 422
