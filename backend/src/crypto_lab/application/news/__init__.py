"""News collection and persistence application boundaries."""

from crypto_lab.application.news.ports import (
    CollectedNewsItem,
    NewsPage,
    NewsProvider,
    NewsQuery,
    NewsRepository,
    StoreNewsResult,
)

__all__ = [
    "CollectedNewsItem",
    "NewsPage",
    "NewsProvider",
    "NewsQuery",
    "NewsRepository",
    "StoreNewsResult",
]
