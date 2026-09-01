from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from crypto_lab.application.news.ports import CollectedNewsItem, StoreNewsResult
from crypto_lab.domain.news.item import NewsItem

PUBLISHED_AT = datetime(2026, 8, 29, 10, 0, tzinfo=UTC)
CRAWL_AT = datetime(2026, 8, 29, 10, 5, tzinfo=UTC)


class FixedClock:
    """Clock that always reports the same instant, for deterministic crawl times."""

    def __init__(self, value: datetime) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


class SequenceIdFactory:
    """Injects monotonically increasing UUIDs so collection identity is deterministic."""

    def __init__(self, start: int = 1) -> None:
        self.next = start
        self.calls = 0

    def __call__(self) -> UUID:
        value = UUID(int=self.next)
        self.next += 1
        self.calls += 1
        return value


class FakeNewsProvider:
    """Provider stub that returns a fixed batch of items or raises on collect."""

    def __init__(
        self,
        provider: str,
        items: tuple[CollectedNewsItem, ...] = (),
        error: Exception | None = None,
    ) -> None:
        self.provider = provider
        self.items = items
        self.error = error
        self.collect_calls = 0

    async def collect(self) -> tuple[CollectedNewsItem, ...]:
        self.collect_calls += 1
        if self.error is not None:
            raise self.error
        return self.items


class FakeNewsRepository:
    """Repository stub that records upsert calls and returns a canned result."""

    def __init__(self, result: StoreNewsResult | None = None) -> None:
        self.result = result or StoreNewsResult(inserted=0, updated=0, unchanged=0)
        self.upsert_calls: list[tuple[object, ...]] = []

    async def upsert_many(self, items: tuple[NewsItem, ...]) -> StoreNewsResult:
        self.upsert_calls.append(items)
        return self.result

    async def list(self, query: object) -> object:  # pragma: no cover - unused by collect
        raise NotImplementedError


def collect_item(
    slug: str,
    *,
    canonical: str | None = None,
    provider_item_id: str | None = None,
    title: str | None = None,
    url: str | None = None,
    related_coins: tuple[str, ...] = ("BTC",),
) -> CollectedNewsItem:
    """Build a well-formed CollectedNewsItem keyed by a short slug."""
    return CollectedNewsItem(
        provider_item_id=provider_item_id or f"pid-{slug}",
        title=title or f"Title {slug}",
        content=f"Content {slug}",
        source="Example Source",
        published_at=PUBLISHED_AT,
        related_coins=related_coins,
        url=url or f"https://mirror.example.com/{slug}",
        canonical_url=canonical or f"https://example.com/{slug}",
    )


def stored(inserted: int = 0, updated: int = 0, unchanged: int = 0) -> StoreNewsResult:
    return StoreNewsResult(inserted=inserted, updated=updated, unchanged=unchanged)
