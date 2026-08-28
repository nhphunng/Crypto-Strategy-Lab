from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from crypto_lab.application.evaluations.ports import EvaluationRepository
from crypto_lab.domain.evaluation.comparison import (
    ComparisonMode,
    EvaluationComparison,
    compare_evaluations,
)


@dataclass(frozen=True, slots=True)
class CompareEvaluationResults:
    repository: EvaluationRepository

    async def execute(
        self, result_ids: tuple[UUID, ...], mode: ComparisonMode = ComparisonMode.CONTEXTUAL
    ) -> EvaluationComparison:
        if not 2 <= len(result_ids) <= 20 or len(set(result_ids)) != len(result_ids):
            raise ValueError("provide 2 to 20 distinct evaluation result IDs")
        results = await self.repository.get_many(result_ids)
        if len(results) != len(result_ids):
            raise ValueError("one or more evaluation results are unavailable")
        return compare_evaluations(results, mode)
