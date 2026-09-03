from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from crypto_lab.application.search_service import SearchEventHub, StrategySearchService
from crypto_lab.bootstrap.strategies import build_strategy_registry
from crypto_lab.domain.search import RandomSearchGenerator
from tests.fixtures.search_repository import MemoryRepository

pytestmark = pytest.mark.integration


class Clock:
    def now(self):
        return datetime.now(UTC)


class SearchUnderTest(StrategySearchService):
    async def _evaluate(self, row, candidate, sequence):
        await asyncio.sleep(0)
        return Decimal(sequence), UUID(int=sequence), UUID(int=sequence + 100)


async def test_generate_backtest_evaluate_rank_progress_reaches_candidate_limit() -> None:
    repository = MemoryRepository()
    service = SearchUnderTest(
        repository=repository,
        generator=RandomSearchGenerator(build_strategy_registry()),
        configurations=None,
        datasets=SimpleNamespace(
            get_complete=lambda _id: _value(
                SimpleNamespace(metadata=SimpleNamespace(candle_count=96))
            )
        ),
        analyzer=None,
        create_backtest=None,
        execute_backtest=None,
        evaluate_backtest=None,
        leaderboard=None,
        clock=Clock(),
        hub=SearchEventHub(),
        execution_policy=None,
        evaluation_policy=None,
        scoring_policy=None,
    )
    run = await service.create(
        dataset_id=uuid4(),
        strategy_ids=("ma", "rsi", "bollinger"),
        minimum_size=2,
        maximum_size=3,
        candidate_limit=3,
        timeout_seconds=60,
        no_improvement_limit=10,
        seed=7,
    )
    for _ in range(100):
        if repository.run.status == "COMPLETED":
            break
        await asyncio.sleep(0.01)

    assert run.status == "COMPLETED"
    assert run.stop_reason == "CANDIDATE_LIMIT"
    assert (run.generated, run.succeeded, run.failed, run.top_score) == (3, 3, 0, Decimal(3))
    assert [item.status for item in repository.items] == ["COMPLETED"] * 3
    await service.close()


async def _value(value):
    return value
