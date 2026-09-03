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
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Any, Protocol
from uuid import NAMESPACE_URL, UUID, uuid5

from crypto_lab.application.strategies.save_configuration import (
    SaveStrategyConfigurationCommand,
    StrategyCombinationInput,
    StrategyConfigurationMemberInput,
)
from crypto_lab.domain.market_data.candle import MarketSelection
from crypto_lab.domain.market_data.dataset import DatasetStatus
from crypto_lab.domain.market_data.ranges import TimeRange
from crypto_lab.domain.market_data.timeframe import Timeframe
from crypto_lab.domain.search import RandomSearchGenerator, StrategyCandidate
from crypto_lab.domain.strategy.configuration import CombinationMethod
from crypto_lab.domain.strategy.signal import SignalAction

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


# ---------------------------------------------------------------------------
# Search loop: a background process that continuously *discovers* new
# strategy combinations (via the random search generator) instead of merely
# re-backtesting already-registered strategies. It shares the auto-evaluation
# module's idioms (deterministic identity via uuid5, catch-log-continue
# failure isolation, start/stop as an asyncio.Task) but is additive: nothing
# above this point is modified by it.
# ---------------------------------------------------------------------------


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

    @property
    def completed(self) -> bool:
        return self.dataset_id is not None and not self.dataset_building


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
    """One cycle: generate genuinely new candidates, backtest, evaluate, rank.

    Unlike AutoEvaluationPipeline (which replays the fixed set of registered
    strategies), this pulls fresh combinations from RandomSearchGenerator on
    every cycle. ``run_cycle`` is a pure function of ``cycle_index`` plus
    whatever is currently in the registry/dataset -- it holds no mutable
    instance state that affects identity -- so re-running the same index
    resolves to the same run/job/evaluation identity instead of duplicating
    work. That is what the idempotency test asserts.
    """

    def __init__(
        self,
        *,
        settings: SearchLoopSettings,
        datasets: Any,
        dataset_reader: Any,
        discovery: Any,
        generator: RandomSearchGenerator,
        configurations: Any,
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
        self._generator = generator
        self._configurations = configurations
        self._analyzer = analyzer
        self._create_backtest = create_backtest
        self._execute_backtest = execute_backtest
        self._evaluate_backtest = evaluate_backtest
        self._ingestion = ingestion
        self._clock = clock
        self._execution_policy = execution_policy
        self._evaluation_policy = evaluation_policy
        self._scoring_policy = scoring_policy

    async def run_cycle(
        self, cycle_index: int, *, request_id: str | None = None
    ) -> SearchLoopCycleReport:
        req_id = request_id or f"search-loop-{cycle_index}"
        dataset_id, building = await self._ensure_dataset(req_id)
        if dataset_id is None or building:
            return SearchLoopCycleReport(cycle_index, dataset_id, building)

        dataset = await self._dataset_reader.get_complete(dataset_id)
        if dataset is None:
            return SearchLoopCycleReport(cycle_index, dataset_id, False)

        strategy_ids = tuple(entry.strategy_id for entry in self._discovery.list())
        seed = self._settings.base_seed + cycle_index
        try:
            candidates = self._generator.generate(
                strategy_ids,
                self._settings.minimum_size,
                self._settings.maximum_size,
                self._settings.candidates_per_cycle,
                seed,
                dataset.metadata.candle_count,
            )
        except ValueError as error:
            search_loop_logger.warning(
                "search_loop_generation_failed",
                extra={"fields": {"cycle": cycle_index, "reason": str(error)[:200]}},
            )
            return SearchLoopCycleReport(cycle_index, dataset_id, False)

        generated = 0
        succeeded = 0
        failed = 0
        top_score: Decimal | None = None
        top_candidate: str | None = None
        for sequence, candidate in enumerate(candidates, 1):
            generated += 1
            try:
                score = await self._evaluate(
                    dataset, dataset_id, candidate, cycle_index, seed, sequence, req_id
                )
            except Exception as error:  # one bad candidate must not stop the cycle
                failed += 1
                search_loop_logger.warning(
                    "search_loop_candidate_failed",
                    extra={
                        "fields": {
                            "cycle": cycle_index,
                            "fingerprint": candidate.fingerprint,
                            "reason": type(error).__name__,
                            "detail": str(error)[:200],
                        }
                    },
                )
                continue
            succeeded += 1
            if top_score is None or score > top_score:
                top_score, top_candidate = score, candidate.display_name

        search_loop_logger.info(
            "search_loop_cycle_completed",
            extra={
                "fields": {
                    "cycle": cycle_index,
                    "dataset_id": str(dataset_id),
                    "generated": generated,
                    "succeeded": succeeded,
                    "failed": failed,
                }
            },
        )
        return SearchLoopCycleReport(
            cycle_index,
            dataset_id,
            False,
            generated,
            succeeded,
            failed,
            top_score,
            top_candidate,
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

    async def _evaluate(
        self,
        dataset: Any,
        dataset_id: UUID,
        candidate: StrategyCandidate,
        cycle_index: int,
        seed: int,
        sequence: int,
        request_id: str,
    ) -> Decimal:
        from crypto_lab.domain.backtest.configuration import BacktestConfiguration

        configuration = await self._configurations.execute(
            SaveStrategyConfigurationCommand(
                display_name=candidate.display_name,
                provider=dataset.metadata.selection.provider,
                pair=dataset.metadata.selection.pair,
                timeframe=dataset.metadata.selection.timeframe.value,
                members=tuple(
                    StrategyConfigurationMemberInput(
                        item.strategy_id, item.strategy_version, item.parameters, None
                    )
                    for item in candidate.members
                ),
                combination=StrategyCombinationInput(
                    CombinationMethod.MAJORITY, SignalAction.HOLD, Decimal("0.3"), Decimal("-0.3")
                ),
            )
        )
        analysis = await self._analyzer.analyze(
            configuration.root_definition_id, dataset_id, request_id
        )
        definition, provenance = analysis.strategy_definition, analysis.context_provenance
        # Restarts reset cycle_index. Include immutable execution inputs so a
        # new dataset or sentiment context cannot collide with a previous run.
        job_id = uuid5(
            SEARCH_LOOP_NAMESPACE,
            f"cycle|{cycle_index}|{candidate.fingerprint}|{dataset_id}|"
            f"{provenance.context_fingerprint}|{seed + sequence}",
        )
        metadata = dataset.metadata
        run = await self._create_backtest.execute(
            BacktestConfiguration(
                uuid5(job_id, "run"),
                job_id,
                metadata.id,
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
                provenance.context_fingerprint,
                self._execution_policy.id,
                str(self._execution_policy.version),
                Decimal("10000"),
                Decimal("0.0004"),
                Decimal("0.0002"),
                seed + sequence,
            )
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
        score: Decimal = evaluation.score
        return score


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

    async def _run(self) -> None:
        while True:
            if self._status is SearchLoopStatus.PAUSED:
                await asyncio.sleep(self.retry_seconds)
                continue
            delay = self.interval_seconds
            try:
                report = await self.pipeline.run_cycle(
                    self._cycle_index, request_id=f"search-loop-{self._cycle_index}"
                )
                self._stats.cycles_completed += 1
                self._stats.candidates_generated += report.generated
                self._stats.candidates_succeeded += report.succeeded
                self._stats.candidates_failed += report.failed
                self._stats.last_cycle_at = self.clock.now()
                self._stats.last_error = None
                if not report.completed:
                    # A building/unavailable dataset is expected on a cold
                    # start; retry sooner.
                    delay = self.retry_seconds
                # The cycle index always advances, even after a building
                # dataset: re-running the SAME index only ever happens
                # explicitly (e.g. in a test), never through the loop's own
                # forward progression.
                self._cycle_index += 1
            except asyncio.CancelledError:  # pragma: no cover - shutdown path
                raise
            except Exception as exc:
                search_loop_logger.warning("search_loop_cycle_failed", exc_info=False)
                self._stats.last_error = str(exc)[:500]
                delay = self.retry_seconds
                self._cycle_index += 1
            await asyncio.sleep(delay)
