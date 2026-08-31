from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from crypto_lab.application.evaluations.ports import (
    BacktestReader,
    Clock,
    EvaluationRepository,
    PolicyReader,
)
from crypto_lab.domain.evaluation.metrics import calculate_metrics
from crypto_lab.domain.evaluation.result import EvaluationResult, create_evaluation_result
from crypto_lab.domain.evaluation.scoring import score_metrics

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EvaluateBacktestResult:
    backtests: BacktestReader
    evaluations: EvaluationRepository
    policies: PolicyReader
    clock: Clock

    async def execute(
        self,
        backtest_result_id: UUID,
        evaluation_policy_id: UUID,
        evaluation_policy_version: str,
        scoring_policy_id: UUID,
        scoring_policy_version: str,
    ) -> EvaluationResult:
        backtest = await self.backtests.get_result(backtest_result_id)
        if backtest is None:
            raise ValueError("backtest result is unavailable")
        evaluation_policy = await self.policies.get_evaluation(
            evaluation_policy_id, evaluation_policy_version
        )
        scoring_policy = await self.policies.get_scoring(scoring_policy_id, scoring_policy_version)
        if evaluation_policy is None or scoring_policy is None:
            raise ValueError("exact evaluation/scoring policy is unavailable")
        metrics = calculate_metrics(backtest)
        outcome = score_metrics(metrics, scoring_policy)
        result = create_evaluation_result(
            backtest, evaluation_policy, scoring_policy, metrics, outcome, self.clock.now()
        )
        persisted = await self.evaluations.save(result)
        logger.info(
            "evaluation_completed",
            extra={
                "backtest_result_id": str(backtest_result_id),
                "evaluation_result_id": str(persisted.id),
                "result_checksum": persisted.content_fingerprint,
            },
        )
        return persisted
