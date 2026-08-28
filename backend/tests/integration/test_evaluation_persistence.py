from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from crypto_lab.api.dependencies import BALANCED_SCORING_POLICY, EVALUATION_POLICY
from crypto_lab.api.schemas.backtest_evaluation import evaluation_to_dto
from crypto_lab.application.evaluations.evaluate_result import EvaluateBacktestResult
from crypto_lab.infrastructure.persistence.evaluation_models import EvaluationResultRow
from crypto_lab.infrastructure.persistence.repositories.evaluation_repository import (
    SqlAlchemyEvaluationRepository,
)
from tests.fixtures.backtest_evaluation.cross_feature import NOW
from tests.fixtures.backtest_evaluation.persistence import BacktestPersistenceContext

pytestmark = pytest.mark.integration


class _Clock:
    def now(self):
        return NOW


async def _evaluate(context: BacktestPersistenceContext):
    repository = SqlAlchemyEvaluationRepository(
        context.database.sessions, context.repository
    )
    await repository.ensure_policies(
        EVALUATION_POLICY, BALANCED_SCORING_POLICY, NOW
    )
    use_case = EvaluateBacktestResult(
        context.repository, repository, repository, _Clock()
    )
    result = await use_case.execute(
        context.result.id,
        EVALUATION_POLICY.id,
        EVALUATION_POLICY.version,
        BALANCED_SCORING_POLICY.id,
        BALANCED_SCORING_POLICY.version,
    )
    return repository, use_case, result


async def test_policy_identity_and_evaluation_are_persisted_idempotently(
    persisted_backtest: BacktestPersistenceContext,
) -> None:
    repository, use_case, first = await _evaluate(persisted_backtest)
    second = await use_case.execute(
        persisted_backtest.result.id,
        EVALUATION_POLICY.id,
        EVALUATION_POLICY.version,
        BALANCED_SCORING_POLICY.id,
        BALANCED_SCORING_POLICY.version,
    )
    async with persisted_backtest.database.sessions() as session:
        count = await session.scalar(select(func.count()).select_from(EvaluationResultRow))

    assert first.id == second.id
    assert first.content_fingerprint == second.content_fingerprint
    assert count == 1
    assert await repository.get_evaluation(
        EVALUATION_POLICY.id, EVALUATION_POLICY.version
    ) == EVALUATION_POLICY
    assert await repository.get_scoring(
        BALANCED_SCORING_POLICY.id, BALANCED_SCORING_POLICY.version
    ) == BALANCED_SCORING_POLICY


async def test_historical_metrics_are_immutable_and_api_safe(
    persisted_backtest: BacktestPersistenceContext,
) -> None:
    repository, _use_case, result = await _evaluate(persisted_backtest)
    loaded = await repository.get(result.id)
    assert loaded is not None
    assert loaded.metrics == result.metrics
    with pytest.raises(FrozenInstanceError):
        loaded.metrics.total_return = Decimal("999")  # type: ignore[misc]

    payload = evaluation_to_dto(loaded).model_dump(by_alias=True, mode="json")
    encoded = str(payload).lower()
    assert "nan" not in encoded
    assert "infinity" not in encoded
    assert payload["evaluationPolicyId"] == str(EVALUATION_POLICY.id)
    assert payload["scoringPolicyId"] == str(BALANCED_SCORING_POLICY.id)
    assert payload["analysisType"] == "HISTORICAL_SIMULATION"
