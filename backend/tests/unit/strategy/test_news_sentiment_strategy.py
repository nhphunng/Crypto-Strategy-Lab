from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from tests.fixtures.strategy.factories import context, definition

from crypto_lab.application.sentiment.context_reader import SentimentDataPoint
from crypto_lab.domain.sentiment.model import ModelRef
from crypto_lab.domain.strategy.context import StrategyContext
from crypto_lab.domain.strategy.definition import StrategyDefinition
from crypto_lab.domain.strategy.errors import StrategyError
from crypto_lab.domain.strategy.implementations.news_sentiment import NewsSentimentStrategy
from crypto_lab.domain.strategy.signal import HistoryState, SignalAction, SignalPhase

MODEL = ModelRef("fake-model", "1.0.0")


class FakeSentimentContextReader:
    def __init__(self, points: tuple[SentimentDataPoint, ...] = ()) -> None:
        self.points = points
        self.calls: list[tuple[str, datetime, datetime, ModelRef]] = []

    async def series(
        self, pair: str, start_time: datetime, end_time: datetime, model: ModelRef
    ) -> tuple[SentimentDataPoint, ...]:
        self.calls.append((pair, start_time, end_time, model))
        return self.points


def _context(hours: int = 3) -> StrategyContext:
    return context([str(index + 1) for index in range(hours)])


def _definition(strategy: NewsSentimentStrategy, **raw: object) -> StrategyDefinition:
    return definition(strategy, raw)


@pytest.mark.asyncio
async def test_evidence_published_after_the_candles_close_is_excluded() -> None:
    # A single-candle context: the one point would satisfy minEvidenceCount=1
    # (and score high enough to BUY) if it were counted -- proving it is
    # excluded, rather than merely absent, requires exactly this shape.
    supplied = _context(hours=1)
    candle = supplied.candles[0]
    late_point = SentimentDataPoint(
        published_at=candle.close_time + timedelta(seconds=1),
        analyzed_at=candle.open_time,
        signed_score=Decimal("1"),
    )
    reader = FakeSentimentContextReader((late_point,))
    strategy = NewsSentimentStrategy(reader, MODEL)
    selected = _definition(strategy, lookbackHours=100, minEvidenceCount=1)

    result = await strategy.analyze(selected, supplied)

    signal = result.signals[0]
    assert signal.phase is SignalPhase.WARMUP
    assert signal.action is SignalAction.HOLD
    assert signal.reason == "insufficient_evidence"


@pytest.mark.asyncio
async def test_evidence_analyzed_after_the_candles_close_is_excluded() -> None:
    supplied = _context(hours=1)
    candle = supplied.candles[0]
    late_analysis_point = SentimentDataPoint(
        published_at=candle.open_time,
        analyzed_at=candle.close_time + timedelta(seconds=1),
        signed_score=Decimal("1"),
    )
    reader = FakeSentimentContextReader((late_analysis_point,))
    strategy = NewsSentimentStrategy(reader, MODEL)
    selected = _definition(strategy, lookbackHours=100, minEvidenceCount=1)

    result = await strategy.analyze(selected, supplied)

    signal = result.signals[0]
    assert signal.phase is SignalPhase.WARMUP
    assert signal.action is SignalAction.HOLD
    assert signal.reason == "insufficient_evidence"


@pytest.mark.asyncio
async def test_below_minimum_evidence_count_holds_in_warmup() -> None:
    supplied = _context(hours=1)
    candle = supplied.candles[0]
    one_point = SentimentDataPoint(
        published_at=candle.open_time,
        analyzed_at=candle.open_time,
        signed_score=Decimal("1"),
    )
    reader = FakeSentimentContextReader((one_point,))
    strategy = NewsSentimentStrategy(reader, MODEL)
    selected = _definition(strategy, lookbackHours=24, minEvidenceCount=3)

    result = await strategy.analyze(selected, supplied)

    assert result.signals[0].phase is SignalPhase.WARMUP
    assert result.signals[0].action is SignalAction.HOLD
    assert result.history_state is HistoryState.INSUFFICIENT


def _evidence_points(candle_open: datetime, scores: list[str]) -> tuple[SentimentDataPoint, ...]:
    return tuple(
        SentimentDataPoint(
            published_at=candle_open,
            analyzed_at=candle_open,
            signed_score=Decimal(score),
        )
        for score in scores
    )


@pytest.mark.asyncio
async def test_average_at_or_above_buy_threshold_triggers_buy() -> None:
    supplied = _context(hours=1)
    candle = supplied.candles[0]
    points = _evidence_points(candle.open_time, ["0.5", "0.5", "0.5"])
    reader = FakeSentimentContextReader(points)
    strategy = NewsSentimentStrategy(reader, MODEL)
    selected = _definition(
        strategy,
        lookbackHours=24,
        minEvidenceCount=3,
        buyThreshold=Decimal("0.2"),
        sellThreshold=Decimal("-0.2"),
    )

    result = await strategy.analyze(selected, supplied)

    signal = result.signals[0]
    assert signal.phase is SignalPhase.EVALUATED
    assert signal.action is SignalAction.BUY
    assert signal.reason == "sentiment_above_buy_threshold"


