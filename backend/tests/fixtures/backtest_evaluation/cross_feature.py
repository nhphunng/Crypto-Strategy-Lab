from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from crypto_lab.domain.backtest.configuration import BacktestConfiguration, ExecutionPolicy
from crypto_lab.domain.market_data.candle import Candle
from crypto_lab.domain.market_data.dataset import calculate_dataset_checksum
from crypto_lab.domain.market_data.timeframe import Timeframe
from crypto_lab.domain.strategy.context import ContextCompleteness, StrategyContext
from crypto_lab.domain.strategy.definition import StrategyDefinition
from crypto_lab.domain.strategy.implementations.moving_average import MovingAverageStrategy
from crypto_lab.domain.strategy.signal import (
    ContextProvenance,
    HistoryState,
    Signal,
    SignalAction,
    SignalPhase,
    StrategyAnalysisResult,
)

DATASET_ID = UUID("10000000-0000-0000-0000-000000000004")
DEFINITION_ID = UUID("20000000-0000-0000-0000-000000000004")
POLICY_ID = UUID("30000000-0000-0000-0000-000000000004")
RUN_ID = UUID("40000000-0000-0000-0000-000000000004")
JOB_ID = UUID("50000000-0000-0000-0000-000000000004")
NOW = datetime(2026, 8, 13, 12, tzinfo=UTC)


def deterministic_inputs(
    actions: tuple[SignalAction, ...],
    prices: tuple[str, ...],
    *,
    fee: str = "0",
    slippage: str = "0",
) -> tuple[BacktestConfiguration, tuple[Candle, ...], StrategyAnalysisResult, ExecutionPolicy]:
    if len(actions) != len(prices):
        raise ValueError("actions and prices must align")
    start = datetime(2026, 1, 1, tzinfo=UTC)
    candles = tuple(
        _candle(start + timedelta(hours=index), price) for index, price in enumerate(prices)
    )
    checksum = calculate_dataset_checksum(candles)
    end = start + timedelta(hours=len(candles))
    context = StrategyContext(
        str(DATASET_ID),
        checksum,
        "BINANCE",
        "BTCUSDT",
        Timeframe.ONE_HOUR,
        start,
        end,
        end,
        ContextCompleteness.COMPLETE,
        candles,
    )
    strategy = MovingAverageStrategy()
    parameters = strategy.validate_parameters({"period": 2})
    definition = StrategyDefinition(
        DEFINITION_ID,
        "ma",
        "MA",
        strategy.metadata.strategy_version,
        strategy.metadata.contract_version,
        parameters,
        NOW,
    )
    signals = tuple(
        Signal.create(
            strategy_definition_id=definition.id,
            strategy_id=definition.strategy_id,
            strategy_type=definition.strategy_type,
            strategy_version=definition.strategy_version,
            contract_version=definition.contract_version,
            dataset_id=str(DATASET_ID),
            dataset_version=checksum,
            context_fingerprint=context.context_fingerprint,
            timestamp=candle.open_time,
            sequence=index,
            action=action,
            phase=SignalPhase.EVALUATED,
            reason="fixture",
        )
        for index, (action, candle) in enumerate(zip(actions, candles, strict=True))
    )
    provenance = ContextProvenance(
        str(DATASET_ID),
        checksum,
        context.context_fingerprint,
        "BINANCE",
        "BTCUSDT",
        Timeframe.ONE_HOUR,
        start,
        end,
        end,
    )
    analysis = StrategyAnalysisResult(
        definition,
        parameters,
        provenance,
        definition.contract_version,
        HistoryState.EVALUABLE,
        signals,
    )
    policy = ExecutionPolicy(POLICY_ID, "next-open-long-only", "1.0.0")
    config = BacktestConfiguration(
        RUN_ID,
        JOB_ID,
        DATASET_ID,
        "1",
        checksum,
        "BINANCE",
        "BTCUSDT",
        Timeframe.ONE_HOUR,
        start,
        end,
        DEFINITION_ID,
        "ma",
        "1.0.0",
        "1.0.0",
        parameters.canonical_fingerprint,
        context.context_fingerprint,
        POLICY_ID,
        "1.0.0",
        Decimal("1000"),
        Decimal(fee),
        Decimal(slippage),
        42,
    )
    return config, candles, analysis, policy


def _candle(open_time: datetime, price: str) -> Candle:
    value = Decimal(price)
    return Candle(
        "BINANCE",
        "BTCUSDT",
        Timeframe.ONE_HOUR,
        open_time,
        Timeframe.ONE_HOUR.close_time(open_time),
        value,
        value,
        value,
        value,
        Decimal("1"),
        True,
        open_time + timedelta(hours=1),
    )
