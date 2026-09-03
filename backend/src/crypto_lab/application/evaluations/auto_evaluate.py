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
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Any, Protocol
from uuid import NAMESPACE_URL, UUID, uuid5

from crypto_lab.application.search_service import StrategySearchService
from crypto_lab.domain.backtest.configuration import canonical_hash
from crypto_lab.domain.market_data.candle import MarketSelection
from crypto_lab.domain.market_data.dataset import DatasetStatus
from crypto_lab.domain.market_data.ranges import TimeRange
from crypto_lab.domain.market_data.timeframe import Timeframe

logger = logging.getLogger("crypto_lab.auto_evaluation")
search_loop_logger = logging.getLogger("crypto_lab.search_loop")

AUTO_NAMESPACE = uuid5(NAMESPACE_URL, "crypto-lab/auto-evaluation/v1")
SEARCH_LOOP_NAMESPACE = uuid5(NAMESPACE_URL, "crypto-lab/search-loop/v1")


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
            sentiment_provenance=analysis.context_provenance.sentiment,
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


class SearchLoopStatus(StrEnum):
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"


@dataclass(frozen=True, slots=True)
class SearchLoopSettings:
    """What the search loop searches over, and how often."""

    provider: str = "BINANCE"
    pair: str = "BTCUSDT"
    timeframe: Timeframe = Timeframe.FIFTEEN_MINUTES
    candles: int = 500
    candidates_per_cycle: int = 10
    minimum_size: int = 2
    maximum_size: int = 4
    base_seed: int = 424242
    interval_seconds: float = 1800.0


@dataclass(frozen=True, slots=True)
class SearchLoopCycleReport:
    """What one cycle of candidate generation and evaluation achieved."""

    cycle_index: int
    dataset_id: UUID | None = None
    dataset_building: bool = False
    generated: int = 0
    succeeded: int = 0
    failed: int = 0
    top_score: Decimal | None = None
    top_candidate: str | None = None
    error: str | None = None

    @property
    def completed(self) -> bool:
        return self.dataset_id is not None and not self.dataset_building and self.error is None


@dataclass(slots=True)
class SearchLoopStats:
    """Running observability totals for the background search loop."""

    status: SearchLoopStatus = SearchLoopStatus.STOPPED
    cycles_completed: int = 0
    candidates_generated: int = 0
    candidates_succeeded: int = 0
    candidates_failed: int = 0
    last_cycle_at: datetime | None = None
    last_error: str | None = None

    def to_payload(self) -> dict[str, object]:
        def stamp(value: datetime | None) -> str | None:
            return None if value is None else value.isoformat().replace("+00:00", "Z")

        return {
            "status": self.status.value,
            "cyclesCompleted": self.cycles_completed,
            "candidatesGenerated": self.candidates_generated,
            "candidatesSucceeded": self.candidates_succeeded,
            "candidatesFailed": self.candidates_failed,
            "lastCycleAt": stamp(self.last_cycle_at),
            "lastError": self.last_error,
        }


