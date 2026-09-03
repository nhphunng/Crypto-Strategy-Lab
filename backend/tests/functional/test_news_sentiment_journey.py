"""Opt-in real FinBERT -> PostgreSQL -> API regression, without public news feeds.

Set CSL_TEST_FINBERT_PATH to a directory from cache_sentiment_model.py and
TEST_DATABASE_URL to a disposable, migrated PostgreSQL database.
"""

from __future__ import annotations

import os
from dataclasses import replace

import pytest

from crypto_lab.application.news.collect_news import CollectNews
from crypto_lab.application.sentiment.analyze_pending_news import AnalyzePendingNews
from crypto_lab.infrastructure.sentiment.finbert_analyzer import (
    MODEL_ID,
    MODEL_VERSION,
    FinBertSentimentAnalyzer,
)
from tests.fixtures.news.fakes import CRAWL_AT, FakeNewsProvider, FixedClock
from tests.functional.test_news_journey import _btc_item, _build_client, _eth_item, _truncate


@pytest.mark.functional
async def test_real_ml_collect_store_analyze_filter_and_replay() -> None:
    model_path = os.getenv("CSL_TEST_FINBERT_PATH")
    if not model_path:
        pytest.skip("Set CSL_TEST_FINBERT_PATH to opt into real FinBERT inference")
    client, database, container = await _build_client()
    try:
        positive = "Bitcoin adoption drives strong profit growth and record revenue."
        negative = "Ethereum exchange reports severe losses and faces bankruptcy."
        items = (
            replace(_btc_item(), title=positive, content=positive),
            replace(_eth_item(), title=negative, content=negative),
        )
        assert container.news_repository is not None
        assert container.sentiment_repository is not None
        collection = CollectNews(
            (FakeNewsProvider("RSS", items),), container.news_repository, clock=FixedClock(CRAWL_AT)
        )
        await collection.execute()
        analyzer = AnalyzePendingNews(
            analyzer=FinBertSentimentAnalyzer(model_path),
            repository=container.sentiment_repository,
            clock=container.clock,
        )
        report = await analyzer.execute()
        assert (report.attempted, report.succeeded, report.failed) == (2, 2, 0)
        assert (await analyzer.execute()).attempted == 0

        page = (await client.get("/api/v1/news")).json()["data"]
        assert page["total"] == 2
        assert {item["sentiment"]["label"] for item in page["items"]} == {"POSITIVE", "NEGATIVE"}
        for item in page["items"]:
            assert item["sentiment"]["modelId"] == MODEL_ID
            assert item["sentiment"]["modelVersion"] == MODEL_VERSION
            assert 0 < float(item["sentiment"]["score"]) < 1

        filtered = (
            await client.get("/api/v1/news", params={"sentiment": "NEGATIVE", "pageSize": 1})
        ).json()["data"]
        assert filtered["total"] == 1
        assert filtered["items"][0]["relatedCoins"] == ["ETH"]
        second = (
            await client.get(
                "/api/v1/news", params={"sentiment": "NEGATIVE", "pageSize": 1, "page": 2}
            )
        ).json()["data"]
        assert second["total"] == 1
        assert second["items"] == []
        assert (await client.get("/api/v1/news?sentiment=INVALID")).status_code == 400
        status = (await client.get("/api/v1/sentiment/status")).json()["data"]
        assert status == {"pending": 0, "analyzed": 2, "failed": 0}
        strategies = (await client.get("/api/v1/strategies")).json()["data"]["strategies"]
        assert "news_sentiment" in {strategy["strategyId"] for strategy in strategies}

        # An edited article must not show or filter by its stale sentiment.
        revised = replace(items[1], title="Ethereum update", content="Results due on Tuesday.")
        await CollectNews(
            (FakeNewsProvider("RSS", (revised,)),),
            container.news_repository,
            clock=FixedClock(CRAWL_AT),
        ).execute()
        assert (await client.get("/api/v1/news?sentiment=NEGATIVE")).json()["data"]["total"] == 0
        eth = (await client.get("/api/v1/news?coin=ETH")).json()["data"]["items"][0]
        assert eth["sentiment"] is None
    finally:
        await client.aclose()
        await _truncate(database)
        await container.close()
