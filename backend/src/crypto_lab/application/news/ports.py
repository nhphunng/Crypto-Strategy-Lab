"""Transport-neutral DTOs and ports for news collection and storage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from crypto_lab.domain.news.item import NewsItem


@dataclass(frozen=True, slots=True)
class CollectedNewsItem:
    """Provider-neutral article data before application-assigned identity and crawl time."""

    provider_item_id: str
    title: str
    content: str
    source: str
    published_at: datetime
    related_coins: tuple[str, ...]
    url: str
    canonical_url: str


@dataclass(frozen=True, slots=True)
class NewsQuery:
    coin: str | None = None
    published_after: datetime | None = None
    published_before: datetime | None = None
    page: int = 1
    page_size: int = 50
    sentiment: str | None = None


@dataclass(frozen=True, slots=True)
class NewsPage:
    items: tuple[NewsItem, ...]
    page: int
    page_size: int
    total: int


@dataclass(frozen=True, slots=True)
class StoreNewsResult:
    inserted: int
    updated: int
    unchanged: int

    @property
    def total(self) -> int:
        return self.inserted + self.updated + self.unchanged


class NewsProvider(Protocol):
    provider: str

    async def collect(self) -> tuple[CollectedNewsItem, ...]: ...


class NewsRepository(Protocol):
    async def upsert_many(self, items: tuple[NewsItem, ...]) -> StoreNewsResult: ...

    async def list(self, query: NewsQuery) -> NewsPage: ...


__all__ = [
    "CollectedNewsItem",
    "NewsPage",
    "NewsProvider",
    "NewsQuery",
    "NewsRepository",
    "StoreNewsResult",
]
