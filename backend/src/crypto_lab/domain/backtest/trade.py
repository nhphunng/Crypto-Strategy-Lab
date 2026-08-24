from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from crypto_lab.domain.backtest.configuration import published_decimal
from crypto_lab.domain.market_data.timeframe import require_utc


class TradeSide(StrEnum):
    LONG = "LONG"


class CloseReason(StrEnum):
    SELL_SIGNAL = "SELL_SIGNAL"
    END_OF_RANGE = "END_OF_RANGE"


@dataclass(frozen=True, slots=True)
class OpenPosition:
    entry_signal_snapshot_id: UUID
    entry_time: datetime
    entry_reference_price: Decimal
    entry_price: Decimal
    quantity: Decimal
    entry_fee: Decimal
    entry_cost: Decimal

    def __post_init__(self) -> None:
        require_utc(self.entry_time)
        if min(self.entry_reference_price, self.entry_price, self.quantity) <= 0:
            raise ValueError("position price and quantity must be positive")
        if self.entry_fee < 0 or self.entry_cost <= 0:
            raise ValueError("position costs are invalid")


@dataclass(frozen=True, slots=True)
class Trade:
    id: UUID
    sequence: int
    entry_signal_snapshot_id: UUID
    exit_signal_snapshot_id: UUID | None
    entry_time: datetime
    exit_time: datetime
    entry_reference_price: Decimal
    exit_reference_price: Decimal
    entry_price: Decimal
    exit_price: Decimal
    side: TradeSide
    quantity: Decimal
    entry_fee: Decimal
    exit_fee: Decimal
    profit_loss: Decimal
    return_percent: Decimal
    close_reason: CloseReason

    def __post_init__(self) -> None:
        require_utc(self.entry_time)
        require_utc(self.exit_time)
        if self.sequence < 0 or self.entry_time > self.exit_time:
            raise ValueError("trade order is invalid")
        if (
            min(
                self.entry_reference_price,
                self.exit_reference_price,
                self.entry_price,
                self.exit_price,
                self.quantity,
            )
            <= 0
        ):
            raise ValueError("trade prices and quantity must be positive")
        if self.entry_fee < 0 or self.exit_fee < 0:
            raise ValueError("trade fees must be non-negative")
        expected = published_decimal(
            self.quantity * self.exit_price
            - self.exit_fee
            - (self.quantity * self.entry_price + self.entry_fee)
        )
        if published_decimal(self.profit_loss) != expected:
            raise ValueError("trade profit/loss does not reconcile")


def close_position(
    *,
    trade_id: UUID,
    sequence: int,
    position: OpenPosition,
    exit_signal_snapshot_id: UUID | None,
    exit_time: datetime,
    exit_reference_price: Decimal,
    slippage_rate: Decimal,
    fee_rate: Decimal,
    close_reason: CloseReason,
) -> tuple[Trade, Decimal]:
    exit_price = published_decimal(exit_reference_price * (Decimal(1) - slippage_rate))
    exit_notional = published_decimal(position.quantity * exit_price)
    exit_fee = published_decimal(exit_notional * fee_rate)
    proceeds = published_decimal(exit_notional - exit_fee)
    profit_loss = published_decimal(proceeds - position.entry_cost)
    return_percent = published_decimal(profit_loss / position.entry_cost * Decimal(100))
    return Trade(
        trade_id,
        sequence,
        position.entry_signal_snapshot_id,
        exit_signal_snapshot_id,
        position.entry_time,
        exit_time,
        position.entry_reference_price,
        exit_reference_price,
        position.entry_price,
        exit_price,
        TradeSide.LONG,
        position.quantity,
        position.entry_fee,
        exit_fee,
        profit_loss,
        return_percent,
        close_reason,
    ), proceeds
