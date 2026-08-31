from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from crypto_lab.application.news.ports import NewsQuery
from crypto_lab.domain.news.item import NewsItem
from crypto_lab.infrastructure.persistence.repositories.news_repository import (
    SqlAlchemyNewsRepository,
)

pytestmark = pytest.mark.integration

PUBLISHED_AT = datetime(2026, 8, 29, 10, 0, tzinfo=UTC)


def _make_item(**overrides: object) -> NewsItem:
    values: dict[str, object] = {
        "id": UUID(int=1),
        "provider": "cryptopanic",
        "provider_item_id": "article-1",
        "title": "Bitcoin reaches a new high",
        "content": "Bitcoin moved above its prior high.",
        "source": "Example News",
        "published_at": PUBLISHED_AT,
        "crawled_at": PUBLISHED_AT + timedelta(minutes=5),
        "related_coins": ("BTC",),
        "url": "https://example.com/articles/1",
        "canonical_url": "https://example.com/articles/1",
    }
    values.update(overrides)
    return NewsItem(**values)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_insert_persists_items_and_counts_only_inserts(
    news_repository: SqlAlchemyNewsRepository,
) -> None:
    original = _make_item()

    result = await news_repository.upsert_many((original,))

    assert (result.inserted, result.updated, result.unchanged) == (1, 0, 0)
    page = await news_repository.list(NewsQuery())
    assert page.total == 1
    assert page.items == (original,)


@pytest.mark.asyncio
async def test_unchanged_rerun_is_idempotent_and_preserves_identity(
    news_repository: SqlAlchemyNewsRepository,
) -> None:
    first = _make_item()
    await news_repository.upsert_many((first,))

    result = await news_repository.upsert_many((first,))

    assert (result.inserted, result.updated, result.unchanged) == (0, 0, 1)
    page = await news_repository.list(NewsQuery())
    assert page.total == 1
    assert page.items[0].id == first.id
    assert page.items[0].published_at == first.published_at
    assert page.items[0].provider == first.provider
    assert page.items[0].provider_item_id == first.provider_item_id


@pytest.mark.asyncio
async def test_changed_identity_updates_mutable_fields_but_keeps_identity_and_published_at(
    news_repository: SqlAlchemyNewsRepository,
) -> None:
    initial = _make_item()
    await news_repository.upsert_many((initial,))

    revised = _make_item(
        title="Bitcoin dips by the close",
        content="Bitcoin traded lower into the close.",
        source="Updated Desk",
        url="https://example.com/articles/1?v=2",
        canonical_url="https://example.com/articles/canonical-1",
        related_coins=("BTC", "ETH"),
        crawled_at=PUBLISHED_AT + timedelta(hours=1),
    )
    result = await news_repository.upsert_many((revised,))

    assert (result.inserted, result.updated, result.unchanged) == (0, 1, 0)
    page = await news_repository.list(NewsQuery())
    assert page.total == 1
    stored = page.items[0]
    assert stored.id == initial.id
    assert stored.provider == initial.provider
    assert stored.provider_item_id == initial.provider_item_id
    assert stored.published_at == initial.published_at
    assert stored.title == revised.title
    assert stored.content == revised.content
    assert stored.source == revised.source
    assert stored.url == revised.url
    assert stored.canonical_url == revised.canonical_url
    assert stored.related_coins == revised.related_coins
    assert stored.crawled_at == revised.crawled_at
    assert stored.content_fingerprint == revised.content_fingerprint


