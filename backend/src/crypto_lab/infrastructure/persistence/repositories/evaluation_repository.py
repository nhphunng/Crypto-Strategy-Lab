from __future__ import annotations

from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from crypto_lab.domain.evaluation.metrics import EvaluationMetrics
from crypto_lab.domain.evaluation.policy import (
    EvaluationPolicy,
    MetricDirection,
    MetricWeight,
    ScoringPolicy,
)
from crypto_lab.domain.evaluation.result import EvaluationResult
from crypto_lab.infrastructure.persistence.evaluation_models import (
    EvaluationPolicyRow,
    EvaluationResultRow,
    ScoringPolicyRow,
)
from crypto_lab.infrastructure.persistence.repositories.backtest_repository import (
    SqlAlchemyBacktestRepository,
)


class SqlAlchemyEvaluationRepository:
    def __init__(
        self, sessions: async_sessionmaker[AsyncSession], backtests: SqlAlchemyBacktestRepository
    ) -> None:
        self._sessions = sessions
        self._backtests = backtests

    async def ensure_policies(
        self, evaluation: EvaluationPolicy, scoring: ScoringPolicy, created_at: object
    ) -> None:
        async with self._sessions() as session, session.begin():
            await session.execute(
                insert(EvaluationPolicyRow)
                .values(
                    id=evaluation.id,
                    policy_id=evaluation.policy_id,
                    version=evaluation.version,
                    fingerprint=evaluation.fingerprint,
                    rules=evaluation.rules,
                    created_at=created_at,
                )
                .on_conflict_do_nothing(index_elements=["policy_id", "version"])
            )
            await session.execute(
                insert(ScoringPolicyRow)
                .values(
                    id=scoring.id,
                    policy_id=scoring.policy_id,
                    version=scoring.version,
                    name=scoring.name,
                    default_rank_metric=scoring.default_rank_metric,
                    fingerprint=scoring.fingerprint,
                    rules=scoring.rules,
                    created_at=created_at,
                )
                .on_conflict_do_nothing(index_elements=["policy_id", "version"])
            )

    async def get_evaluation(self, policy_id: UUID, version: str) -> EvaluationPolicy | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(EvaluationPolicyRow).where(
                    EvaluationPolicyRow.id == policy_id, EvaluationPolicyRow.version == version
                )
            )
        return None if row is None else EvaluationPolicy(row.id, row.policy_id, row.version)

    async def get_scoring(self, policy_id: UUID, version: str) -> ScoringPolicy | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(ScoringPolicyRow).where(
                    ScoringPolicyRow.id == policy_id, ScoringPolicyRow.version == version
                )
            )
        if row is None:
            return None
        metric_rules = cast(list[dict[str, object]], row.rules["metrics"])
        tie_break = cast(list[object], row.rules["tieBreak"])
        metrics = tuple(
            MetricWeight(
                str(item["metric"]),
                MetricDirection(str(item["direction"])),
                Decimal(str(item["lowerBound"])),
                Decimal(str(item["upperBound"])),
                Decimal(str(item["weight"])),
                bool(item.get("required", True)),
            )
            for item in metric_rules
        )
        return ScoringPolicy(
            row.id,
            row.policy_id,
            row.version,
            row.name,
            metrics,
            tuple(str(value) for value in tie_break),
            row.default_rank_metric,
        )

    async def save(self, result: EvaluationResult) -> EvaluationResult:
        async with self._sessions() as session, session.begin():
            await session.execute(
                insert(EvaluationResultRow)
                .values(_values(result))
                .on_conflict_do_nothing(constraint="uq_evaluation_results_source_policies")
            )
            row = await session.scalar(
                select(EvaluationResultRow).where(
                    EvaluationResultRow.backtest_result_id == result.backtest_result.id,
                    EvaluationResultRow.evaluation_policy_id == result.evaluation_policy_id,
                    EvaluationResultRow.evaluation_policy_version
                    == result.evaluation_policy_version,
                    EvaluationResultRow.scoring_policy_id == result.scoring_policy_id,
                    EvaluationResultRow.scoring_policy_version == result.scoring_policy_version,
                )
            )
        if row is None:
            raise RuntimeError("evaluation result could not be resolved")
        if row.content_fingerprint != result.content_fingerprint:
            raise ValueError("evaluation source/policies conflict with immutable content")
        return result if row.id == result.id else await self._domain(row)

    async def get(self, result_id: UUID) -> EvaluationResult | None:
        async with self._sessions() as session:
            row = await session.get(EvaluationResultRow, result_id)
        return None if row is None else await self._domain(row)

    async def get_many(self, result_ids: tuple[UUID, ...]) -> tuple[EvaluationResult, ...]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(EvaluationResultRow).where(EvaluationResultRow.id.in_(result_ids))
                )
            ).all()
        by_id = {row.id: row for row in rows}
        values = []
        for result_id in result_ids:
            row = by_id.get(result_id)
            if row is not None:
                values.append(await self._domain(row))
        return tuple(values)

    async def _domain(self, row: EvaluationResultRow) -> EvaluationResult:
        backtest = await self._backtests.get_result(row.backtest_result_id)
        if backtest is None:
            raise RuntimeError("evaluation backtest provenance is missing")
        metrics = EvaluationMetrics(
            Decimal(row.total_return),
            Decimal(row.win_rate),
            Decimal(row.max_drawdown),
            row.number_of_trades,
            None if row.profit_factor is None else Decimal(row.profit_factor),
            None if row.sharpe_ratio is None else Decimal(row.sharpe_ratio),
        )
        return EvaluationResult(
            row.id,
            backtest,
            row.evaluation_policy_id,
            row.evaluation_policy_version,
            row.scoring_policy_id,
            row.scoring_policy_version,
            metrics,
            Decimal(row.score),
            row.eligible,
            tuple(row.exclusion_reasons),
            row.content_fingerprint,
            row.evaluated_at,
        )


def _values(result: EvaluationResult) -> dict[str, object]:
    backtest, c, m = result.backtest_result, result.backtest_result.configuration, result.metrics
    return {
        "id": result.id,
        "backtest_result_id": backtest.id,
        "job_id": c.job_id,
        "run_id": c.run_id,
        "strategy_definition_id": c.strategy_definition_id,
        "strategy_id": c.strategy_id,
        "strategy_version": c.strategy_version,
        "dataset_id": c.dataset_id,
        "dataset_checksum": c.dataset_checksum,
        "pair": c.pair,
        "timeframe": c.timeframe.value,
        "start_time": c.start_time,
        "end_time": c.end_time,
        "execution_policy_id": c.execution_policy_id,
        "execution_policy_version": c.execution_policy_version,
        "execution_config_fingerprint": c.execution_config_fingerprint,
        "execution_config": c.execution_config,
        "evaluation_policy_id": result.evaluation_policy_id,
        "evaluation_policy_version": result.evaluation_policy_version,
        "scoring_policy_id": result.scoring_policy_id,
        "scoring_policy_version": result.scoring_policy_version,
        "total_return": m.total_return,
        "win_rate": m.win_rate,
        "max_drawdown": m.max_drawdown,
        "number_of_trades": m.number_of_trades,
        "profit_factor": m.profit_factor,
        "sharpe_ratio": m.sharpe_ratio,
        "score": result.score,
        "eligible": result.eligible,
        "exclusion_reasons": list(result.exclusion_reasons),
        "content_fingerprint": result.content_fingerprint,
        "evaluated_at": result.evaluated_at,
    }
