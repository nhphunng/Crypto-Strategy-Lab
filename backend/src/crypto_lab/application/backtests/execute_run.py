from __future__ import annotations

import logging
from dataclasses import dataclass
from time import perf_counter
from uuid import UUID

from crypto_lab.application.backtests.ports import (
    BacktestRepository,
    Clock,
    DatasetReader,
    ExecutionPolicyReader,
    StrategyAnalyzer,
)
from crypto_lab.domain.backtest.configuration import RunStatus
from crypto_lab.domain.backtest.engine import execute_backtest
from crypto_lab.domain.backtest.errors import BacktestError, BacktestErrorCode
from crypto_lab.domain.backtest.result import BacktestResult
from crypto_lab.domain.market_data.dataset import DatasetStatus

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ExecuteBacktestRun:
    repository: BacktestRepository
    datasets: DatasetReader
    strategies: StrategyAnalyzer
    policies: ExecutionPolicyReader
    clock: Clock

    async def execute(self, run_id: UUID, request_id: str) -> BacktestResult:
        run = await self.repository.get_run(run_id)
        if run is None:
            raise BacktestError(
                BacktestErrorCode.CONFIGURATION_INVALID, "backtest run is unavailable"
            )
        existing = await self.repository.get_result_for_run(run_id)
        if existing is not None:
            if run.status is RunStatus.REQUESTED:
                reused = run.running(self.clock.now())
                await self.repository.update_run(reused)
                await self.repository.update_run(reused.completed(self.clock.now()))
            return existing
        if run.status is not RunStatus.REQUESTED:
            raise BacktestError(BacktestErrorCode.JOB_CONFLICT, "backtest run cannot be started")
        running = run.running(self.clock.now())
        await self.repository.update_run(running)
        started = perf_counter()
        try:
            dataset = await self.datasets.get_complete(run.configuration.dataset_id)
            if dataset is None or dataset.metadata.status is not DatasetStatus.COMPLETE:
                raise BacktestError(
                    BacktestErrorCode.DATASET_INELIGIBLE, "complete dataset is unavailable"
                )
            analysis = await self.strategies.analyze(
                run.configuration.strategy_definition_id, run.configuration.dataset_id, request_id
            )
            policy = await self.policies.get(
                run.configuration.execution_policy_id, run.configuration.execution_policy_version
            )
            if policy is None:
                raise BacktestError(
                    BacktestErrorCode.CONFIGURATION_INVALID, "execution policy is unavailable"
                )
            duration = max(0, int((perf_counter() - started) * 1000))
            result = execute_backtest(
                run.configuration,
                dataset.candles,
                analysis,
                policy,
                created_at=self.clock.now(),
                execution_duration_ms=duration,
            )
            persisted = await self.repository.save_result(result)
            await self.repository.update_run(running.completed(self.clock.now()))
            logger.info(
                "backtest_completed",
                extra={
                    "request_id": request_id,
                    "run_id": str(run_id),
                    "result_checksum": persisted.result_checksum,
                },
            )
            return persisted
        except Exception as exc:
            code = (
                exc.code.value
                if isinstance(exc, BacktestError)
                else BacktestErrorCode.EXECUTION_FAILED.value
            )
            await self.repository.update_run(running.failed(self.clock.now(), code))
            logger.info(
                "backtest_failed",
                extra={"request_id": request_id, "run_id": str(run_id), "failure_code": code},
            )
            raise