@pytest.mark.asyncio
async def test_same_canonical_url_from_another_provider_does_not_duplicate_or_rewrite(
    news_repository: SqlAlchemyNewsRepository,
) -> None:
    owner = _make_item(
        id=UUID(int=1),
        provider="cryptopanic",
        provider_item_id="article-1",
        title="Bitcoin reaches a new high",
        source="Example News",
        url="https://example.com/articles/1",
        canonical_url="https://example.com/articles/1",
        related_coins=("BTC",),
    )
    await news_repository.upsert_many((owner,))

    other_provider = _make_item(
        id=UUID(int=2),
        provider="coindesk",
        provider_item_id="article-2",
        title="Bitcoin reaches a new high",
        source="CoinDesk",
        url="https://example.com/articles/1",
        canonical_url="https://example.com/articles/1",
        related_coins=("BTC",),
    )
    result = await news_repository.upsert_many((other_provider,))

    assert (result.inserted, result.updated, result.unchanged) == (0, 0, 1)
    page = await news_repository.list(NewsQuery())
    assert page.total == 1
    assert page.items[0].id == owner.id
    assert page.items[0].source == owner.source
    assert page.items[0].provider == owner.provider


@pytest.mark.asyncio
async def test_list_filters_by_exact_coin_array_membership(
    news_repository: SqlAlchemyNewsRepository,
) -> None:
    btc = _make_item(
        id=UUID(int=1),
        provider_item_id="article-1",
        related_coins=("BTC", "ETH"),
        published_at=PUBLISHED_AT + timedelta(minutes=1),
    )
    eth = _make_item(
        id=UUID(int=2),
        provider_item_id="article-2",
        related_coins=("ETH",),
        content="Ethereum outperformed.",
        title="Ethereum outperforms",
        url="https://example.com/articles/2",
        canonical_url="https://example.com/articles/2",
        published_at=PUBLISHED_AT + timedelta(minutes=2),
    )
    await news_repository.upsert_many((btc, eth))

    page = await news_repository.list(NewsQuery(coin="BTC"))

    assert page.total == 1
    assert page.items[0].id == btc.id


@pytest.mark.asyncio
async def test_list_half_open_published_range(
    news_repository: SqlAlchemyNewsRepository,
) -> None:
    before = _make_item(
        id=UUID(int=1),
        provider_item_id="before",
        published_at=PUBLISHED_AT - timedelta(seconds=1),
    )
    at_start = _make_item(
        id=UUID(int=2),
        provider_item_id="start",
        published_at=PUBLISHED_AT,
        title="At start",
        url="https://example.com/start",
        canonical_url="https://example.com/start",
    )
    at_end = _make_item(
        id=UUID(int=3),
        provider_item_id="end",
        published_at=PUBLISHED_AT + timedelta(minutes=1),
        title="At end",
        url="https://example.com/end",
        canonical_url="https://example.com/end",
    )
    after = _make_item(
        id=UUID(int=4),
        provider_item_id="after",
        published_at=PUBLISHED_AT + timedelta(minutes=2),
        title="After",
        url="https://example.com/after",
        canonical_url="https://example.com/after",
    )
    await news_repository.upsert_many((before, at_start, at_end, after))

    page = await news_repository.list(
        NewsQuery(
            published_after=PUBLISHED_AT,
            published_before=PUBLISHED_AT + timedelta(minutes=1),
        )
    )

    assert page.total == 1
    assert page.items[0].id == at_start.id


@pytest.mark.asyncio
async def test_list_orders_by_published_desc_then_id_asc_with_total_and_pagination(
    news_repository: SqlAlchemyNewsRepository,
) -> None:
    items = tuple(
        _make_item(
            id=UUID(int=index + 1),
            provider_item_id=f"article-{index + 1}",
            published_at=PUBLISHED_AT + timedelta(minutes=index),
            title=f"Article {index + 1}",
            url=f"https://example.com/articles/{index + 1}",
            canonical_url=f"https://example.com/articles/{index + 1}",
        )
        for index in range(5)
    )
    await news_repository.upsert_many(items)

    first = await news_repository.list(NewsQuery(page=1, page_size=2))
    second = await news_repository.list(NewsQuery(page=2, page_size=2))

    assert first.total == 5
    assert second.total == 5
    assert first.page_size == 2
    assert [item.id for item in first.items] == [UUID(int=5), UUID(int=4)]
    assert [item.id for item in second.items] == [UUID(int=3), UUID(int=2)]
