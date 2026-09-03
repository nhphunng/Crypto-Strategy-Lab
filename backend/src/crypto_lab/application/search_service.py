from __future__ import annotations

import asyncio
from datetime import datetime
from decimal import Decimal
from time import monotonic
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from crypto_lab.application.strategies.save_configuration import (
    SaveStrategyConfigurationCommand,
    StrategyCombinationInput,
    StrategyConfigurationMemberInput,
)
from crypto_lab.domain.backtest.configuration import BacktestConfiguration
from crypto_lab.domain.search import CandidateMember, StrategyCandidate, StrategyGenerator
from crypto_lab.domain.strategy.configuration import CombinationMethod
from crypto_lab.domain.strategy.signal import SignalAction


class SearchEventHub:
    def __init__(self) -> None:
        self._subscribers: dict[UUID, set[asyncio.Queue[dict[str, object]]]] = {}

    async def publish(self, run_id: UUID, payload: dict[str, object]) -> None:
        event = {"eventType": "SEARCH_PROGRESS", "version": 1, "payload": payload}
        for queue in tuple(self._subscribers.get(run_id, ())):
            if queue.full():
                _ = queue.get_nowait()
            queue.put_nowait(event)

    def subscribe(self, run_id: UUID) -> asyncio.Queue[dict[str, object]]:
        queue: asyncio.Queue[dict[str, object]] = asyncio.Queue(maxsize=8)
        self._subscribers.setdefault(run_id, set()).add(queue)
        return queue

    def unsubscribe(self, run_id: UUID, queue: asyncio.Queue[dict[str, object]]) -> None:
        subscribers = self._subscribers.get(run_id)
        if subscribers is not None:
            subscribers.discard(queue)
            if not subscribers:
                self._subscribers.pop(run_id, None)


