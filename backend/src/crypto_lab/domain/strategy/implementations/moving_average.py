from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from crypto_lab.domain.strategy.context import StrategyContext
from crypto_lab.domain.strategy.definition import StrategyDefinition
from crypto_lab.domain.strategy.parameters import (
    ParameterDefinition,
    ParameterSchema,
    ParameterValueType,
    ValidatedParameterSet,
)
from crypto_lab.domain.strategy.protocol import StrategyCapability, StrategyMetadata
from crypto_lab.domain.strategy.signal import (
    ContextProvenance,
    HistoryState,
    Signal,
    SignalAction,
    SignalPhase,
    StrategyAnalysisResult,
)
from crypto_lab.domain.strategy.version import SemanticVersion


class MovingAverageStrategy:
    metadata = StrategyMetadata(
        strategy_id="ma",
        strategy_type="MA",
        display_name="Simple Moving Average Crossover",
        strategy_version=SemanticVersion.parse("1.0.0"),
        contract_version=SemanticVersion.parse("1.0.0"),
        parameter_schema=ParameterSchema(
            (
                ParameterDefinition(
                    "period", "Close-price window", ParameterValueType.INTEGER, 20, 2, 500
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
        assert isinstance(period, int)
        moving: list[Decimal | None] = []
        total = Decimal(0)
        for index, candle in enumerate(context.candles):
            total += candle.close
            if index >= period:
                total -= context.candles[index - period].close
            moving.append(total / period if index >= period - 1 else None)
        signals = []
        for index, candle in enumerate(context.candles):
            current, previous = moving[index], moving[index - 1] if index else None
            action = SignalAction.HOLD
            phase = (
                SignalPhase.WARMUP if current is None or previous is None else SignalPhase.EVALUATED
            )
            reason = "insufficient_history" if phase is SignalPhase.WARMUP else "no_strict_crossing"
            if current is not None and previous is not None:
                prior_close = context.candles[index - 1].close
                if prior_close <= previous and candle.close > current:
                    action, reason = SignalAction.BUY, "close_crossed_above_ma"
                elif prior_close >= previous and candle.close < current:
                    action, reason = SignalAction.SELL, "close_crossed_below_ma"
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


def _signal(
    definition: StrategyDefinition,
    context: StrategyContext,
    index: int,
    action: SignalAction,
    phase: SignalPhase,
    reason: str,
) -> Signal:
    candle = context.candles[index]
    return Signal.create(
        strategy_definition_id=definition.id,
        strategy_id=definition.strategy_id,
        strategy_type=definition.strategy_type,
        strategy_version=definition.strategy_version,
        contract_version=definition.contract_version,
        dataset_id=context.dataset_id,
        dataset_version=context.dataset_version,
        context_fingerprint=context.context_fingerprint,
        timestamp=candle.open_time,
        sequence=index,
        action=action,
        phase=phase,
        reason=reason,
    )


def _result(
    definition: StrategyDefinition,
    context: StrategyContext,
    signals: tuple[Signal, ...],
    state: HistoryState,
) -> StrategyAnalysisResult:
    provenance = ContextProvenance(
        context.dataset_id,
        context.dataset_version,
        context.context_fingerprint,
        context.provider,
        context.pair,
        context.timeframe,
        context.range_start,
        context.range_end,
        context.decision_timestamp,
    )
    return StrategyAnalysisResult(
        definition, definition.parameters, provenance, definition.contract_version, state, signals
    )
