"""Real offline FinBERT, durable candidate queue, backtest and leaderboard acceptance."""

from __future__ import annotations

import asyncio
import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from crypto_lab.api.dependencies import build_container
from crypto_lab.application.evaluations.auto_evaluate import SearchLoopPipeline, SearchLoopSettings
from crypto_lab.application.news.collect_news import CollectNews
from crypto_lab.application.sentiment.analyze_pending_news import AnalyzePendingNews
from crypto_lab.domain.market_data.candle import MarketSelection
from crypto_lab.domain.market_data.ranges import TimeRange
from crypto_lab.domain.market_data.timeframe import Timeframe
from crypto_lab.infrastructure.sentiment.finbert_analyzer import (
    MODEL_ID,
    MODEL_VERSION,
    FinBertSentimentAnalyzer,
)
from crypto_lab.infrastructure.settings import Settings
from crypto_lab.main import create_app
from tests.fixtures.news.fakes import FakeNewsProvider, FixedClock, collect_item
from tests.fixtures.strategy.factories import candles

pytestmark = pytest.mark.functional


async def test_real_sentiment_composite_search_persists_replayable_ranked_results(
    backtest_database,
):
    model_path = os.getenv("CSL_TEST_FINBERT_PATH")
    if not model_path:
        pytest.skip("Set CSL_TEST_FINBERT_PATH to run real offline FinBERT acceptance")
    database = backtest_database
    container = build_container(
        Settings(
            database_url=str(database.engine.url.render_as_string(hide_password=False)),
            _env_file=None,
        )
    )
    app = create_app(container)
    start = datetime(2026, 8, 19, tzinfo=UTC)
    end = start + timedelta(hours=60)
    async with database.engine.begin() as conn:
        await conn.execute(text("TRUNCATE news_items CASCADE"))
    try:
        await container.initialize_backtest_evaluation()
        analyzer = FinBertSentimentAnalyzer(model_path)
        for index, (at, headline) in enumerate(
            (
                (start, "Bitcoin adoption drives strong profit growth and record revenue."),
                (
                    start + timedelta(hours=31),
                    "Bitcoin exchange reports severe losses and faces bankruptcy.",
                ),
            )
        ):
            article = replace(
                collect_item(f"sentiment-search-{index}"),
                title=headline,
                content=headline,
                related_coins=("BTC",),
                published_at=at,
            )
            await CollectNews(
                (FakeNewsProvider("RSS", (article,)),),
                container.news_repository,
                clock=FixedClock(at),
            ).execute()
            report = await AnalyzePendingNews(
                analyzer=analyzer, repository=container.sentiment_repository, clock=FixedClock(at)
            ).execute()
            assert report.succeeded == 1
        values = candles(
            [str(100 + (index % 8) * 3) for index in range(240)],
            start=start,
            timeframe=Timeframe.FIFTEEN_MINUTES,
        )
        market = container.repository
        await market.store_closed_candles(values)
        claim = await market.claim_dataset(
            MarketSelection("BINANCE", "BTCUSDT", Timeframe.FIFTEEN_MINUTES),
            TimeRange(start, end),
            end,
            timedelta(minutes=5),
        )
        dataset = await market.finalize_dataset(claim.dataset.id, claim.build_token, values, end)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            board_query = dict(
                scoringPolicyId="balanced", scoringPolicyVersion="1.0.0", rankBy="OVERALL_SCORE"
            )
            initial = await client.get("/api/v1/leaderboards", params=board_query)
            assert initial.status_code == 200, initial.text
            # Seed 258 selects one evidence item and a 59-hour lookback, allowing
            # this small fixture to exercise actual sentiment decisions.
            response = await client.post(
                "/api/v1/search-runs",
                json=dict(
                    datasetId=str(dataset.id),
                    strategyIds=["ma", "rsi", "news_sentiment"],
                    minimumSize=3,
                    maximumSize=3,
                    candidateLimit=1,
                    timeoutSeconds=60,
                    noImprovementLimit=1,
                    seed=258,
                ),
            )
            assert response.status_code == 201, response.text
            search_id = UUID(response.json()["data"]["id"])
            run = await asyncio.wait_for(container.strategy_search.wait(search_id), 60)
            assert (run.status, run.succeeded, run.failed) == ("COMPLETED", 1, 0), (
                run.failure_detail
            )
            candidates = (await client.get(f"/api/v1/search-runs/{search_id}/candidates")).json()[
                "data"
            ]
            candidate = candidates[0]
            assert {member["strategyId"] for member in candidate["members"]} == {
                "ma",
                "rsi",
                "news_sentiment",
            }
            backtest_id = UUID(candidate["backtestRunId"])
            result = await container.backtest_repository.get_result_for_run(backtest_id)
            assert result is not None
            provenance = result.configuration.sentiment_provenance
            assert len(provenance) == 1
            assert (provenance[0].model_id, provenance[0].model_version) == (
                MODEL_ID,
                MODEL_VERSION,
            )
            assert provenance[0].window_end <= end
            assert len(provenance[0].evidence_fingerprint) == 64
            changed = replace(
                result.configuration,
                sentiment_provenance=(replace(provenance[0], model_version="different"),),
            )
            assert changed.input_fingerprint != result.configuration.input_fingerprint
            assert len(result.trades) > 0
            replay = await container.execute_backtest.execute(backtest_id, "replay")
            assert replay.result_checksum == result.result_checksum
            evaluation = await container.evaluation_repository.get(
                UUID(candidate["evaluationResultId"])
            )
            assert evaluation is not None
            board = await client.get("/api/v1/leaderboards", params=board_query)
            assert board.status_code == 200, board.text
            assert str(evaluation.id) in board.text

            # Background scheduling uses that same persisted executor and survives
            # coordinator recreation without inserting another search or candidate.
            class Materialized:
                async def materialize(self, *args, **kwargs):
                    from types import SimpleNamespace

                    return SimpleNamespace(dataset=dataset, building=False)

            class Discovery:
                def list(self):
                    return tuple(
                        entry
                        for entry in container.strategy_discovery.list()
                        if entry.strategy_id in ("ma", "rsi", "news_sentiment")
                    )

            settings = SearchLoopSettings(
                candles=240, minimum_size=3, maximum_size=3, candidates_per_cycle=1, base_seed=258
            )

            def pipeline():
                return SearchLoopPipeline(
                    settings=settings,
                    datasets=Materialized(),
                    discovery=Discovery(),
                    search=container.strategy_search,
                    clock=FixedClock(end),
                )

            first = await pipeline().run_cycle(0)
            second = await pipeline().run_cycle(0)
            assert first == second
            assert first.succeeded == 1
            assert await pipeline().restore() == 1
            assert (await pipeline().snapshot()).candidates_succeeded == 1
            all_runs = (await client.get("/api/v1/search-runs")).json()["data"]
            assert len([r for r in all_runs if r["origin"] == "BACKGROUND"]) == 1
    finally:
        await container.close()
        async with database.engine.begin() as conn:
            await conn.execute(text("TRUNCATE news_items CASCADE"))
