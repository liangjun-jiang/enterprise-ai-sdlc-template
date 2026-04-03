"""Pydantic models and helpers for the AI pipeline metrics endpoint."""

import os
import re
from datetime import date, timedelta

from pydantic import BaseModel

_GITHUB_REPO_RE = re.compile(r"^[^/]+/[^/]+$")


def validate_github_env() -> None:
    """Raise RuntimeError if required GitHub environment variables are missing or invalid."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "Missing required environment variable GITHUB_TOKEN. "
            "Set it to a GitHub personal access token with 'repo' scope."
        )

    repo = os.environ.get("GITHUB_REPO")
    if not repo:
        raise RuntimeError(
            "Missing required environment variable GITHUB_REPO. "
            "Set it to the target repository in 'owner/repo' format (e.g. 'acme/my-repo')."
        )

    if not _GITHUB_REPO_RE.match(repo):
        raise RuntimeError(
            f"Invalid GITHUB_REPO value '{repo}'. "
            "Expected format is 'owner/repo' (e.g. 'acme/my-repo')."
        )


def compute_period_range(period: str) -> tuple[date, date]:
    """Return (period_start, today) for the given period label.

    Args:
        period: Either ``'this_week'`` or ``'this_month'``.

    Returns:
        A tuple of ``(period_start, today)`` as :class:`datetime.date` objects.

    Raises:
        ValueError: If *period* is not a recognised label.
    """
    today = date.today()

    if period == "this_week":
        # ISO weekday: Monday = 1, Sunday = 7
        monday = today - timedelta(days=today.weekday())
        return monday, today

    if period == "this_month":
        first = today.replace(day=1)
        return first, today

    raise ValueError(f"Unknown period '{period}'. Expected 'this_week' or 'this_month'.")


class AiMetricsResponse(BaseModel):
    """Response body for the AI pipeline metrics endpoint."""

    period: str
    """Echoed query parameter ('this_week' or 'this_month')."""

    period_start: date
    """ISO-8601 date of the period start (Monday or 1st of month)."""

    period_end: date
    """ISO-8601 date of today (UTC)."""

    plans_generated: int
    """Count of issues with labels 'ai-generated' and 'ai-plan'."""

    issues_created_by_ai: int
    """Count of issues with label 'ai-generated'."""

    ai_prs_opened: int
    """Count of pull requests with label 'ai-generated'."""

    ai_prs_merged: int
    """Subset of ai_prs_opened that are merged."""

    ai_prs_rejected_closed: int
    """Subset of ai_prs_opened that are closed but not merged."""
