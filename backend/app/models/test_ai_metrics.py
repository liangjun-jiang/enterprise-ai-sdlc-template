"""Tests for backend/app/models/ai_metrics.py."""

import os
from datetime import date, timedelta
from unittest.mock import patch

import pytest

from app.models.ai_metrics import (
    AiMetricsResponse,
    compute_period_range,
    validate_github_env,
)


# ---------------------------------------------------------------------------
# compute_period_range
# ---------------------------------------------------------------------------


def test_compute_period_range_this_week_returns_monday() -> None:
    start, end = compute_period_range("this_week")
    assert end == date.today()
    # start must be a Monday (weekday == 0)
    assert start.weekday() == 0
    # start must be <= end and within the last 6 days
    assert start <= end
    assert (end - start).days <= 6


def test_compute_period_range_this_month_returns_first() -> None:
    start, end = compute_period_range("this_month")
    today = date.today()
    assert end == today
    assert start == today.replace(day=1)


def test_compute_period_range_this_week_on_monday() -> None:
    """When today IS Monday, period_start == today."""
    # Find the most recent (or current) Monday
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    with patch("app.models.ai_metrics.date") as mock_date:
        mock_date.today.return_value = monday
        # timedelta still needs to work normally
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        start, end = compute_period_range("this_week")

    assert start == monday
    assert end == monday


def test_compute_period_range_unknown_period_raises() -> None:
    with pytest.raises(ValueError, match="Unknown period"):
        compute_period_range("last_quarter")


# ---------------------------------------------------------------------------
# validate_github_env
# ---------------------------------------------------------------------------


def test_validate_github_env_passes_with_valid_vars() -> None:
    with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_abc", "GITHUB_REPO": "acme/my-repo"}):
        validate_github_env()  # should not raise


def test_validate_github_env_raises_when_token_missing() -> None:
    env = {"GITHUB_REPO": "acme/my-repo"}
    with patch.dict(os.environ, env, clear=True):
        # Ensure GITHUB_TOKEN is absent
        os.environ.pop("GITHUB_TOKEN", None)
        with pytest.raises(RuntimeError, match="GITHUB_TOKEN"):
            validate_github_env()


def test_validate_github_env_raises_when_repo_missing() -> None:
    env = {"GITHUB_TOKEN": "ghp_abc"}
    with patch.dict(os.environ, env, clear=True):
        os.environ.pop("GITHUB_REPO", None)
        with pytest.raises(RuntimeError, match="GITHUB_REPO"):
            validate_github_env()


def test_validate_github_env_raises_when_repo_format_invalid() -> None:
    with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_abc", "GITHUB_REPO": "not-a-valid-repo"}):
        with pytest.raises(RuntimeError, match="owner/repo"):
            validate_github_env()


def test_validate_github_env_raises_when_repo_has_extra_slashes() -> None:
    with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_abc", "GITHUB_REPO": "org/repo/extra"}):
        with pytest.raises(RuntimeError, match="owner/repo"):
            validate_github_env()


# ---------------------------------------------------------------------------
# AiMetricsResponse
# ---------------------------------------------------------------------------


def test_ai_metrics_response_roundtrip() -> None:
    today = date.today()
    first = today.replace(day=1)

    payload = {
        "period": "this_month",
        "period_start": first.isoformat(),
        "period_end": today.isoformat(),
        "plans_generated": 5,
        "issues_created_by_ai": 12,
        "ai_prs_opened": 8,
        "ai_prs_merged": 6,
        "ai_prs_rejected_closed": 2,
    }

    model = AiMetricsResponse.model_validate(payload)

    assert model.period == "this_month"
    assert model.period_start == first
    assert model.period_end == today
    assert model.plans_generated == 5
    assert model.issues_created_by_ai == 12
    assert model.ai_prs_opened == 8
    assert model.ai_prs_merged == 6
    assert model.ai_prs_rejected_closed == 2


def test_ai_metrics_response_rejects_missing_field() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        AiMetricsResponse.model_validate(
            {
                "period": "this_week",
                # period_start intentionally omitted
                "period_end": date.today().isoformat(),
                "plans_generated": 0,
                "issues_created_by_ai": 0,
                "ai_prs_opened": 0,
                "ai_prs_merged": 0,
                "ai_prs_rejected_closed": 0,
            }
        )
