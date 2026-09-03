from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid5

from crypto_lab.domain.backtest.configuration import (
    BacktestConfiguration,
    ExecutionPolicy,
    published_decimal,
    quantity_decimal,
)
from crypto_lab.domain.backtest.equity import EquityCurve, EquityPoint
from crypto_lab.domain.backtest.errors import BacktestError, BacktestErrorCode, NoOpCode
from crypto_lab.domain.backtest.result import (
    BacktestHistoryState,
    BacktestResult,
    SignalSnapshot,
    TradeState,
    result_checksum,
)
from crypto_lab.domain.backtest.trade import CloseReason, OpenPosition, Trade, close_position
from crypto_lab.domain.market_data.candle import Candle
from crypto_lab.domain.market_data.dataset import calculate_dataset_checksum
from crypto_lab.domain.strategy.signal import (
    HistoryState,
    SignalAction,
    SignalPhase,
    StrategyAnalysisResult,
)


def execute_backtest(
    configuration: BacktestConfiguration,
    candles: tuple[Candle, ...],
    analysis: StrategyAnalysisResult,
    policy: ExecutionPolicy,
    *,
    created_at: datetime,
    execution_duration_ms: int = 0,
) -> BacktestResult:
    _validate_inputs(configuration, candles, analysis, policy)
    result_id = uuid5(configuration.job_id, configuration.input_fingerprint)
    snapshots = [SignalSnapshot.from_signal(result_id, signal) for signal in analysis.signals]
    cash = configuration.initial_capital
    position: OpenPosition | None = None
    trades: list[Trade] = []
    points: list[EquityPoint] = []

    for index, candle in enumerate(candles):
        event_id: UUID | None = None
        if index > 0:
            signal_index = index - 1
            snapshot = snapshots[signal_index]
            signal = analysis.signals[signal_index]
            event_id = snapshot.id
            if signal.phase is SignalPhase.WARMUP:
                snapshots[signal_index] = snapshot.with_no_op(NoOpCode.WARMUP)
            elif signal.action is SignalAction.HOLD:
                snapshots[signal_index] = snapshot.with_no_op(NoOpCode.HOLD)
            elif signal.action is SignalAction.BUY:
                if position is not None:
                    snapshots[signal_index] = snapshot.with_no_op(NoOpCode.ALREADY_LONG)
                else:
                    fill = published_decimal(
                        candle.open * (Decimal(1) + configuration.slippage_rate)
                    )
                    quantity = quantity_decimal(
                        cash / (fill * (Decimal(1) + configuration.fee_rate))
                    )
                    if quantity <= 0:
                        snapshots[signal_index] = snapshot.with_no_op(NoOpCode.INSUFFICIENT_CAPITAL)
                    else:
                        notional = published_decimal(quantity * fill)
                        fee = published_decimal(notional * configuration.fee_rate)
                        cost = published_decimal(notional + fee)
                        if cost > cash:
                            raise BacktestError(
                                BacktestErrorCode.INSUFFICIENT_CAPITAL,
                                "entry cost exceeds available cash",
                            )
                        cash = published_decimal(cash - cost)
                        position = OpenPosition(
                            snapshot.id, candle.open_time, candle.open, fill, quantity, fee, cost
                        )
            elif position is None:
                snapshots[signal_index] = snapshot.with_no_op(NoOpCode.ALREADY_FLAT)
            else:
                trade, proceeds = close_position(
                    trade_id=uuid5(result_id, f"trade:{len(trades)}"),
                    sequence=len(trades),
                    position=position,
                    exit_signal_snapshot_id=snapshot.id,
                    exit_time=candle.open_time,
                    exit_reference_price=candle.open,
                    slippage_rate=configuration.slippage_rate,
                    fee_rate=configuration.fee_rate,
                    close_reason=CloseReason.SELL_SIGNAL,
                )
                trades.append(trade)
                cash = published_decimal(cash + proceeds)
                position = None

        if index == len(candles) - 1:
            final_signal = analysis.signals[index]
            final_snapshot = snapshots[index]
            if final_signal.phase is SignalPhase.WARMUP:
                snapshots[index] = final_snapshot.with_no_op(NoOpCode.WARMUP)
            elif final_signal.action is SignalAction.HOLD:
                snapshots[index] = final_snapshot.with_no_op(NoOpCode.HOLD)
            else:
                snapshots[index] = final_snapshot.with_no_op(NoOpCode.FINAL_CANDLE_SIGNAL)
            if position is not None:
                trade, proceeds = close_position(
                    trade_id=uuid5(result_id, f"trade:{len(trades)}"),
                    sequence=len(trades),
                    position=position,
                    exit_signal_snapshot_id=None,
                    exit_time=candle.close_time,
                    exit_reference_price=candle.close,
                    slippage_rate=configuration.slippage_rate,
                    fee_rate=configuration.fee_rate,
                    close_reason=CloseReason.END_OF_RANGE,
                )
                trades.append(trade)
                cash = published_decimal(cash + proceeds)
                position = None

        quantity = Decimal(0) if position is None else position.quantity
        position_value = published_decimal(quantity * candle.close)
        points.append(
            EquityPoint(
                uuid5(result_id, f"equity:{index}"),
                index,
                candle.open_time,
                candle.close_time,
                cash,
                quantity,
                candle.close,
                position_value,
                published_decimal(cash + position_value),
                event_id,
            )
        )

    history_state = (
        BacktestHistoryState.INSUFFICIENT
        if analysis.history_state is HistoryState.INSUFFICIENT
        else BacktestHistoryState.EVALUABLE
    )
    curve = EquityCurve(tuple(points))
    frozen_snapshots, frozen_trades = tuple(snapshots), tuple(trades)
    checksum = result_checksum(configuration, history_state, frozen_snapshots, frozen_trades, curve)
    return BacktestResult(
        result_id,
        configuration,
        checksum,
        history_state,
        TradeState.HAS_TRADES if trades else TradeState.NO_TRADES,
        frozen_snapshots,
        frozen_trades,
        curve,
        execution_duration_ms,
        created_at,
    )


