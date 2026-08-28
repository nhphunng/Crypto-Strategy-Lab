from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from tests.fixtures.backtest_evaluation.cross_feature import NOW
from tests.fixtures.backtest_evaluation.scenarios import forced_close, redundant_signals

from crypto_lab.domain.backtest.configuration import published_decimal, quantity_decimal
from crypto_lab.domain.backtest.engine import execute_backtest
from crypto_lab.domain.backtest.errors import NoOpCode
from crypto_lab.domain.backtest.trade import CloseReason, OpenPosition, close_position


def test_redundant_signals_costs_and_equity_reconcile() -> None:
    config, candles, analysis, policy = redundant_signals()
    result = execute_backtest(config, candles, analysis, policy, created_at=NOW)
    assert result.signals[1].no_op_code is NoOpCode.ALREADY_LONG
    assert len(result.trades) == 1
    assert result.final_equity == result.equity_curve.points[-1].total_equity
    assert all(
        point.total_equity == point.cash + point.position_value
        for point in result.equity_curve.points
    )


def test_open_position_is_force_closed() -> None:
    config, candles, analysis, policy = forced_close()
    result = execute_backtest(config, candles, analysis, policy, created_at=NOW)
    assert result.trades[0].close_reason is CloseReason.END_OF_RANGE
    assert result.trades[0].exit_signal_snapshot_id is None
    assert result.equity_curve.points[-1].quantity == 0


def test_trade_reconciliation_uses_the_same_published_notional_rounding() -> None:
    fee_rate = Decimal("0.0004")
    slippage_rate = Decimal("0.0002")
    entry_reference = Decimal("64000.12345678")
    entry_price = published_decimal(entry_reference * (Decimal(1) + slippage_rate))
    quantity = quantity_decimal(
        Decimal("10000") / (entry_price * (Decimal(1) + fee_rate))
    )
    entry_notional = published_decimal(quantity * entry_price)
    entry_fee = published_decimal(entry_notional * fee_rate)
    position = OpenPosition(
        UUID("10000000-0000-4000-8000-000000000001"),
        datetime(2026, 8, 1, tzinfo=UTC),
        entry_reference,
        entry_price,
        quantity,
        entry_fee,
        published_decimal(entry_notional + entry_fee),
    )

    trade, _ = close_position(
        trade_id=UUID("20000000-0000-4000-8000-000000000001"),
        sequence=0,
        position=position,
        exit_signal_snapshot_id=None,
        exit_time=datetime(2026, 8, 2, tzinfo=UTC),
        exit_reference_price=Decimal("65000.87654321"),
        slippage_rate=slippage_rate,
        fee_rate=fee_rate,
        close_reason=CloseReason.END_OF_RANGE,
    )

    assert trade.profit_loss == Decimal("144.187036451812037443")
