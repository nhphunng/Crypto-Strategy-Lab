"""News list DTOs aligned to the TV5 contract.

JSON is camelCase and instants are UTC ISO-8601 millisecond strings. Task 4
fills ``sentiment`` with the latest COMPLETED analysis for each item (see
``domain.sentiment``); an item with no analysis yet, or whose only analysis
FAILED, still projects ``sentiment: null`` -- a label/score is never
fabricated for a pending or failed analysis.
"""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from pydantic import Field

from crypto_lab.api.common import ApiModel
from crypto_lab.application.news.ports import NewsPage
from crypto_lab.domain.market_data.candle import format_utc_millis
from crypto_lab.domain.news.item import NewsItem
from crypto_lab.domain.sentiment.analysis import NewsSentimentAnalysis
from crypto_lab.domain.sentiment.model import SentimentStatus


class SentimentAnalysisDto(ApiModel):
    """The latest COMPLETED sentiment analysis for a News item, if any."""

    label: str
    score: str
    model_id: str = Field(alias="modelId")
    model_version: str = Field(alias="modelVersion")
    analyzed_at: str = Field(alias="analyzedAt")


class NewsItemDto(ApiModel):
    news_id: str = Field(alias="newsId")
    title: str
    content: str
    source: str
    published_at: str = Field(alias="publishedAt")
    crawled_at: str = Field(alias="crawledAt")
    related_coins: tuple[str, ...] = Field(alias="relatedCoins")
    url: str
    sentiment: SentimentAnalysisDto | None = None


class NewsPageDto(ApiModel):
    items: tuple[NewsItemDto, ...]
    page: int
    page_size: int = Field(alias="pageSize")
    total: int


def item_to_dto(
    item: NewsItem,
    sentiment_map: Mapping[UUID, NewsSentimentAnalysis] | None = None,
) -> NewsItemDto:
    analysis = (sentiment_map or {}).get(item.id)
    sentiment = (
        SentimentAnalysisDto(
            label=analysis.label.value,
            score=str(analysis.score),
            model_id=analysis.model_id,
            model_version=analysis.model_version,
            analyzed_at=format_utc_millis(analysis.analyzed_at),
        )
        if analysis is not None and analysis.status is SentimentStatus.COMPLETED
        else None
    )
    return NewsItemDto(
        news_id=str(item.id),
        title=item.title,
        content=item.content,
        source=item.source,
        published_at=format_utc_millis(item.published_at),
        crawled_at=format_utc_millis(item.crawled_at),
        related_coins=item.related_coins,
        url=item.url,
        sentiment=sentiment,
    )


def page_to_dto(
    page: NewsPage,
    sentiment_map: Mapping[UUID, NewsSentimentAnalysis] | None = None,
) -> NewsPageDto:
    return NewsPageDto(
        items=tuple(item_to_dto(item, sentiment_map) for item in page.items),
        page=page.page,
        page_size=page.page_size,
        total=page.total,
    )
