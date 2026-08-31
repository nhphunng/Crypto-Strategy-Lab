from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID, uuid4

from crypto_lab.application.news.ports import (
    CollectedNewsItem,
    NewsProvider,
    NewsRepository,
    StoreNewsResult,
)
from crypto_lab.domain.news.item import NewsItem

logger = logging.getLogger(__name__)


class Clock(Protocol):
    """Reports the instant used to stamp every item's crawl time."""

    def now(self) -> datetime: ...


class NewsCollectionFailure(Exception):
    """Raised when every configured provider failed to yield any news."""

    def __init__(self, provider_failures: Mapping[str, Exception]) -> None:
        self.provider_failures = dict(provider_failures)
        providers = ", ".join(sorted(self.provider_failures)) or "none configured"
        super().__init__(f"All news providers failed: {providers}")


class CollectNews:
    """Collect from every configured provider and persist the merged batch once."""

    def __init__(
        self,
        providers: Sequence[NewsProvider],
        repository: NewsRepository,
        *,
        clock: Clock,
        id_factory: Callable[[], UUID] = uuid4,
    ) -> None:
        self._providers = providers
        self._repository = repository
        self._clock = clock
        self._id_factory = id_factory
        self.provider_failures: dict[str, Exception] = {}

    async def execute(self) -> StoreNewsResult:
        self.provider_failures = {}
        if not self._providers:
            return StoreNewsResult(inserted=0, updated=0, unchanged=0)

        collected: list[NewsItem] = []
        seen: set[str] = set()
        failed = 0
        for provider in self._providers:
            try:
                items = await provider.collect()
            except Exception as exc:
                logger.exception("news provider %s failed", provider.provider)
                self.provider_failures[provider.provider] = exc
                failed += 1
                continue
            self._extend(collected, seen, provider, items)

        if failed == len(self._providers):
            raise NewsCollectionFailure(self.provider_failures)
        if not collected:
            return StoreNewsResult(inserted=0, updated=0, unchanged=0)
        return await self._repository.upsert_many(tuple(collected))

    def _extend(
        self,
        collected: list[NewsItem],
        seen: set[str],
        provider: NewsProvider,
        items: tuple[CollectedNewsItem, ...],
    ) -> None:
        for raw in items:
            canonical_key = raw.canonical_url.strip()
            if canonical_key in seen:
                continue
            seen.add(canonical_key)
            collected.append(self._to_item(provider, raw))

    def _to_item(self, provider: NewsProvider, raw: CollectedNewsItem) -> NewsItem:
        return NewsItem(
            id=self._id_factory(),
            provider=provider.provider,
            provider_item_id=raw.provider_item_id,
            title=raw.title,
            content=raw.content,
            source=raw.source,
            published_at=raw.published_at,
            crawled_at=self._clock.now(),
            related_coins=raw.related_coins,
            url=raw.url,
            canonical_url=raw.canonical_url,
        )


__all__ = ["Clock", "CollectNews", "NewsCollectionFailure"]