@pytest.mark.asyncio
async def test_average_at_or_below_sell_threshold_triggers_sell() -> None:
    supplied = _context(hours=1)
    candle = supplied.candles[0]
    points = _evidence_points(candle.open_time, ["-0.5", "-0.5", "-0.5"])
    reader = FakeSentimentContextReader(points)
    strategy = NewsSentimentStrategy(reader, MODEL)
    selected = _definition(
        strategy,
        lookbackHours=24,
        minEvidenceCount=3,
        buyThreshold=Decimal("0.2"),
        sellThreshold=Decimal("-0.2"),
    )

    result = await strategy.analyze(selected, supplied)

    signal = result.signals[0]
    assert signal.phase is SignalPhase.EVALUATED
    assert signal.action is SignalAction.SELL
    assert signal.reason == "sentiment_below_sell_threshold"


@pytest.mark.asyncio
async def test_average_between_thresholds_holds_evaluated() -> None:
    supplied = _context(hours=1)
    candle = supplied.candles[0]
    points = _evidence_points(candle.open_time, ["0.05", "-0.05", "0.0"])
    reader = FakeSentimentContextReader(points)
    strategy = NewsSentimentStrategy(reader, MODEL)
    selected = _definition(
        strategy,
        lookbackHours=24,
        minEvidenceCount=3,
        buyThreshold=Decimal("0.2"),
        sellThreshold=Decimal("-0.2"),
    )

    result = await strategy.analyze(selected, supplied)

    signal = result.signals[0]
    assert signal.phase is SignalPhase.EVALUATED
    assert signal.action is SignalAction.HOLD
    assert signal.reason == "sentiment_within_neutral_band"


@pytest.mark.asyncio
async def test_relationship_rule_rejects_sell_threshold_not_below_buy_threshold() -> None:
    reader = FakeSentimentContextReader(())
    strategy = NewsSentimentStrategy(reader, MODEL)

    with pytest.raises(StrategyError):
        strategy.validate_parameters({"buyThreshold": "0.2", "sellThreshold": "0.3"})


async def test_evidence_and_model_are_part_of_signal_and_context_identity() -> None:
    from dataclasses import replace

    supplied = _context(2)
    point = SentimentDataPoint(
        supplied.range_start,
        supplied.range_start,
        Decimal("0.8"),
        news_id="news",
        analysis_id="analysis",
        content_fingerprint="a" * 64,
    )
    reader = FakeSentimentContextReader((point,))
    strategy = NewsSentimentStrategy(reader, MODEL)
    selected = _definition(strategy, minEvidenceCount=1)
    first = await strategy.analyze(selected, supplied)
    reader.points = (replace(point, signed_score=Decimal("-0.8")),)
    changed = await strategy.analyze(selected, supplied)
    assert first.signals[0].action != changed.signals[0].action
    assert first.signals[0].id != changed.signals[0].id
    assert (
        first.context_provenance.context_fingerprint
        != changed.context_provenance.context_fingerprint
    )
    provenance = first.context_provenance.sentiment[0]
    assert provenance.model_id == MODEL.model_id
    assert provenance.window_end == supplied.decision_timestamp
    reader.points = (point,)
    other_model = NewsSentimentStrategy(reader, ModelRef(MODEL.model_id, "2.0.0"))
    assert (await other_model.analyze(selected, supplied)).signals[0].id != first.signals[0].id
    reader.points += (
        replace(point, analyzed_at=supplied.decision_timestamp + timedelta(seconds=1)),
    )
    assert (await strategy.analyze(selected, supplied)) == first


async def test_revisions_are_selected_as_of_each_candle_without_double_counting() -> None:
    from dataclasses import replace

    supplied = _context(3)
    old = SentimentDataPoint(
        supplied.range_start,
        supplied.range_start,
        Decimal("0.8"),
        news_id="news",
        analysis_id="old",
    )
    new = replace(
        old,
        analyzed_at=supplied.candles[1].open_time,
        signed_score=Decimal("-0.8"),
        analysis_id="new",
    )
    reader = FakeSentimentContextReader((new, old))
    strategy = NewsSentimentStrategy(reader, MODEL)
    selected = _definition(strategy, minEvidenceCount=1)
    result = await strategy.analyze(selected, supplied)
    assert [signal.action for signal in result.signals] == [
        SignalAction.BUY,
        SignalAction.SELL,
        SignalAction.SELL,
    ]
    reader.points = (old, new)
    assert await strategy.analyze(selected, supplied) == result
    selected = _definition(strategy, minEvidenceCount=2)
    assert all(
        signal.phase is SignalPhase.WARMUP
        for signal in (await strategy.analyze(selected, supplied)).signals
    )
