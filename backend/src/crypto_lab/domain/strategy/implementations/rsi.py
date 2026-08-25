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


class RsiStrategy:
    metadata = StrategyMetadata(
        strategy_id="rsi",
        strategy_type="RSI",
        display_name="Relative Strength Index Threshold Exit",
        strategy_version=SemanticVersion.parse("1.0.0"),
        contract_version=SemanticVersion.parse("1.0.0"),
        parameter_schema=ParameterSchema(
            (
                ParameterDefinition(
                    "period", "Wilder smoothing period", ParameterValueType.INTEGER, 14, 2, 200
                ),
                ParameterDefinition(
                    "lowerThreshold",
                    "Oversold exit threshold",
                    ParameterValueType.DECIMAL,
                    Decimal("30"),
                    Decimal("0"),
                    Decimal("100"),
                ),
                ParameterDefinition(
                    "upperThreshold",
                    "Overbought exit threshold",
                    ParameterValueType.DECIMAL,
                    Decimal("70"),
                    Decimal("0"),
                    Decimal("100"),
                ),
            ),
            (RelationshipRule("lowerThreshold", "lt", "upperThreshold"),),
        ),
        capabilities=frozenset({StrategyCapability.REASON}),
    )

    def validate_parameters(self, raw: Mapping[str, object]) -> ValidatedParameterSet:
        return self.metadata.parameter_schema.validate(raw)

    def analyze(
        self, definition: StrategyDefinition, context: StrategyContext
    ) -> StrategyAnalysisResult:
        period = definition.parameters.values["period"]
        lower = definition.parameters.values["lowerThreshold"]
        upper = definition.parameters.values["upperThreshold"]
        assert isinstance(period, int) and isinstance(lower, Decimal) and isinstance(upper, Decimal)
        values: list[Decimal | None] = [None] * len(context.candles)
        if len(context.candles) > period:
            changes = [
                context.candles[i].close - context.candles[i - 1].close
                for i in range(1, len(context.candles))
            ]
            gain = (
                sum((max(change, Decimal(0)) for change in changes[:period]), Decimal(0)) / period
            )
            loss = (
                sum((max(-change, Decimal(0)) for change in changes[:period]), Decimal(0)) / period
            )
            values[period] = _rsi(gain, loss)
            for candle_index in range(period + 1, len(context.candles)):
                change = changes[candle_index - 1]
                gain = (gain * (period - 1) + max(change, Decimal(0))) / period
                loss = (loss * (period - 1) + max(-change, Decimal(0))) / period
                values[candle_index] = _rsi(gain, loss)
        signals = []
        for index in range(len(context.candles)):
            current, previous = values[index], values[index - 1] if index else None
            phase = (
                SignalPhase.WARMUP if current is None or previous is None else SignalPhase.EVALUATED
            )
            action, reason = (
                SignalAction.HOLD,
                "insufficient_history" if phase is SignalPhase.WARMUP else "no_strict_crossing",
            )
            if current is not None and previous is not None:
                if previous <= lower and current > lower:
                    action, reason = SignalAction.BUY, "rsi_crossed_above_lower"
                elif previous >= upper and current < upper:
                    action, reason = SignalAction.SELL, "rsi_crossed_below_upper"
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


def _rsi(gain: Decimal, loss: Decimal) -> Decimal:
    if gain == 0 and loss == 0:
        return Decimal(50)
    if loss == 0:
        return Decimal(100)
    if gain == 0:
        return Decimal(0)
    return Decimal(100) - Decimal(100) / (Decimal(1) + gain / loss)
