"""News list DTOs aligned to the TV5 contract.

JSON is camelCase and instants are UTC ISO-8601 millisecond strings. Task 3
always projects ``sentiment`` as ``null``; the analysis fields are reserved so
Task 4 can fill them without a contract change.
"""

from __future__ import annotations

from pydantic import Field

from crypto_lab.api.common import ApiModel
from crypto_lab.application.news.ports import NewsPage
from crypto_lab.domain.market_data.candle import format_utc_millis
from crypto_lab.domain.news.item import NewsItem


class SentimentAnalysisDto(ApiModel):
    """Reserved analysis payload; Task 3 always projects ``null``."""

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


def item_to_dto(item: NewsItem) -> NewsItemDto:
    # The Task 3 mapper always projects the reserved analysis payload as null.
    return NewsItemDto(
        news_id=str(item.id),
        title=item.title,
        content=item.content,
        source=item.source,
        published_at=format_utc_millis(item.published_at),
        crawled_at=format_utc_millis(item.crawled_at),
        related_coins=item.related_coins,
        url=item.url,
        sentiment=None,
    )


def page_to_dto(page: NewsPage) -> NewsPageDto:
    return NewsPageDto(
        items=tuple(item_to_dto(item) for item in page.items),
        page=page.page,
        page_size=page.page_size,
        total=page.total,
    )