class StrategySearchService:
    def __init__(
        self,
        *,
        repository: Any,
        generator: StrategyGenerator,
        configurations: Any,
        datasets: Any,
        analyzer: Any,
        create_backtest: Any,
        execute_backtest: Any,
        evaluate_backtest: Any,
        leaderboard: Any,
        clock: Any,
        hub: SearchEventHub,
        execution_policy: Any,
        evaluation_policy: Any,
        scoring_policy: Any,
    ) -> None:
        self.repository = repository
        self.generator = generator
        self.configurations = configurations
        self.datasets = datasets
        self.analyzer = analyzer
        self.create_backtest = create_backtest
        self.execute_backtest = execute_backtest
        self.evaluate_backtest = evaluate_backtest
        self.leaderboard = leaderboard
        self.clock = clock
        self.hub = hub
        self.execution_policy = execution_policy
        self.evaluation_policy = evaluation_policy
        self.scoring_policy = scoring_policy
        self._tasks: dict[UUID, asyncio.Task[None]] = {}

    async def create(
        self,
        *,
        dataset_id: UUID,
        strategy_ids: tuple[str, ...],
        minimum_size: int,
        maximum_size: int,
        candidate_limit: int,
        timeout_seconds: int,
        no_improvement_limit: int,
        seed: int,
        run_id: UUID | None = None,
        origin: str = "MANUAL",
        loop_key: str | None = None,
        cycle_index: int | None = None,
    ) -> Any:
        dataset = await self.datasets.get_complete(dataset_id)
        if dataset is None:
            raise ValueError("complete dataset is unavailable")
        now = self.clock.now()
        run = await self.repository.create(
            {
                "id": run_id or uuid4(),
                "origin": origin,
                "loop_key": loop_key,
                "cycle_index": cycle_index,
                "status": "QUEUED",
                "dataset_id": dataset_id,
                "strategy_ids": list(strategy_ids),
                "minimum_size": minimum_size,
                "maximum_size": maximum_size,
                "candidate_limit": candidate_limit,
                "timeout_seconds": timeout_seconds,
                "no_improvement_limit": no_improvement_limit,
                "seed": seed,
                "generator_id": self.generator.generator_id,
                "generator_version": self.generator.version,
                "generated": 0,
                "running": 0,
                "succeeded": 0,
                "failed": 0,
                "created_at": now,
            }
        )
        if run.status in ("QUEUED", "RUNNING") and run.id not in self._tasks:
            self._tasks[run.id] = asyncio.create_task(
                self._run(run.id), name=f"strategy-search-{run.id}"
            )
        return run

    async def wait(self, run_id: UUID) -> Any:
        task = self._tasks.get(run_id)
        if task is not None:
            await task
        return await self.repository.get(run_id)

    async def cancel(self, run_id: UUID) -> bool:
        changed = await self.repository.cancel(run_id, self.clock.now())
        if changed:
            row = await self.repository.get(run_id)
            if row is not None:
                await self.hub.publish(run_id, search_run_payload(row))
        return bool(changed)

    async def close(self) -> None:
        tasks = tuple(self._tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _run(self, run_id: UUID) -> None:
        started_at, started = self.clock.now(), monotonic()
        best: Decimal | None = None
        stale = 0
        try:
            row = await self.repository.get(run_id)
            assert row is not None
            if row.status == "CANCELLED":
                return
            await self.repository.patch(
                run_id, status="RUNNING", started_at=row.started_at or started_at
            )
            dataset = await self.datasets.get_complete(row.dataset_id)
            if dataset is None:
                raise ValueError("complete dataset is unavailable")
            # Generation is a durable producer phase. Once generated is set,
            # recovery consumes the stored queue without consulting the registry.
            if row.generated == 0:
                candidates = self.generator.generate(
                    tuple(row.strategy_ids),
                    row.minimum_size,
                    row.maximum_size,
                    row.candidate_limit,
                    row.seed,
                    dataset.metadata.candle_count,
                )
                generated = 0
                for sequence, candidate in enumerate(candidates, 1):
                    await self.repository.add_candidate(
                        {
                            "search_run_id": run_id,
                            "sequence": sequence,
                            "fingerprint": candidate.fingerprint,
                            "display_name": candidate.display_name,
                            "members": [
                                {
                                    "strategyId": member.strategy_id,
                                    "strategyVersion": member.strategy_version,
                                    "parameters": member.parameters,
                                }
                                for member in candidate.members
                            ],
                            "status": "QUEUED",
                            "created_at": self.clock.now(),
                        }
                    )
                    generated = sequence
                await self.repository.patch(run_id, generated=generated)
            items = await self.repository.candidates(run_id, limit=row.candidate_limit)
            queue = [
                (
                    StrategyCandidate(
                        item.fingerprint,
                        item.display_name,
                        tuple(
                            CandidateMember(
                                member["strategyId"],
                                member["strategyVersion"],
                                member["parameters"],
                            )
                            for member in item.members
                        ),
                    ),
                    item,
                )
                for item in sorted(items, key=lambda item: item.sequence)
            ]
            reason = "SEARCH_SPACE_EXHAUSTED"
            succeeded = failed = 0
            for sequence, (candidate, item) in enumerate(queue, 1):
                current = await self.repository.get(run_id)
                if current is None or current.status == "CANCELLED":
                    return
                if item.status not in ("COMPLETED", "FAILED"):
                    if monotonic() - started >= row.timeout_seconds:
                        reason = "TIMEOUT"
                        break
                    if stale >= row.no_improvement_limit:
                        reason = "NO_IMPROVEMENT"
                        break
                    await self.repository.patch_candidate(item.id, status="RUNNING")
                    await self.repository.patch(
                        run_id, running=1, current_candidate=candidate.display_name
                    )
                    await self._publish(run_id)
                    try:
                        score, backtest_id, evaluation_id = await self._evaluate(
                            row, candidate, sequence
                        )
                        await self.repository.patch_candidate(
                            item.id,
                            status="COMPLETED",
                            score=score,
                            backtest_run_id=backtest_id,
                            evaluation_result_id=evaluation_id,
                            completed_at=self.clock.now(),
                        )
                        item.status, item.score = "COMPLETED", score
                    except Exception as exc:
                        await self.repository.patch_candidate(
                            item.id,
                            status="FAILED",
                            failure_code=type(exc).__name__[:64],
                            completed_at=self.clock.now(),
                        )
                        item.status = "FAILED"
                if item.status == "COMPLETED":
                    succeeded += 1
                    if best is None or item.score > best:
                        best, stale = item.score, 0
                        await self.repository.patch(
                            run_id, top_score=best, top_candidate=candidate.display_name
                        )
                    else:
                        stale += 1
                else:
                    failed += 1
                    stale += 1
                await self.repository.patch(run_id, succeeded=succeeded, failed=failed, running=0)
                await self._publish(run_id)
                if sequence >= row.candidate_limit:
                    reason = "CANDIDATE_LIMIT"
            # A cancellation arriving during the final candidate must remain cancelled.
            current = await self.repository.get(run_id)
            if current is None or current.status == "CANCELLED":
                return
            for _, item in queue:
                if item.status == "QUEUED":
                    await self.repository.patch_candidate(
                        item.id, status="CANCELLED", completed_at=self.clock.now()
                    )
            await self.repository.patch(
                run_id,
                status="COMPLETED",
                stop_reason=reason,
                completed_at=self.clock.now(),
                current_candidate=None,
                running=0,
            )
            await self._publish(run_id)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            await self.repository.patch(
                run_id,
                status="FAILED",
                stop_reason="SEARCH_FAILED",
                failure_detail=str(exc)[:1000],
                completed_at=self.clock.now(),
                current_candidate=None,
                running=0,
            )
            await self._publish(run_id)
        finally:
            self._tasks.pop(run_id, None)

    async def _evaluate(
        self, row: Any, candidate: Any, sequence: int
    ) -> tuple[Decimal, UUID, UUID]:
        dataset = await self.datasets.get_complete(row.dataset_id)
        if dataset is None:
            raise ValueError("dataset became unavailable")
        configuration = await self.configurations.execute(
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
        analysis = await self.analyzer.analyze(
            configuration.root_definition_id, row.dataset_id, f"search-{row.id}-{sequence}"
        )
        definition, provenance = analysis.strategy_definition, analysis.context_provenance
        job_id = uuid5(
            NAMESPACE_URL,
            f"search|{row.id}|{candidate.fingerprint}|{provenance.context_fingerprint}",
        )
        metadata = dataset.metadata
        run = await self.create_backtest.execute(
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
                self.execution_policy.id,
                self.execution_policy.version,
                Decimal("10000"),
                Decimal("0.0004"),
                Decimal("0.0002"),
                row.seed + sequence,
                sentiment_provenance=provenance.sentiment,
            )
        )
        result = await self.execute_backtest.execute(
            run.configuration.run_id, f"search-{row.id}-{sequence}", resume_interrupted=True
        )
        evaluation = await self.evaluate_backtest.execute(
            result.id,
            self.evaluation_policy.id,
            self.evaluation_policy.version,
            self.scoring_policy.id,
            self.scoring_policy.version,
        )
        await self.leaderboard.on_evaluation_completed(evaluation.id, request_id=f"search-{row.id}")
        return evaluation.score, run.configuration.run_id, evaluation.id

    async def _publish(self, run_id: UUID) -> None:
        row = await self.repository.get(run_id)
        if row is not None:
            await self.hub.publish(run_id, search_run_payload(row))


def search_run_payload(row: Any) -> dict[str, object]:
    def stamp(value: datetime | None) -> str | None:
        return None if value is None else value.isoformat().replace("+00:00", "Z")

    return {
        "id": str(row.id),
        "type": "SEARCH",
        "origin": row.origin,
        "cycleIndex": row.cycle_index,
        "status": row.status,
        "datasetId": str(row.dataset_id),
        "strategyIds": list(row.strategy_ids),
        "minimumSize": row.minimum_size,
        "maximumSize": row.maximum_size,
        "candidateLimit": row.candidate_limit,
        "generated": row.generated,
        "running": row.running,
        "succeeded": row.succeeded,
        "failed": row.failed,
        "topScore": None if row.top_score is None else str(row.top_score),
        "topCandidate": row.top_candidate,
        "currentCandidate": row.current_candidate,
        "generator": f"{row.generator_id}@{row.generator_version}",
        "seed": row.seed,
        "stopReason": row.stop_reason,
        "failureDetail": row.failure_detail,
        "createdAt": stamp(row.created_at),
        "startedAt": stamp(row.started_at),
        "completedAt": stamp(row.completed_at),
    }
