from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from crypto_lab.application.backtests.ports import BacktestRepository
from crypto_lab.domain.backtest.equity import EquityPoint
from crypto_lab.domain.backtest.result import BacktestResult
from crypto_lab.domain.backtest.trade import Trade


@dataclass(frozen=True, slots=True)
class GetBacktestResult:
    repository: BacktestRepository

    async def get(self, result_id: UUID) -> BacktestResult | None:
        return await self.repository.get_result(result_id)

    async def counts(self, result_id: UUID) -> tuple[int, int] | None:
        return await self.repository.result_counts(result_id)

    async def trades(
        self, result_id: UUID, cursor: str | None = None, limit: int = 25
    ) -> tuple[tuple[Trade, ...], str | None]:
        _bounded(limit)
        return await self.repository.list_trades(result_id, cursor, limit)

    async def equity(
        self, result_id: UUID, cursor: str | None = None, limit: int = 25
    ) -> tuple[tuple[EquityPoint, ...], str | None]:
        _bounded(limit)
        return await self.repository.list_equity(result_id, cursor, limit)


def _bounded(limit: int) -> None:
    if not 1 <= limit <= 200:
        raise ValueError("page size must be between 1 and 200")
