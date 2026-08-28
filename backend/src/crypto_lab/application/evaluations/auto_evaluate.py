"""Keep the leaderboard populated without a manual backtest.

A fresh deployment has no Evaluation Result, so the leaderboard correctly shows
that nothing is ranked yet. This pipeline closes that gap: it materializes the
configured dataset, runs every registered Strategy over it, evaluates each
result under the platform policies, and hands the evaluation to the leaderboard.

Every step is idempotent. Runs, results, and evaluations are resolved by their
immutable identity, so repeating a cycle re-uses what already exists instead of
producing duplicates, and the leaderboard sees no visible change.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol
from uuid import NAMESPACE_URL, UUID, uuid5

from crypto_lab.domain.market_data.candle import MarketSelection
from crypto_lab.domain.market_data.dataset import DatasetStatus
from crypto_lab.domain.market_data.ranges import TimeRange
from crypto_lab.domain.market_data.timeframe import Timeframe

logger = logging.getLogger("crypto_lab.auto_evaluation")

AUTO_NAMESPACE = uuid5(NAMESPACE_URL, "crypto-lab/auto-evaluation/v1")


@dataclass(frozen=True, slots=True)
class AutoEvaluationSettings:
    """What the pipeline evaluates, and how often."""

    provider: str = "BINANCE"
    pair: str = "BTCUSDT"
    timeframe: Timeframe = Timeframe.FIFTEEN_MINUTES
    candles: int = 500
    initial_capital: Decimal = Decimal("10000")
    fee_rate: Decimal = Decimal("0.0004")
    slippage_rate: Decimal = Decimal("0.0002")
    random_seed: int = 424242
    interval_seconds: float = 3600.0


@dataclass(frozen=True, slots=True)
class AutoEvaluationReport:
    """What one cycle achieved, for logs and tests."""

    dataset_id: UUID | None = None
    dataset_building: bool = False
    evaluated: tuple[UUID, ...] = ()
    skipped: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()

    @property
    def completed(self) -> bool:
        return self.dataset_id is not None and not self.dataset_building


class PolicyBundle(Protocol):
    """Read-only view of an immutable policy record."""

    @property
    def id(self) -> UUID: ...

    @property
    def version(self) -> Any: ...


class AutoEvaluationPipeline:
    """One cycle: dataset, backtests, evaluations, leaderboard ingestion."""

    def __init__(
        self,
        *,
        settings: AutoEvaluationSettings,
        datasets: Any,
        dataset_reader: Any,
        discovery: Any,
        definitions: Any,
        analyzer: Any,
        create_backtest: Any,
        execute_backtest: Any,
        evaluate_backtest: Any,
        ingestion: Any,
        clock: Any,
        execution_policy: PolicyBundle,
        evaluation_policy: PolicyBundle,
        scoring_policy: PolicyBundle,
    ) -> None:
        self._settings = settings
        self._datasets = datasets
        self._dataset_reader = dataset_reader
        self._discovery = discovery
        self._definitions = definitions
        self._analyzer = analyzer
        self._create_backtest = create_backtest
        self._execute_backtest = execute_backtest
        self._evaluate_backtest = evaluate_backtest
        self._ingestion = ingestion
        self._clock = clock
        self._execution_policy = execution_policy
        self._evaluation_policy = evaluation_policy
        self._scoring_policy = scoring_policy

    async def run_once(self, *, request_id: str = "auto-evaluation") -> AutoEvaluationReport:
        dataset_id, building = await self._ensure_dataset(request_id)
        if dataset_id is None or building:
            return AutoEvaluationReport(dataset_id=dataset_id, dataset_building=building)

        evaluated: list[UUID] = []
        skipped: list[str] = []
        failures: list[str] = []
        for entry in self._discovery.list():
            label = f"{entry.strategy_id}@{entry.strategy_version}"
            try:
                evaluation_id = await self._evaluate_strategy(entry, dataset_id, request_id)
            except Exception as error:  # one strategy must not stop the others
                logger.warning(
                    "auto_evaluation_strategy_failed",
                    extra={
                        "fields": {
                            "strategy": label,
                            "reason": type(error).__name__,
                            "detail": str(error)[:200],
                        }
                    },
                )
                failures.append(label)
                continue
            if evaluation_id is None:
                skipped.append(label)
                continue
            evaluated.append(evaluation_id)

        logger.info(
            "auto_evaluation_cycle_completed",
            extra={
                "fields": {
                    "dataset_id": str(dataset_id),
                    "evaluated": len(evaluated),
                    "skipped": len(skipped),
                    "failed": len(failures),
                }
            },
        )
        return AutoEvaluationReport(
            dataset_id=dataset_id,
            evaluated=tuple(evaluated),
            skipped=tuple(skipped),
            failures=tuple(failures),
        )

    # -- steps ---------------------------------------------------------------

    async def _ensure_dataset(self, request_id: str) -> tuple[UUID | None, bool]:
        """Materialize the configured window of closed Candles."""

        settings = self._settings
        selection = MarketSelection(settings.provider, settings.pair, settings.timeframe)
        time_range = self._window(settings)
        result = await self._datasets.materialize(selection, time_range, request_id=request_id)
        dataset = result.dataset
        if dataset.status is DatasetStatus.BUILDING or result.building:
            logger.info(
                "auto_evaluation_dataset_building",
                extra={"fields": {"dataset_id": str(dataset.id)}},
            )
            return dataset.id, True
        if dataset.status is not DatasetStatus.COMPLETE:
            logger.warning(
                "auto_evaluation_dataset_unavailable",
                extra={"fields": {"status": dataset.status.value}},
            )
            return None, False
        return dataset.id, False

    def _window(self, settings: AutoEvaluationSettings) -> TimeRange:
        """A stable window of fully closed Candles ending at the last boundary."""

        timeframe = settings.timeframe
        end = timeframe.floor(self._clock.now())
        start = end - timedelta(seconds=timeframe.seconds * settings.candles)
        return TimeRange(start, end)

    async def _evaluate_strategy(
        self,
        entry: Any,
        dataset_id: UUID,
        request_id: str,
    ) -> UUID | None:
        definition = await self._definitions.create_or_resolve(
            self._definition_for(entry),
        )
        analysis = await self._analyzer.analyze(definition.id, dataset_id, request_id)
        dataset = await self._dataset_reader.get_complete(dataset_id)
        if dataset is None:
            return None
        run = await self._create_backtest.execute(
            self._configuration(definition, analysis, dataset, dataset_id),
        )
        result = await self._execute_backtest.execute(run.configuration.run_id, request_id)
        evaluation = await self._evaluate_backtest.execute(
            result.id,
            self._evaluation_policy.id,
            str(self._evaluation_policy.version),
            self._scoring_policy.id,
            str(self._scoring_policy.version),
        )
        await self._ingestion.on_evaluation_completed(evaluation.id, request_id=request_id)
        return UUID(str(evaluation.id))

    def _definition_for(self, entry: Any) -> Any:
        from crypto_lab.domain.strategy.definition import StrategyDefinition

        metadata = entry.metadata
        parameters = entry.strategy.validate_parameters({})
        return StrategyDefinition(
            # Deterministic identity so repeated cycles resolve the same row.
            id=uuid5(
                AUTO_NAMESPACE,
                f"definition|{metadata.strategy_id}|{parameters.canonical_fingerprint}",
            ),
            strategy_id=metadata.strategy_id,
            strategy_type=metadata.strategy_type,
            strategy_version=metadata.strategy_version,
            contract_version=metadata.contract_version,
            parameters=parameters,
            created_at=self._clock.now(),
        )

    def _configuration(
        self,
        definition: Any,
        analysis: Any,
        dataset: Any,
        dataset_id: UUID,
    ) -> Any:
        from crypto_lab.domain.backtest.configuration import BacktestConfiguration

        settings = self._settings
        metadata = dataset.metadata
        job_id = uuid5(AUTO_NAMESPACE, f"job|{dataset_id}|{definition.id}")
        return BacktestConfiguration(
            uuid5(job_id, "run"),
            job_id,
            dataset_id,
            metadata.schema_version,
            metadata.checksum,
            metadata.selection.provider,
            metadata.selection.pair,
            metadata.selection.timeframe,
            metadata.time_range.start_time,
            metadata.time_range.end_time,
            definition.id,
            definition.strategy_id,
            str(definition.strategy_version),
            str(analysis.contract_version),
            definition.parameters.canonical_fingerprint,
            analysis.context_provenance.context_fingerprint,
            self._execution_policy.id,
            str(self._execution_policy.version),
            settings.initial_capital,
            settings.fee_rate,
            settings.slippage_rate,
            settings.random_seed,
        )


@dataclass(slots=True)
class AutoEvaluationLoop:
    """Runs the pipeline at startup and then on a fixed interval."""

    pipeline: AutoEvaluationPipeline
    interval_seconds: float = 3600.0
    retry_seconds: float = 30.0
    _task: asyncio.Task[None] | None = field(default=None, init=False)

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        task = self._task
        self._task = None
        if task is None:
            return
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):  # pragma: no cover - shutdown path
            pass

    async def _run(self) -> None:
        while True:
            delay = self.interval_seconds
            try:
                report = await self.pipeline.run_once()
                # A building dataset is expected on a cold start; retry sooner.
                if not report.completed:
                    delay = self.retry_seconds
            except asyncio.CancelledError:  # pragma: no cover - shutdown path
                raise
            except Exception:
                logger.warning("auto_evaluation_cycle_failed", exc_info=False)
                delay = self.retry_seconds
            await asyncio.sleep(delay)


def utc_window_end(clock: Any, timeframe: Timeframe) -> datetime:
    """Exposed for tests that assert the window aligns to closed Candles."""

    return timeframe.floor(clock.now())
