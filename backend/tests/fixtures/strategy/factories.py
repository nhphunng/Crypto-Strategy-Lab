from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from crypto_lab.domain.market_data.candle import Candle
from crypto_lab.domain.market_data.timeframe import Timeframe
from crypto_lab.domain.strategy.context import ContextCompleteness, StrategyContext
from crypto_lab.domain.strategy.definition import StrategyDefinition
from crypto_lab.domain.strategy.implementations.moving_average import MovingAverageStrategy
from crypto_lab.domain.strategy.implementations.rsi import RsiStrategy


def candles(closes: list[str], *, start: datetime | None = None) -> tuple[Candle, ...]:
    start = start or datetime(2026, 1, 1, tzinfo=UTC)
    result = []
    for index, close_text in enumerate(closes):
        opened = start + timedelta(hours=index)
        close = Decimal(close_text)
        result.append(
            Candle(
                provider="BINANCE",
                pair="BTCUSDT",
                timeframe=Timeframe.ONE_HOUR,
                open_time=opened,
                close_time=Timeframe.ONE_HOUR.close_time(opened),
                open=close,
                high=close,
                low=close,
                close=close,
                volume=Decimal("1"),
                closed=True,
                received_at=opened + timedelta(hours=1),
            )
        )
    return tuple(result)


def context(closes: list[str]) -> StrategyContext:
    values = candles(closes)
    start = values[0].open_time if values else datetime(2026, 1, 1, tzinfo=UTC)
    end = values[-1].close_time if values else start
    return StrategyContext(
        dataset_id="fixture-dataset",
        dataset_version="fixture-v1",
        provider="BINANCE",
        pair="BTCUSDT",
        timeframe=Timeframe.ONE_HOUR,
        range_start=start,
        range_end=end,
        decision_timestamp=end,
        completeness=ContextCompleteness.COMPLETE,
        candles=values,
    )


def definition(
    strategy: MovingAverageStrategy | RsiStrategy, raw: dict[str, object]
) -> StrategyDefinition:
    return StrategyDefinition(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        strategy_id=strategy.metadata.strategy_id,
        strategy_type=strategy.metadata.strategy_type,
        strategy_version=strategy.metadata.strategy_version,
        contract_version=strategy.metadata.contract_version,
        parameters=strategy.validate_parameters(raw),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
