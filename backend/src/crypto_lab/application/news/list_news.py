"""ListNews use case: read stored news with a safe default window and paging."""

from __future__ import annotations

from datetime import timedelta

from crypto_lab.application.market_data.ports import Clock
from crypto_lab.application.news.ports import NewsPage, NewsQuery, NewsRepository

DEFAULT_WINDOW_DAYS = 7


class ListNews:
    def __init__(self, repository: NewsRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    async def execute(self, query: NewsQuery) -> NewsPage:
        now = self._clock.now()
        resolved = NewsQuery(
            coin=query.coin,
            published_after=query.published_after or now - timedelta(days=DEFAULT_WINDOW_DAYS),
            published_before=query.published_before or now,
            page=query.page,
            page_size=query.page_size,
            sentiment=query.sentiment,
        )
        return await self._repository.list(resolved)
