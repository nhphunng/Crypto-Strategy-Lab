from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from decimal import Decimal

from crypto_lab.application.sentiment.context_reader import (
    SentimentContextReader,
    SentimentDataPoint,
)
from crypto_lab.domain.sentiment.model import ModelRef
from crypto_lab.domain.strategy.context import StrategyContext
from crypto_lab.domain.strategy.definition import StrategyDefinition
from crypto_lab.domain.strategy.implementations.moving_average import _result, _signal
from crypto_lab.domain.strategy.parameters import (
    ParameterDefinition,
    ParameterSchema,
    ParameterValueType,
    RelationshipRule,
    ValidatedParameterSet,
)
from crypto_lab.domain.strategy.protocol import StrategyCapability, StrategyMetadata
from crypto_lab.domain.strategy.signal import (
    HistoryState,
    SignalAction,
    SignalPhase,
    StrategyAnalysisResult,
)
from crypto_lab.domain.strategy.version import SemanticVersion


class NewsSentimentStrategy:
    """Rolling-average News sentiment threshold strategy.

    No-look-ahead is not structurally enforced for sentiment the way it is
    for Candles in ``StrategyContext.__post_init__`` -- there is no
    first-class mechanism for that today outside of candle data. Instead this
    strategy self-enforces it: for a given candle's decision, a sentiment
    data point counts as evidence only if BOTH its ``published_at`` and its
    ``analyzed_at`` are no later than that candle's own ``close_time``. Filtering
    on ``analyzed_at`` too (even though it is a pipeline artifact, not
    trading-relevant world state) prevents an unrealistic backtest where the
    model analyzed an article faster than it could have in a live system.
    """

    metadata = StrategyMetadata(
        strategy_id="news_sentiment",
        strategy_type="SENTIMENT",
        display_name="News Sentiment Threshold",
        strategy_version=SemanticVersion.parse("1.0.0"),
        contract_version=SemanticVersion.parse("1.0.0"),
        parameter_schema=ParameterSchema(
            (
                ParameterDefinition(
                    "lookbackHours",
                    "Rolling sentiment window in hours",
                    ParameterValueType.INTEGER,
                    24,
                    1,
                    168,
                ),
                ParameterDefinition(
                    "buyThreshold",
                    "Rolling sentiment score to trigger BUY",
                    ParameterValueType.DECIMAL,
                    Decimal("0.2"),
                    Decimal("-1"),
                    Decimal("1"),
                ),
                ParameterDefinition(
                    "sellThreshold",
                    "Rolling sentiment score to trigger SELL",
                    ParameterValueType.DECIMAL,
                    Decimal("-0.2"),
                    Decimal("-1"),
                    Decimal("1"),
                ),
                ParameterDefinition(
                    "minEvidenceCount",
                    "Minimum analyzed articles required to decide",
                    ParameterValueType.INTEGER,
                    3,
                    1,
                    500,
                ),
            ),
            (RelationshipRule("sellThreshold", "lt", "buyThreshold"),),
        ),
        capabilities=frozenset({StrategyCapability.REASON}),
    )

    def __init__(self, reader: SentimentContextReader, model: ModelRef) -> None:
        self._reader = reader
        self._model = model

    def validate_parameters(self, raw: Mapping[str, object]) -> ValidatedParameterSet:
        return self.metadata.parameter_schema.validate(raw)

    async def analyze(
        self, definition: StrategyDefinition, context: StrategyContext
    ) -> StrategyAnalysisResult:
        lookback_hours = definition.parameters.values["lookbackHours"]
        buy_threshold = definition.parameters.values["buyThreshold"]
        sell_threshold = definition.parameters.values["sellThreshold"]
        min_evidence = definition.parameters.values["minEvidenceCount"]
        assert isinstance(lookback_hours, int)
        assert isinstance(buy_threshold, Decimal)
        assert isinstance(sell_threshold, Decimal)
        assert isinstance(min_evidence, int)

        lookback = timedelta(hours=lookback_hours)
        points = await self._reader.series(
            context.pair,
            context.range_start - lookback,
            context.decision_timestamp,
            self._model,
        )

        signals = []
        for index, candle in enumerate(context.candles):
            window_end = candle.close_time
            window_start = window_end - lookback
            evidence = _evidence_within(points, window_start, window_end)
            if len(evidence) < min_evidence:
                action = SignalAction.HOLD
                phase = SignalPhase.WARMUP
                reason = "insufficient_evidence"
            else:
                total = sum((point.signed_score for point in evidence), Decimal(0))
                average = total / len(evidence)
                phase = SignalPhase.EVALUATED
                if average >= buy_threshold:
                    action, reason = SignalAction.BUY, "sentiment_above_buy_threshold"
                elif average <= sell_threshold:
                    action, reason = SignalAction.SELL, "sentiment_below_sell_threshold"
                else:
                    action, reason = SignalAction.HOLD, "sentiment_within_neutral_band"
            signals.append(_signal(definition, context, index, action, phase, reason))

        state = (
            HistoryState.EMPTY
            if not signals
            else (
                HistoryState.INSUFFICIENT
                if signals[-1].phase is SignalPhase.WARMUP
                else HistoryState.EVALUABLE
            )
        )
        return _result(definition, context, tuple(signals), state)


def _evidence_within(
    points: tuple[SentimentDataPoint, ...],
    window_start: datetime,
    window_end: datetime,
) -> tuple[SentimentDataPoint, ...]:
    return tuple(
        point
        for point in points
        # Self-enforced no-look-ahead: both dimensions must be no later than
        # this candle's own close (see class docstring).
        if window_start <= point.published_at <= window_end and point.analyzed_at <= window_end
    )
