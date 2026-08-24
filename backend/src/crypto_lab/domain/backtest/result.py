from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid5

from crypto_lab.domain.backtest.configuration import BacktestConfiguration, canonical_hash
from crypto_lab.domain.backtest.equity import EquityCurve
from crypto_lab.domain.backtest.errors import NoOpCode
from crypto_lab.domain.backtest.trade import Trade
from crypto_lab.domain.market_data.candle import canonical_decimal, format_utc_millis
from crypto_lab.domain.strategy.signal import Signal


class BacktestHistoryState(StrEnum):
    INSUFFICIENT = "INSUFFICIENT"
    EVALUABLE = "EVALUABLE"


class TradeState(StrEnum):
    NO_TRADES = "NO_TRADES"
    HAS_TRADES = "HAS_TRADES"


@dataclass(frozen=True, slots=True)
class SignalSnapshot:
    id: UUID
    source_signal_id: str
    sequence: int
    timestamp: datetime
    action: str
    phase: str
    strength: Decimal | None
    reason: str | None
    no_op_code: NoOpCode | None

    @classmethod
    def from_signal(cls, result_id: UUID, signal: Signal) -> SignalSnapshot:
        return cls(
            uuid5(result_id, signal.id),
            signal.id,
            signal.sequence,
            signal.timestamp,
            signal.action.value,
            signal.phase.value,
            signal.strength,
            signal.reason,
            None,
        )

    def with_no_op(self, code: NoOpCode) -> SignalSnapshot:
        return SignalSnapshot(
            self.id,
            self.source_signal_id,
            self.sequence,
            self.timestamp,
            self.action,
            self.phase,
            self.strength,
            self.reason,
            code,
        )


@dataclass(frozen=True, slots=True)
class BacktestResult:
    id: UUID
    configuration: BacktestConfiguration
    result_checksum: str
    history_state: BacktestHistoryState
    trade_state: TradeState
    signals: tuple[SignalSnapshot, ...]
    trades: tuple[Trade, ...]
    equity_curve: EquityCurve
    execution_duration_ms: int
    created_at: datetime

    def __post_init__(self) -> None:
        if len(self.result_checksum) != 64:
            raise ValueError("result checksum must be SHA-256")
        if self.execution_duration_ms < 0:
            raise ValueError("execution duration must be non-negative")
        if self.trade_state is TradeState.NO_TRADES and self.trades:
            raise ValueError("NO_TRADES result cannot contain trades")
        if self.trade_state is TradeState.HAS_TRADES and not self.trades:
            raise ValueError("HAS_TRADES result requires trades")

    @property
    def final_equity(self) -> Decimal:
        return self.equity_curve.final_equity

    @property
    def input_fingerprint(self) -> str:
        return self.configuration.input_fingerprint


def result_checksum(
    configuration: BacktestConfiguration,
    history_state: BacktestHistoryState,
    signals: tuple[SignalSnapshot, ...],
    trades: tuple[Trade, ...],
    curve: EquityCurve,
) -> str:
    return canonical_hash(
        {
            "equity": [
                {
                    "cash": canonical_decimal(p.cash),
                    "closePrice": canonical_decimal(p.close_price),
                    "position": p.position,
                    "quantity": canonical_decimal(p.quantity),
                    "time": format_utc_millis(p.candle_open_time),
                    "totalEquity": canonical_decimal(p.total_equity),
                }
                for p in curve.points
            ],
            "historyState": history_state.value,
            "inputFingerprint": configuration.input_fingerprint,
            "signals": [
                {
                    "action": s.action,
                    "id": s.source_signal_id,
                    "noOp": None if s.no_op_code is None else s.no_op_code.value,
                    "phase": s.phase,
                    "sequence": s.sequence,
                    "timestamp": format_utc_millis(s.timestamp),
                }
                for s in signals
            ],
            "trades": [
                {
                    "closeReason": t.close_reason.value,
                    "entryFee": canonical_decimal(t.entry_fee),
                    "entryPrice": canonical_decimal(t.entry_price),
                    "entrySignalId": str(t.entry_signal_snapshot_id),
                    "exitFee": canonical_decimal(t.exit_fee),
                    "exitPrice": canonical_decimal(t.exit_price),
                    "exitSignalId": None
                    if t.exit_signal_snapshot_id is None
                    else str(t.exit_signal_snapshot_id),
                    "profitLoss": canonical_decimal(t.profit_loss),
                    "quantity": canonical_decimal(t.quantity),
                    "sequence": t.sequence,
                }
                for t in trades
            ],
        }
    )
