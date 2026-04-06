from typing import Literal

from fastapi import APIRouter

from app.models.ai_metrics import AiMetricsResponse
from app.services.github_metrics import fetch_ai_metrics

router = APIRouter(tags=["ai-metrics"])


@router.get("/ai-metrics", response_model=AiMetricsResponse)
async def get_ai_metrics(
    period: Literal["this_week", "this_month"],
) -> AiMetricsResponse:
    """Return AI pipeline activity metrics for the requested time period.

    Parameters
    ----------
    period:
        ``this_week`` — Monday of the current ISO week through today.
        ``this_month`` — 1st of the current month through today.
    """
    return await fetch_ai_metrics(period)
