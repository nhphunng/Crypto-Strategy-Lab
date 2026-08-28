from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from crypto_lab.domain.evaluation.metrics import EvaluationMetrics
from crypto_lab.domain.evaluation.policy import MetricDirection, MetricWeight, ScoringPolicy
from crypto_lab.domain.evaluation.scoring import score_metrics


def _policy() -> ScoringPolicy:
    return ScoringPolicy(
        UUID(int=1),
        "test",
        "1",
        "Test",
        (
            MetricWeight(
                "totalReturn",
                MetricDirection.HIGHER,
                Decimal("-100"),
                Decimal("100"),
                Decimal("0.5"),
            ),
            MetricWeight(
                "maxDrawdown", MetricDirection.LOWER, Decimal("0"), Decimal("100"), Decimal("0.5")
            ),
        ),
        ("evaluationResultId:asc",),
    )


def test_fixed_bound_direction_weight_and_clamping() -> None:
    outcome = score_metrics(
        EvaluationMetrics(Decimal("200"), Decimal(0), Decimal("25"), 0, None, None), _policy()
    )
    assert outcome.eligible
    assert outcome.score == Decimal("87.500000000000000000")


def test_required_null_is_ineligible_and_zero() -> None:
    policy = ScoringPolicy(
        UUID(int=2),
        "test-null",
        "1",
        "Test",
        (
            MetricWeight(
                "sharpeRatio", MetricDirection.HIGHER, Decimal("-3"), Decimal("3"), Decimal(1)
            ),
        ),
        ("evaluationResultId:asc",),
    )
    outcome = score_metrics(
        EvaluationMetrics(Decimal(0), Decimal(0), Decimal(0), 0, None, None), policy
    )
    assert not outcome.eligible
    assert outcome.score == 0
    assert outcome.exclusion_reasons == ("REQUIRED_METRIC_UNDEFINED:sharpeRatio",)
