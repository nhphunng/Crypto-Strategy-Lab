"""Functional regression test for the news collect -> store -> query journey.

Walks the same sequence a deployment performs end to end: a provider yields
BTC + ETH feed items, `CollectNews` normalizes and persists them idempotently,
`GET /api/v1/news?coin=BTC` filters to the BTC story, and a provider failure
does not take down the health or Market routes nor the already-stored news.

Runs against the real PostgreSQL repository and the real ASGI app, but uses a
fake news provider so no public feed is reached.
"""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from crypto_lab.api.dependencies import Container, build_container
from crypto_lab.application.news.collect_news import CollectNews, NewsCollectionFailure
from crypto_lab.application.news.list_news import ListNews
from crypto_lab.application.news.ports import CollectedNewsItem
from crypto_lab.infrastructure.database import Database
from crypto_lab.infrastructure.settings import Settings
from crypto_lab.main import create_app
from tests.fixtures.news.fakes import (
    CRAWL_AT,
    FakeNewsProvider,
    FixedClock,
    collect_item,
)

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://crypto_lab:crypto_lab@localhost:55432/crypto_lab",
)


def _btc_item() -> CollectedNewsItem:
    return collect_item("btc", provider_item_id="pid-btc", related_coins=("BTC",))


def _eth_item() -> CollectedNewsItem:
    return collect_item("eth", provider_item_id="pid-eth", related_coins=("ETH",))


async def _truncate(database: Database) -> None:
    async with database.engine.begin() as connection:
        await connection.execute(text("TRUNCATE news_items CASCADE"))


async def _build_client() -> tuple[AsyncClient, Database, Container]:
    container = build_container(Settings(_env_file=None))
    database = container.database
    assert database is not None
    if not await database.ping():
        await database.dispose()
        pytest.skip("PostgreSQL integration database is unavailable")
    await _truncate(database)

    news_repository = container.news_repository
    assert news_repository is not None

    fake = FakeNewsProvider("RSS", (_btc_item(), _eth_item()))
    container.collect_news = CollectNews(
        (fake,), news_repository, clock=FixedClock(CRAWL_AT)
    )
    container.list_news = ListNews(news_repository, FixedClock(CRAWL_AT))

    app = create_app(container)
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    return client, database, container


def _collect(container: Container) -> CollectNews:
    assert container.collect_news is not None
    return container.collect_news


@pytest.mark.asyncio
async def test_collect_is_idempotent_and_query_filters_by_coin() -> None:
    client, database, container = await _build_client()
    try:
        first = await _collect(container).execute()
        assert (first.inserted, first.updated, first.unchanged) == (2, 0, 0)

        second = await _collect(container).execute()
        assert (second.inserted, second.updated, second.unchanged) == (0, 0, 2)

        response = await client.get("/api/v1/news", params={"coin": "BTC"})
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] == 1
        item = data["items"][0]
        assert item["title"] == "Title btc"
        assert item["content"] == "Content btc"
        assert item["source"] == "Example Source"
        assert item["relatedCoins"] == ["BTC"]
        assert item["sentiment"] is None
        assert item["url"].startswith("https://mirror.example.com/btc")
    finally:
        await client.aclose()
        await _truncate(database)
        await database.dispose()


@pytest.mark.asyncio
async def test_provider_failure_does_not_break_health_market_or_stored_news() -> None:
    client, database, container = await _build_client()
    try:
        await _collect(container).execute()

        failing = FakeNewsProvider("RSS", error=RuntimeError("provider down"))
        repository = container.news_repository
        assert repository is not None
        container.collect_news = CollectNews(
            (failing,),
            repository,
            clock=FixedClock(CRAWL_AT),
        )
        with pytest.raises(NewsCollectionFailure):
            await _collect(container).execute()

        live = await client.get("/health/live")
        assert live.status_code == 200
        assert live.json()["status"] == "UP"

        market = await client.get("/api/v1/market-data/dimensions")
        assert market.status_code == 200

        news = await client.get("/api/v1/news", params={"coin": "ETH"})
        assert news.status_code == 200
        assert news.json()["data"]["total"] == 1
    finally:
        await client.aclose()
        await _truncate(database)
        await database.dispose()
