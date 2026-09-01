"""REST boundary for Sentiment Service status."""

from __future__ import annotations

from fastapi import APIRouter, Request

from crypto_lab.api.common import ApiModel, SuccessEnvelope, success_envelope
from crypto_lab.api.middleware import request_id
from crypto_lab.application.news.errors import dependency_unavailable
from crypto_lab.infrastructure.persistence.repositories.sentiment_repository import (
    SqlAlchemySentimentAnalysisRepository,
)

router = APIRouter(prefix="/api/v1/sentiment", tags=["sentiment"])


class SentimentStatusDto(ApiModel):
    pending: int
    analyzed: int
    failed: int


def _sentiment_repository(request: Request) -> SqlAlchemySentimentAnalysisRepository:
    container = request.app.state.container
    repository = getattr(container, "sentiment_repository", None)
    if not isinstance(repository, SqlAlchemySentimentAnalysisRepository):
        raise dependency_unavailable()
    return repository


@router.get("/status", response_model=SuccessEnvelope[SentimentStatusDto])
async def get_sentiment_status(request: Request) -> SuccessEnvelope[SentimentStatusDto]:
    from crypto_lab.api.dependencies import SENTIMENT_MODEL

    repository = _sentiment_repository(request)
    counts = await repository.count_by_status(SENTIMENT_MODEL)
    return success_envelope(
        SentimentStatusDto(
            pending=counts.get("pending", 0),
            analyzed=counts.get("analyzed", 0),
            failed=counts.get("failed", 0),
        ),
        "Sentiment status loaded.",
        request_id(request),
    )


__all__ = ["router"]
