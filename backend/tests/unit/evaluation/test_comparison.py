from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest
from tests.fixtures.backtest_evaluation.cross_feature import NOW
from tests.fixtures.backtest_evaluation.scenarios import profitable

from crypto_lab.domain.backtest.engine import execute_backtest
from crypto_lab.domain.evaluation.comparison import (
    ComparisonMode,
    IncompatibleComparisonError,
    compare_evaluations,
)
from crypto_lab.domain.evaluation.metrics import calculate_metrics
from crypto_lab.domain.evaluation.policy import (
    EvaluationPolicy,
    MetricDirection,
    MetricWeight,
    ScoringPolicy,
)
from crypto_lab.domain.evaluation.result import create_evaluation_result
from crypto_lab.domain.evaluation.scoring import score_metrics


def _evaluation():
    config, candles, analysis, execution = profitable()
    backtest = execute_backtest(config, candles, analysis, execution, created_at=NOW)
    evaluation = EvaluationPolicy(UUID(int=10), "standard", "1")
    scoring = ScoringPolicy(
        UUID(int=11),
        "return",
        "1",
        "Return",
        (
            MetricWeight(
                "totalReturn", MetricDirection.HIGHER, Decimal("-100"), Decimal("100"), Decimal(1)
            ),
        ),
        ("evaluationResultId:asc",),
    )
    metrics = calculate_metrics(backtest)
    return create_evaluation_result(
        backtest, evaluation, scoring, metrics, score_metrics(metrics, scoring), NOW
    )


def test_compatible_results_are_stably_ordered() -> None:
    first = _evaluation()
    second = replace(first, id=UUID(int=99), score=Decimal("10"))
    comparison = compare_evaluations((second, first))
    assert comparison.compatible
    assert comparison.results[0] is first


def test_all_differences_report_and_strict_rejects() -> None:
    first = _evaluation()
    second = replace(first, scoring_policy_version="2")
    contextual = compare_evaluations((first, second))
    assert [item.dimension for item in contextual.differences] == ["scoring_policy_version"]
    with pytest.raises(IncompatibleComparisonError):
        compare_evaluations((first, second), ComparisonMode.STRICT)
