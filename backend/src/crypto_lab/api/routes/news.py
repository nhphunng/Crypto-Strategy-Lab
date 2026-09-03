"""REST boundary for reading stored news."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, Request

from crypto_lab.api.common import SuccessEnvelope, success_envelope
from crypto_lab.api.middleware import request_id
from crypto_lab.api.schemas.news import NewsPageDto, page_to_dto
from crypto_lab.application.news.errors import (
    NewsError,
    coin_invalid,
    dependency_unavailable,
    page_invalid,
    range_invalid,
)
from crypto_lab.application.news.list_news import ListNews
from crypto_lab.application.news.ports import NewsQuery
from crypto_lab.application.sentiment.ports import SentimentAnalysisRepository
from crypto_lab.domain.sentiment.model import SentimentLabel

router = APIRouter(prefix="/api/v1/news", tags=["news"])

_COIN = re.compile(r"^[A-Z0-9]{1,10}$")

MIN_PAGE_SIZE = 1
MAX_PAGE_SIZE = 100


def _news_service(request: Request) -> ListNews:
    """Resolve the ListNews use case; Task 7 adds the concrete container field."""
    container = request.app.state.container
    service = getattr(container, "list_news", None)
    if not isinstance(service, ListNews):
        raise dependency_unavailable()
    return service


def _sentiment_repository(request: Request) -> SentimentAnalysisRepository | None:
    """Resolve the sentiment repository if wired; sentiment is optional here.

    A deployment (or a test's stub container) that has not wired sentiment
    yet must not fail the news list -- it simply projects `sentiment: null`
    for every item, which is also the correct contract for a pending or
    failed analysis.
    """
    container = request.app.state.container
    repository: SentimentAnalysisRepository | None = getattr(
        container, "sentiment_repository", None
    )
    return repository


def _published(value: str | None, field: str) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise range_invalid(
            f"{field} must be a valid UTC ISO-8601 instant.", field=field
        ) from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise range_invalid(f"{field} must carry a UTC offset.", field=field)
    return parsed.astimezone(UTC)


@router.get("", response_model=SuccessEnvelope[NewsPageDto])
async def list_news(
    request: Request,
    coin: str | None = Query(default=None),
    sentiment: SentimentLabel | None = Query(default=None),
    published_after: str | None = Query(default=None, alias="publishedAfter"),
    published_before: str | None = Query(default=None, alias="publishedBefore"),
    page: int = Query(default=1),
    page_size: int = Query(default=50, alias="pageSize"),
    service: ListNews = Depends(_news_service),
    sentiment_repository: SentimentAnalysisRepository | None = Depends(_sentiment_repository),
) -> SuccessEnvelope[NewsPageDto]:
    if coin is not None and not _COIN.fullmatch(coin):
        raise coin_invalid("coin must be an uppercase market symbol.", coin=coin)
    after = _published(published_after, "publishedAfter")
    before = _published(published_before, "publishedBefore")
    if after is not None and before is not None and after > before:
        raise range_invalid("publishedAfter must not be after publishedBefore.")
    if page < 1:
        raise page_invalid("page must be at least 1.", page=page)
    if not MIN_PAGE_SIZE <= page_size <= MAX_PAGE_SIZE:
        raise page_invalid("pageSize must be between 1 and 100.", pageSize=page_size)

    result = await service.execute(
        NewsQuery(
            coin=coin,
            published_after=after,
            published_before=before,
            page=page,
            page_size=page_size,
            sentiment=sentiment.value if sentiment else None,
        )
    )
    sentiment_map = (
        await sentiment_repository.latest_for(tuple(item.id for item in result.items))
        if sentiment_repository is not None
        else {}
    )
    return success_envelope(page_to_dto(result, sentiment_map), "News loaded.", request_id(request))


__all__ = ["NewsError", "router"]
