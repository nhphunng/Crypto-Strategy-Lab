from __future__ import annotations

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


class BollingerBandsStrategy:
    metadata = StrategyMetadata(
        strategy_id="bollinger",
        strategy_type="BOLLINGER_BANDS",
        display_name="Bollinger Bands Mean Reversion",
        strategy_version=SemanticVersion.parse("1.0.0"),
        contract_version=SemanticVersion.parse("1.0.0"),
        parameter_schema=ParameterSchema(
            (
                ParameterDefinition(
                    "period", "Close-price window", ParameterValueType.INTEGER, 20, 2, 500
                ),
                ParameterDefinition(
                    "standardDeviations",
                    "Band width in population standard deviations",
                    ParameterValueType.DECIMAL,
                    Decimal("2"),
                    Decimal("0"),
                    Decimal("10"),
                    minimum_inclusive=False,
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
        period = definition.parameters.values["period"]
        deviations = definition.parameters.values["standardDeviations"]
        assert isinstance(period, int) and isinstance(deviations, Decimal)

        total = Decimal(0)
        total_squares = Decimal(0)
        signals = []
        for index, candle in enumerate(context.candles):
            total += candle.close
            total_squares += candle.close * candle.close
            if index >= period:
                expired = context.candles[index - period].close
                total -= expired
                total_squares -= expired * expired

            if index < period - 1:
                action = SignalAction.HOLD
                phase = SignalPhase.WARMUP
                reason = "insufficient_history"
            else:
                mean = total / period
                variance = total_squares / period - mean * mean
                standard_deviation = max(variance, Decimal(0)).sqrt()
                lower_band = mean - deviations * standard_deviation
                upper_band = mean + deviations * standard_deviation
                action = SignalAction.HOLD
                phase = SignalPhase.EVALUATED
                reason = "close_within_bands"
                if candle.close < lower_band:
                    action, reason = SignalAction.BUY, "close_below_lower_band"
                elif candle.close > upper_band:
                    action, reason = SignalAction.SELL, "close_above_upper_band"
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