def _validate_inputs(
    configuration: BacktestConfiguration,
    candles: tuple[Candle, ...],
    analysis: StrategyAnalysisResult,
    policy: ExecutionPolicy,
) -> None:
    if not candles:
        raise BacktestError(
            BacktestErrorCode.DATASET_INELIGIBLE, "complete dataset must contain candles"
        )
    if (
        policy.id != configuration.execution_policy_id
        or policy.version != configuration.execution_policy_version
    ):
        raise BacktestError(
            BacktestErrorCode.CONFIGURATION_INVALID, "execution policy identity differs"
        )
    if calculate_dataset_checksum(candles) != configuration.dataset_checksum:
        raise BacktestError(BacktestErrorCode.DATASET_INTEGRITY_FAILED, "dataset checksum differs")
    definition, provenance = analysis.strategy_definition, analysis.context_provenance
    if (
        definition.id != configuration.strategy_definition_id
        or definition.strategy_id != configuration.strategy_id
        or str(definition.strategy_version) != configuration.strategy_version
        or str(analysis.contract_version) != configuration.contract_version
        or definition.parameters.canonical_fingerprint != configuration.parameter_fingerprint
        or provenance.sentiment != configuration.sentiment_provenance
        or provenance.context_fingerprint != configuration.context_fingerprint
        or provenance.dataset_id != str(configuration.dataset_id)
        or provenance.dataset_version != configuration.dataset_checksum
    ):
        raise BacktestError(
            BacktestErrorCode.STRATEGY_INCOMPATIBLE, "strategy analysis provenance differs"
        )
    if analysis.history_state is HistoryState.EMPTY or len(analysis.signals) != len(candles):
        raise BacktestError(
            BacktestErrorCode.SIGNAL_MISALIGNED, "signals must align one-to-one with candles"
        )
    for index, (signal, candle) in enumerate(zip(analysis.signals, candles, strict=True)):
        if (
            signal.sequence != index
            or signal.timestamp != candle.open_time
            or signal.dataset_id != str(configuration.dataset_id)
        ):
            raise BacktestError(
                BacktestErrorCode.SIGNAL_MISALIGNED, f"signal {index} is misaligned"
            )
