from __future__ import annotations

from dataclasses import dataclass

from crypto_lab.application.backtests.ports import BacktestRepository, Clock
from crypto_lab.domain.backtest.configuration import BacktestConfiguration, BacktestRun, RunStatus


@dataclass(frozen=True, slots=True)
class CreateBacktestRun:
    repository: BacktestRepository
    clock: Clock

    async def execute(self, configuration: BacktestConfiguration) -> BacktestRun:
        run = BacktestRun(configuration, RunStatus.REQUESTED, self.clock.now())
        return await self.repository.create_or_resolve_run(run)
