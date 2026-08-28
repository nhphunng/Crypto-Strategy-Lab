from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from decimal import Decimal

from crypto_lab.domain.strategy.context import StrategyContext
from crypto_lab.domain.strategy.definition import StrategyDefinition
from crypto_lab.domain.strategy.implementations.moving_average import _result, _signal
from crypto_lab.domain.strategy.parameters import (
    ParameterDefinition,
    ParameterSchema,
    ParameterValueType,
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


class SupportResistanceStrategy:
    metadata = StrategyMetadata(
        strategy_id="support_resistance",
        strategy_type="SUPPORT_RESISTANCE",
        display_name="Support and Resistance Proximity",
        strategy_version=SemanticVersion.parse("1.0.0"),
        contract_version=SemanticVersion.parse("1.0.0"),
        parameter_schema=ParameterSchema(
            (
                ParameterDefinition(
                    "lookback", "Prior-candle level window", ParameterValueType.INTEGER, 120, 2, 500
                ),
                ParameterDefinition(
                    "tolerancePercent",
                    "Maximum distance from a level as a price percentage",
                    ParameterValueType.DECIMAL,
                    Decimal("0.7"),
                    Decimal("0"),
                    Decimal("10"),
                ),
            )
        ),
        capabilities=frozenset({StrategyCapability.REASON}),
    )

    def validate_parameters(self, raw: Mapping[str, object]) -> ValidatedParameterSet:
        return self.metadata.parameter_schema.validate(raw)

    def analyze(
        self, definition: StrategyDefinition, context: StrategyContext
    ) -> StrategyAnalysisResult:
        lookback = definition.parameters.values["lookback"]
        tolerance_percent = definition.parameters.values["tolerancePercent"]
        assert isinstance(lookback, int) and isinstance(tolerance_percent, Decimal)
        tolerance = tolerance_percent / Decimal(100)

        support_candidates: deque[int] = deque()
        resistance_candidates: deque[int] = deque()
        signals = []
        for index, candle in enumerate(context.candles):
            oldest = index - lookback
            while support_candidates and support_candidates[0] < oldest:
                support_candidates.popleft()
            while resistance_candidates and resistance_candidates[0] < oldest:
                resistance_candidates.popleft()

            if index < lookback:
                action = SignalAction.HOLD
                phase = SignalPhase.WARMUP
                reason = "insufficient_history"
            else:
                support = context.candles[support_candidates[0]].low
                resistance = context.candles[resistance_candidates[0]].high
                near_support = abs(candle.close - support) <= support * tolerance
                near_resistance = abs(candle.close - resistance) <= resistance * tolerance
                action = SignalAction.HOLD
                phase = SignalPhase.EVALUATED
                reason = "close_between_levels"
                if near_support and near_resistance:
                    reason = "overlapping_level_zones"
                elif near_support:
                    action, reason = SignalAction.BUY, "close_near_support"
                elif near_resistance:
                    action, reason = SignalAction.SELL, "close_near_resistance"
            signals.append(_signal(definition, context, index, action, phase, reason))

            while support_candidates and (
                context.candles[support_candidates[-1]].low >= candle.low
            ):
                support_candidates.pop()
            support_candidates.append(index)
            while resistance_candidates and (
                context.candles[resistance_candidates[-1]].high <= candle.high
            ):
                resistance_candidates.pop()
            resistance_candidates.append(index)

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
