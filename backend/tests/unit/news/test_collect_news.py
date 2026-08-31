from __future__ import annotations

from datetime import timedelta
from typing import cast
from uuid import UUID

import pytest
from tests.fixtures.news.fakes import (
    CRAWL_AT,
    PUBLISHED_AT,
    FakeNewsProvider,
    FakeNewsRepository,
    FixedClock,
    SequenceIdFactory,
    collect_item,
    stored,
)

from crypto_lab.application.news.collect_news import CollectNews, NewsCollectionFailure
from crypto_lab.domain.news.item import NewsItem


def _make(
    providers: tuple[FakeNewsProvider, ...] = (),
    result=None,
    *,
    clock=FixedClock(CRAWL_AT),
    id_factory: SequenceIdFactory | None = None,
) -> tuple[CollectNews, FakeNewsRepository]:
    if id_factory is None:
        id_factory = SequenceIdFactory()
    repository = FakeNewsRepository(result)
    use_case = CollectNews(
        providers,
        repository,
        clock=clock,
        id_factory=id_factory,
    )
    return use_case, repository


@pytest.mark.asyncio
async def test_combines_providers_and_persists_exactly_once() -> None:
    provider_a = FakeNewsProvider("a", (collect_item("one"), collect_item("two")))
    provider_b = FakeNewsProvider("b", (collect_item("three"),))
    use_case, repository = _make((provider_a, provider_b), result=stored(inserted=3))

    result = await use_case.execute()

    assert result == stored(inserted=3)
    assert len(repository.upsert_calls) == 1
    persisted = repository.upsert_calls[0]
    assert [item.canonical_url for item in persisted] == [
        "https://example.com/one",
        "https://example.com/two",
        "https://example.com/three",
    ]
    assert [item.id for item in persisted] == [UUID(int=1), UUID(int=2), UUID(int=3)]
    assert all(item.crawled_at == CRAWL_AT for item in persisted)
    assert provider_a.collect_calls == 1
    assert provider_b.collect_calls == 1


@pytest.mark.asyncio
async def test_converts_collected_item_to_news_item_with_injected_clock_and_id() -> None:
    use_case, repository = _make((FakeNewsProvider("cryptopanic", (collect_item("lead"),)),))

    await use_case.execute()

    persisted = repository.upsert_calls[0]
    assert len(persisted) == 1
    item = cast(NewsItem, persisted[0])
    assert item.id == UUID(int=1)
    assert item.provider == "cryptopanic"
    assert item.provider_item_id == "pid-lead"
    assert item.published_at == PUBLISHED_AT
    assert item.crawled_at == CRAWL_AT
    assert item.title == "Title lead"
    assert item.source == "Example Source"
    assert item.content_fingerprint


@pytest.mark.asyncio
async def test_collapses_duplicate_canonical_urls_across_providers_keeping_first() -> None:
    shared = "https://example.com/shared"
    provider_a = FakeNewsProvider(
        "a",
        (collect_item("x", canonical=shared, url="https://mirror.example.com/x"),),
    )
    provider_b = FakeNewsProvider(
        "b",
        (collect_item("y", canonical=shared, url="https://mirror.example.com/y"),),
    )
    use_case, repository = _make((provider_a, provider_b))

    await use_case.execute()

    persisted = repository.upsert_calls[0]
    assert len(persisted) == 1
    kept = cast(NewsItem, persisted[0])
    assert kept.canonical_url == shared
    assert kept.url == "https://mirror.example.com/x"
    assert kept.provider == "a"


@pytest.mark.asyncio
async def test_collapse_is_deterministic_across_repeated_runs() -> None:
    shared = "https://example.com/shared"
    providers = (
        FakeNewsProvider("a", (collect_item("x", canonical=shared),)),
        FakeNewsProvider("b", (collect_item("y", canonical=shared),)),
    )
    first, first_repo = _make(providers)
    await first.execute()
    second, second_repo = _make(providers)
    await second.execute()

    assert first_repo.upsert_calls == second_repo.upsert_calls


@pytest.mark.asyncio
async def test_preserves_store_news_result_counts() -> None:
    use_case, repository = _make(
        (FakeNewsProvider("a", (collect_item("one"),)),), result=stored(2, 1, 3)
    )

    result = await use_case.execute()

    assert result == stored(2, 1, 3)
    assert result.total == 6


@pytest.mark.asyncio
async def test_isolates_single_provider_failure_and_records_it() -> None:
    boom = RuntimeError("provider a is down")
    provider_a = FakeNewsProvider("a", error=boom)
    provider_b = FakeNewsProvider("b", (collect_item("ok"),))
    use_case, repository = _make((provider_a, provider_b))

    result = await use_case.execute()

    assert result == stored(0, 0, 0)
    persisted = repository.upsert_calls[0]
    assert [item.provider for item in persisted] == ["b"]
    assert use_case.provider_failures == {"a": boom}
    assert provider_a.collect_calls == 1


@pytest.mark.asyncio
async def test_records_a_failure_per_provider() -> None:
    a_boom = RuntimeError("a")
    b_boom = ConnectionError("b")
    use_case, _ = _make(
        (FakeNewsProvider("a", error=a_boom), FakeNewsProvider("b", error=b_boom))
    )

    with pytest.raises(NewsCollectionFailure) as caught:
        await use_case.execute()

    assert caught.value.provider_failures == {"a": a_boom, "b": b_boom}


@pytest.mark.asyncio
async def test_raises_typed_failure_when_all_providers_fail_without_persisting() -> None:
    use_case, repository = _make(
        (
            FakeNewsProvider("a", error=RuntimeError("a")),
            FakeNewsProvider("b", error=RuntimeError("b")),
        )
    )

    with pytest.raises(NewsCollectionFailure):
        await use_case.execute()

    assert repository.upsert_calls == []


@pytest.mark.asyncio
async def test_no_providers_is_a_successful_no_op() -> None:
    use_case, repository = _make()

    result = await use_case.execute()

    assert result == stored(0, 0, 0)
    assert repository.upsert_calls == []


@pytest.mark.asyncio
async def test_id_factory_is_not_consumed_for_collapsed_duplicates() -> None:
    shared = "https://example.com/shared"
    factory = SequenceIdFactory()
    use_case, repository = _make(
        (
            FakeNewsProvider("a", (collect_item("x", canonical=shared),)),
            FakeNewsProvider(
                "b",
                (collect_item("y", canonical=shared, url="https://mirror.example.com/y"),),
            ),
        ),
        id_factory=factory,
    )

    await use_case.execute()

    assert factory.calls == 1
    assert repository.upsert_calls[0][0].id == UUID(int=1)


@pytest.mark.asyncio
async def test_persisted_item_published_at_cannot_be_after_crawl_clock() -> None:
    use_case, _ = _make(
        (FakeNewsProvider("a", (collect_item("late"),)),),
        clock=FixedClock(PUBLISHED_AT - timedelta(minutes=10)),
    )

    with pytest.raises(ValueError, match="published_at must not be after crawled_at"):
        await use_case.execute()