class SearchLoopPipeline:
    """Schedule durable search runs through the shared generator and executor."""

    def __init__(
        self,
        *,
        settings: SearchLoopSettings,
        datasets: Any,
        discovery: Any,
        search: StrategySearchService,
        clock: Any,
    ) -> None:
        self._settings = settings
        self._datasets = datasets
        self._discovery = discovery
        self._search = search
        self._clock = clock
        self._loop_key = canonical_hash(asdict(settings))

    async def restore(self) -> int:
        runs = await self._search.repository.background_runs(self._loop_key)
        if not runs:
            return 0
        latest = runs[-1]
        return int(latest.cycle_index) + (latest.status not in ("QUEUED", "RUNNING"))

    async def snapshot(self) -> SearchLoopStats:
        runs = await self._search.repository.background_runs(self._loop_key)
        latest = runs[-1] if runs else None
        return SearchLoopStats(
            cycles_completed=sum(row.status == "COMPLETED" for row in runs),
            candidates_generated=sum(row.generated for row in runs),
            candidates_succeeded=sum(row.succeeded for row in runs),
            candidates_failed=sum(row.failed for row in runs),
            last_cycle_at=latest.completed_at if latest else None,
            last_error=latest.failure_detail if latest else None,
        )

    async def run_cycle(
        self, cycle_index: int, *, request_id: str | None = None
    ) -> SearchLoopCycleReport:
        runs = await self._search.repository.background_runs(self._loop_key)
        existing = next((row for row in runs if row.cycle_index == cycle_index), None)
        if existing is not None:
            dataset_id = existing.dataset_id
        else:
            dataset_id, building = await self._ensure_dataset(
                request_id or f"search-loop-{cycle_index}"
            )
            if dataset_id is None or building:
                return SearchLoopCycleReport(cycle_index, dataset_id, building)
        settings = self._settings
        run = await self._search.create(
            run_id=uuid5(SEARCH_LOOP_NAMESPACE, f"{self._loop_key}|{cycle_index}"),
            origin="BACKGROUND",
            loop_key=self._loop_key,
            cycle_index=cycle_index,
            dataset_id=dataset_id,
            strategy_ids=tuple(entry.strategy_id for entry in self._discovery.list()),
            minimum_size=settings.minimum_size,
            maximum_size=settings.maximum_size,
            candidate_limit=settings.candidates_per_cycle,
            timeout_seconds=max(60, int(settings.interval_seconds)),
            no_improvement_limit=settings.candidates_per_cycle,
            seed=settings.base_seed + cycle_index,
        )
        run = await self._search.wait(run.id)
        return SearchLoopCycleReport(
            cycle_index,
            dataset_id,
            False,
            run.generated,
            run.succeeded,
            run.failed,
            run.top_score,
            run.top_candidate,
            run.failure_detail
            if run.status == "FAILED"
            else ("Search was cancelled" if run.status == "CANCELLED" else None),
        )

    async def _ensure_dataset(self, request_id: str) -> tuple[UUID | None, bool]:
        """Materialize the configured window of closed Candles."""

        settings = self._settings
        selection = MarketSelection(settings.provider, settings.pair, settings.timeframe)
        time_range = self._window(settings)
        result = await self._datasets.materialize(selection, time_range, request_id=request_id)
        dataset = result.dataset
        if dataset.status is DatasetStatus.BUILDING or result.building:
            search_loop_logger.info(
                "search_loop_dataset_building",
                extra={"fields": {"dataset_id": str(dataset.id)}},
            )
            return dataset.id, True
        if dataset.status is not DatasetStatus.COMPLETE:
            search_loop_logger.warning(
                "search_loop_dataset_unavailable",
                extra={"fields": {"status": dataset.status.value}},
            )
            return None, False
        return dataset.id, False

    def _window(self, settings: SearchLoopSettings) -> TimeRange:
        """A stable window of fully closed Candles ending at the last boundary."""

        timeframe = settings.timeframe
        end = timeframe.floor(self._clock.now())
        start = end - timedelta(seconds=timeframe.seconds * settings.candles)
        return TimeRange(start, end)


@dataclass(slots=True)
class SearchLoopRunner:
    """Runs the search pipeline at startup, then on a fixed interval; pausable via API.

    Pause/resume are poll-based: the run loop only checks the pause flag
    before *starting* a new cycle, so an in-flight cycle always finishes
    rather than being aborted mid-candidate.
    """

    pipeline: SearchLoopPipeline
    clock: Any
    interval_seconds: float = 1800.0
    retry_seconds: float = 30.0
    _task: asyncio.Task[None] | None = field(default=None, init=False)
    _cycle_index: int = field(default=0, init=False)
    _status: SearchLoopStatus = field(default=SearchLoopStatus.STOPPED, init=False)
    _stats: SearchLoopStats = field(default_factory=SearchLoopStats, init=False)

    def start(self) -> None:
        if self._task is None:
            self._status = SearchLoopStatus.RUNNING
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        task = self._task
        self._task = None
        self._status = SearchLoopStatus.STOPPED
        if task is None:
            return
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):  # pragma: no cover - shutdown path
            pass

    def pause(self) -> None:
        self._status = SearchLoopStatus.PAUSED

    def resume(self) -> None:
        self._status = SearchLoopStatus.RUNNING

    def status(self) -> SearchLoopStats:
        return replace(self._stats, status=self._status)

    async def snapshot(self) -> SearchLoopStats:
        if isinstance(self.pipeline, SearchLoopPipeline):
            persisted = await self.pipeline.snapshot()
            return replace(
                persisted,
                status=self._status,
                last_error=self._stats.last_error or persisted.last_error,
            )
        return self.status()

    async def _run(self) -> None:
        restored = False
        while True:
            if self._status is SearchLoopStatus.PAUSED:
                await asyncio.sleep(self.retry_seconds)
                continue
            delay = self.interval_seconds
            try:
                if not restored and isinstance(self.pipeline, SearchLoopPipeline):
                    self._cycle_index = await self.pipeline.restore()
                    self._stats = await self.pipeline.snapshot()
                    restored = True
                report = await self.pipeline.run_cycle(
                    self._cycle_index, request_id=f"search-loop-{self._cycle_index}"
                )
                self._stats.cycles_completed += int(report.completed)
                self._stats.candidates_generated += report.generated
                self._stats.candidates_succeeded += report.succeeded
                self._stats.candidates_failed += report.failed
                self._stats.last_cycle_at = self.clock.now()
                self._stats.last_error = report.error
                if not report.completed:
                    # A building/unavailable dataset is expected on a cold
                    # start; retry sooner.
                    delay = self.retry_seconds
                if report.completed or report.error:
                    self._cycle_index += 1
            except asyncio.CancelledError:  # pragma: no cover - shutdown path
                raise
            except Exception as exc:
                search_loop_logger.warning("search_loop_cycle_failed", exc_info=False)
                self._stats.last_error = str(exc)[:500]
                delay = self.retry_seconds
            await asyncio.sleep(delay)
