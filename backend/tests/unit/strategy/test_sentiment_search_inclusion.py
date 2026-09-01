"""Proves NewsSentimentStrategy is a normal, uniformly-treated Strategy.

Registering it in a StrategyRegistry alongside MA and RSI is sufficient for
RandomSearchGenerator to produce an "MA + RSI + Sentiment" combination, and
for each member's `analyze()` to run against a shared context and produce
timestamp-aligned signals a composite analyzer can zip together -- with zero
special-casing anywhere in the search or composite-analysis machinery.
"""

from __future__ import annotations

from datetime import datetime
from inspect import isawaitable

import pytest
from tests.fixtures.strategy.factories import context, definition

from crypto_lab.application.sentiment.context_reader import SentimentDataPoint
from crypto_lab.domain.search import RandomSearchGenerator
from crypto_lab.domain.sentiment.model import ModelRef
from crypto_lab.domain.strategy.implementations.moving_average import MovingAverageStrategy
from crypto_lab.domain.strategy.implementations.news_sentiment import NewsSentimentStrategy
from crypto_lab.domain.strategy.implementations.rsi import RsiStrategy
from crypto_lab.domain.strategy.registry import StrategyRegistry
from crypto_lab.domain.strategy.signal import SignalPhase
from crypto_lab.domain.strategy.version import ContractVersionRange


class FakeSentimentContextReader:
    async def series(
        self, pair: str, start_time: datetime, end_time: datetime, model: ModelRef
    ) -> tuple[SentimentDataPoint, ...]:
        return ()


def _registry() -> StrategyRegistry:
    registry = StrategyRegistry(ContractVersionRange(major=1, minimum_minor=0, maximum_minor=0))
    registry.register_many(
        (
            MovingAverageStrategy(),
            RsiStrategy(),
            NewsSentimentStrategy(FakeSentimentContextReader(), ModelRef("fake-model", "1.0.0")),
        )
    )
    return registry


def test_random_search_generates_a_combination_containing_all_three_strategies() -> None:
    registry = _registry()
    generator = RandomSearchGenerator(registry)

    candidates = tuple(generator.generate(("ma", "rsi", "news_sentiment"), 3, 3, 5, seed=424242))

    assert len(candidates) == 5
    for candidate in candidates:
        member_ids = {member.strategy_id for member in candidate.members}
        assert member_ids == {"ma", "rsi", "news_sentiment"}


@pytest.mark.asyncio
async def test_all_three_members_analyze_against_a_shared_context_with_aligned_signals() -> None:
    registry = _registry()
    supplied = context(["10", "9", "8", "10", "12", "10"])

    results = []
    for entry in registry.discover():
        strategy = entry.strategy
        selected = definition(strategy, {})
        pending = strategy.analyze(selected, supplied)
        result = await pending if isawaitable(pending) else pending
        results.append(result)

    assert len(results) == 3
    aligned = tuple(zip(*(result.signals for result in results), strict=True))
    assert len(aligned) == len(supplied.candles)
    for children in aligned:
        timestamps = {child.timestamp for child in children}
        assert len(timestamps) == 1
    # The Sentiment member has no evidence (fake reader returns none), so it
    # stays in WARMUP -- proving the plumbing accepts an all-HOLD member
    # uniformly alongside MA/RSI, without any strategy-specific handling.
    sentiment_result = next(
        r for r in results if r.strategy_definition.strategy_id == "news_sentiment"
    )
    assert all(signal.phase is SignalPhase.WARMUP for signal in sentiment_result.signals)
