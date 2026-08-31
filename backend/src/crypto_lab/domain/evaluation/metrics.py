from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from itertools import pairwise

from crypto_lab.domain.backtest.configuration import published_decimal
from crypto_lab.domain.backtest.result import BacktestResult


@dataclass(frozen=True, slots=True)
class EvaluationMetrics:
    total_return: Decimal
    win_rate: Decimal
    max_drawdown: Decimal
    number_of_trades: int
    profit_factor: Decimal | None
    sharpe_ratio: Decimal | None

    def values(self) -> dict[str, Decimal | int | None]:
        return {
            "maxDrawdown": self.max_drawdown,
            "numberOfTrades": self.number_of_trades,
            "profitFactor": self.profit_factor,
            "sharpeRatio": self.sharpe_ratio,
            "totalReturn": self.total_return,
            "winRate": self.win_rate,
        }


def calculate_metrics(result: BacktestResult) -> EvaluationMetrics:
    initial = result.configuration.initial_capital
    total_return = published_decimal((result.final_equity - initial) / initial * Decimal(100))
    count = len(result.trades)
    wins = sum(trade.profit_loss > 0 for trade in result.trades)
    win_rate = Decimal(0) if count == 0 else published_decimal(Decimal(wins) / count * Decimal(100))
    peak: Decimal | None = None
    maximum = Decimal(0)
    for point in result.equity_curve.points:
        peak = point.total_equity if peak is None else max(peak, point.total_equity)
        if peak > 0:
            maximum = max(maximum, (peak - point.total_equity) / peak * Decimal(100))
    gross_profit = sum(
        (trade.profit_loss for trade in result.trades if trade.profit_loss > 0), Decimal(0)
    )
    gross_loss = -sum(
        (trade.profit_loss for trade in result.trades if trade.profit_loss < 0), Decimal(0)
    )
    profit_factor = None if gross_loss == 0 else published_decimal(gross_profit / gross_loss)
    observations = (initial, *(point.total_equity for point in result.equity_curve.points))
    returns = tuple(
        (current - previous) / previous
        for previous, current in pairwise(observations)
        if previous != 0
    )
    sharpe: Decimal | None = None
    if len(returns) >= 2:
        mean = sum(returns, Decimal(0)) / len(returns)
        variance = sum(((value - mean) ** 2 for value in returns), Decimal(0)) / (len(returns) - 1)
        if variance != 0:
            with localcontext() as context:
                context.prec = 50
                periods = Decimal(365 * 24 * 60 * 60) / Decimal(
                    result.configuration.timeframe.duration.total_seconds()
                )
                sharpe = published_decimal(mean / variance.sqrt() * periods.sqrt())
    return EvaluationMetrics(
        total_return, win_rate, published_decimal(maximum), count, profit_factor, sharpe
    )
