from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import func, select

from crypto_lab.api.dependencies import BALANCED_SCORING_POLICY, EVALUATION_POLICY
from crypto_lab.application.evaluations.evaluate_result import EvaluateBacktestResult
from crypto_lab.domain.evaluation.policy import ScoringPolicy
from crypto_lab.infrastructure.persistence.evaluation_models import (
    EvaluationResultRow,
    ScoringPolicyRow,
)
from crypto_lab.infrastructure.persistence.repositories.evaluation_repository import (
    SqlAlchemyEvaluationRepository,
)
from tests.fixtures.backtest_evaluation.cross_feature import NOW
from tests.fixtures.backtest_evaluation.persistence import BacktestPersistenceContext

pytestmark = pytest.mark.integration


class _Clock:
    def now(self):
        return NOW


def _version_two() -> ScoringPolicy:
    return replace(
        BALANCED_SCORING_POLICY,
        id=UUID(int=804),
        version="2.0.0",
        name="Balanced v2",
    )


async def test_new_policy_version_creates_new_evaluation_without_overwrite(
    persisted_backtest: BacktestPersistenceContext,
) -> None:
    context = persisted_backtest
    repository = SqlAlchemyEvaluationRepository(
        context.database.sessions, context.repository
    )
    version_two = _version_two()
    await repository.ensure_policies(EVALUATION_POLICY, BALANCED_SCORING_POLICY, NOW)
    await repository.ensure_policies(EVALUATION_POLICY, version_two, NOW)
    evaluator = EvaluateBacktestResult(
        context.repository, repository, repository, _Clock()
    )
    first = await evaluator.execute(
        context.result.id,
        EVALUATION_POLICY.id,
        EVALUATION_POLICY.version,
        BALANCED_SCORING_POLICY.id,
        BALANCED_SCORING_POLICY.version,
    )
    second = await evaluator.execute(
        context.result.id,
        EVALUATION_POLICY.id,
        EVALUATION_POLICY.version,
        version_two.id,
        version_two.version,
    )
    reloaded_first = await repository.get(first.id)
    async with context.database.sessions() as session:
        evaluation_count = await session.scalar(
            select(func.count()).select_from(EvaluationResultRow)
        )
        policy_count = await session.scalar(
            select(func.count()).select_from(ScoringPolicyRow)
        )

    assert first.id != second.id
    assert first.scoring_policy_version == "1.0.0"
    assert second.scoring_policy_version == "2.0.0"
    assert reloaded_first == first
    assert evaluation_count == 2
    assert policy_count == 2


async def test_existing_policy_identity_rejects_changed_rules(
    persisted_backtest: BacktestPersistenceContext,
) -> None:
    context = persisted_backtest
    repository = SqlAlchemyEvaluationRepository(
        context.database.sessions, context.repository
    )
    await repository.ensure_policies(EVALUATION_POLICY, BALANCED_SCORING_POLICY, NOW)
    metrics = BALANCED_SCORING_POLICY.metrics
    conflicting = replace(
        BALANCED_SCORING_POLICY,
        id=UUID(int=805),
        metrics=(
            replace(metrics[0], weight=Decimal("0.25")),
            replace(metrics[1], weight=Decimal("0.35")),
            *metrics[2:],
        ),
    )

    with pytest.raises(ValueError, match="immutable rules"):
        await repository.ensure_policies(EVALUATION_POLICY, conflicting, NOW)

    loaded = await repository.get_scoring(
        BALANCED_SCORING_POLICY.id, BALANCED_SCORING_POLICY.version
    )
    assert loaded == BALANCED_SCORING_POLICY
