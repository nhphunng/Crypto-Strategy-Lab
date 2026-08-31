from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from crypto_lab.domain.backtest.configuration import published_decimal
from crypto_lab.domain.market_data.timeframe import require_utc


@dataclass(frozen=True, slots=True)
class EquityPoint:
    id: UUID
    position: int
    candle_open_time: datetime
    valued_at: datetime
    cash: Decimal
    quantity: Decimal
    close_price: Decimal
    position_value: Decimal
    total_equity: Decimal
    event_signal_snapshot_id: UUID | None = None

    def __post_init__(self) -> None:
        require_utc(self.candle_open_time)
        require_utc(self.valued_at)
        if (
            self.position < 0
            or min(self.cash, self.quantity, self.position_value, self.total_equity) < 0
        ):
            raise ValueError("equity values must be non-negative")
        if self.close_price <= 0:
            raise ValueError("close price must be positive")
        expected_value = published_decimal(self.quantity * self.close_price)
        expected_total = published_decimal(self.cash + expected_value)
        if self.position_value != expected_value or self.total_equity != expected_total:
            raise ValueError("equity point does not reconcile")


@dataclass(frozen=True, slots=True)
class EquityCurve:
    points: tuple[EquityPoint, ...]

    def __post_init__(self) -> None:
        if any(point.position != index for index, point in enumerate(self.points)):
            raise ValueError("equity positions must be contiguous")
        if any(
            current.candle_open_time <= previous.candle_open_time
            for previous, current in zip(self.points, self.points[1:], strict=False)
        ):
            raise ValueError("equity points must be chronologically ordered")

    @property
    def final_equity(self) -> Decimal:
        if not self.points:
            raise ValueError("equity curve cannot be empty")
        return self.points[-1].total_equity
