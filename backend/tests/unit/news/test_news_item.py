from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest

from crypto_lab.domain.news.item import NewsItem

PUBLISHED_AT = datetime(2026, 8, 29, 10, 0, tzinfo=UTC)
CRAWLED_AT = datetime(2026, 8, 29, 10, 5, tzinfo=UTC)


def _news_item(**overrides: object) -> NewsItem:
    values: dict[str, object] = {
        "id": UUID(int=1),
        "provider": "cryptopanic",
        "provider_item_id": "article-1",
        "title": "Bitcoin reaches a new high",
        "content": "Bitcoin moved above its prior high.",
        "source": "Example News",
        "published_at": PUBLISHED_AT,
        "crawled_at": CRAWLED_AT,
        "related_coins": ("BTC",),
        "url": "https://example.com/articles/1",
        "canonical_url": "https://example.com/articles/1",
    }
    values.update(overrides)
    return NewsItem(**values)  # type: ignore[arg-type]


def test_news_item_is_a_frozen_slotted_value_object() -> None:
    item = _news_item()

    assert item.id == UUID(int=1)
    assert not hasattr(item, "__dict__")
    with pytest.raises(FrozenInstanceError):
        item.title = "changed"  # type: ignore[misc]


def test_news_item_normalizes_text_coins_and_aware_datetimes() -> None:
    eastern = timezone(timedelta(hours=-4))

    item = NewsItem(
        id=UUID(int=1),
        provider="  crypto   panic  ",
        provider_item_id="  article-1  ",
        title="  Bitcoin\t reaches   a new high  ",
        content=" Bitcoin moved\nabove its prior high. ",
        source="  Example   News ",
        published_at=datetime(2026, 8, 29, 6, 0, tzinfo=eastern),
        crawled_at=datetime(2026, 8, 29, 6, 5, tzinfo=eastern),
        related_coins=(" eth ", "btc", "BTC", " ada "),
        url="  https://example.com/articles/1  ",
        canonical_url=" https://example.com/articles/1 ",
    )

    assert item.provider == "crypto panic"
    assert item.provider_item_id == "article-1"
    assert item.title == "Bitcoin reaches a new high"
    assert item.content == "Bitcoin moved above its prior high."
    assert item.source == "Example News"
    assert item.published_at == PUBLISHED_AT
    assert item.crawled_at == CRAWLED_AT
    assert item.related_coins == ("ADA", "BTC", "ETH")
    assert item.url == "https://example.com/articles/1"
    assert item.canonical_url == "https://example.com/articles/1"
    assert item.content_fingerprint == (
        "9bedf8697dd9a9228b7d450381ed3f585b2b57820abec057498bb163cfabf89a"
    )


@pytest.mark.parametrize(
    "field_name",
    ("provider", "provider_item_id", "title", "content", "source"),
)
def test_news_item_rejects_blank_required_text(field_name: str) -> None:
    with pytest.raises(ValueError, match=f"{field_name} must not be blank"):
        _news_item(**{field_name: " \t\n "})


@pytest.mark.parametrize("field_name", ("url", "canonical_url"))
@pytest.mark.parametrize("value", ("http://example.com/articles/1", "", "https:///missing-host"))
def test_news_item_rejects_non_https_urls(field_name: str, value: str) -> None:
    with pytest.raises(ValueError, match=f"{field_name} must be an HTTPS URL"):
        _news_item(**{field_name: value})


@pytest.mark.parametrize("field_name", ("published_at", "crawled_at"))
def test_news_item_rejects_naive_datetimes(field_name: str) -> None:
    with pytest.raises(ValueError, match=f"{field_name} must be timezone-aware"):
        _news_item(**{field_name: datetime(2026, 8, 29, 10, 0)})


def test_news_item_rejects_publication_after_crawl() -> None:
    with pytest.raises(ValueError, match="published_at must not be after crawled_at"):
        _news_item(published_at=CRAWLED_AT + timedelta(seconds=1))


def test_fingerprint_uses_only_normalized_title_content_and_canonical_url() -> None:
    original = _news_item()
    recrawled = _news_item(
        title=" Bitcoin   reaches a new high ",
        content="Bitcoin moved\nabove its prior high.",
        crawled_at=CRAWLED_AT + timedelta(hours=1),
        url="https://mirror.example.com/articles/1",
    )
    canonical_change = _news_item(canonical_url="https://example.com/articles/canonical-1")

    assert recrawled.content_fingerprint == original.content_fingerprint
    assert canonical_change.content_fingerprint != original.content_fingerprint


def test_news_application_dtos_are_frozen_slotted_boundary_values() -> None:
    from crypto_lab.application.news.ports import (
        CollectedNewsItem,
        NewsPage,
        NewsQuery,
        StoreNewsResult,
    )

    collected = CollectedNewsItem(
        provider_item_id="article-1",
        title="Bitcoin reaches a new high",
        content="Bitcoin moved above its prior high.",
        source="Example News",
        published_at=PUBLISHED_AT,
        related_coins=("BTC",),
        url="https://example.com/articles/1",
        canonical_url="https://example.com/articles/1",
    )
    query = NewsQuery(
        coin="BTC",
        published_after=PUBLISHED_AT,
        published_before=CRAWLED_AT,
        page=2,
        page_size=25,
    )
    page = NewsPage(items=(_news_item(),), page=2, page_size=25, total=26)
    result = StoreNewsResult(inserted=1, updated=2, unchanged=3)

    assert collected.provider_item_id == "article-1"
    assert query.page_size == 25
    assert page.items == (_news_item(),)
    assert page.total == 26
    assert result.total == 6
    for value in (collected, query, page, result):
        assert not hasattr(value, "__dict__")
        with pytest.raises(FrozenInstanceError):
            setattr(value, fields(value)[0].name, "changed")


@pytest.mark.asyncio
async def test_news_ports_accept_replaceable_typed_adapters() -> None:
    from crypto_lab.application.news.ports import (
        CollectedNewsItem,
        NewsPage,
        NewsProvider,
        NewsQuery,
        NewsRepository,
        StoreNewsResult,
    )

    collected = CollectedNewsItem(
        provider_item_id="article-1",
        title="Bitcoin reaches a new high",
        content="Bitcoin moved above its prior high.",
        source="Example News",
        published_at=PUBLISHED_AT,
        related_coins=("BTC",),
        url="https://example.com/articles/1",
        canonical_url="https://example.com/articles/1",
    )
    page = NewsPage(items=(_news_item(),), page=1, page_size=50, total=1)
    stored = StoreNewsResult(inserted=1, updated=0, unchanged=0)

    class FakeProvider:
        provider = "fake"

        async def collect(self) -> tuple[CollectedNewsItem, ...]:
            return (collected,)

    class FakeRepository:
        async def upsert_many(self, items: tuple[NewsItem, ...]) -> StoreNewsResult:
            return stored

        async def list(self, query: NewsQuery) -> NewsPage:
            return page

    provider: NewsProvider = FakeProvider()
    repository: NewsRepository = FakeRepository()
    query = NewsQuery(coin="BTC")

    assert provider.provider == "fake"
    assert await provider.collect() == (collected,)
    assert await repository.upsert_many((_news_item(),)) == stored
    assert await repository.list(query) == page
