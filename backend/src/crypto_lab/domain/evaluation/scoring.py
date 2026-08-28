from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from crypto_lab.domain.backtest.configuration import published_decimal
from crypto_lab.domain.evaluation.metrics import EvaluationMetrics
from crypto_lab.domain.evaluation.policy import MetricDirection, ScoringPolicy


@dataclass(frozen=True, slots=True)
class ScoreOutcome:
    score: Decimal
    eligible: bool
    exclusion_reasons: tuple[str, ...]


def score_metrics(metrics: EvaluationMetrics, policy: ScoringPolicy) -> ScoreOutcome:
    values = metrics.values()
    reasons = tuple(
        f"REQUIRED_METRIC_UNDEFINED:{descriptor.metric}"
        for descriptor in policy.metrics
        if descriptor.required and values.get(descriptor.metric) is None
    )
    if reasons:
        return ScoreOutcome(Decimal(0), False, reasons)
    weighted = Decimal(0)
    for descriptor in policy.metrics:
        value = values.get(descriptor.metric)
        if value is None:
            continue
        decimal_value = Decimal(value)
        clamped = min(descriptor.upper_bound, max(descriptor.lower_bound, decimal_value))
        normalized = (clamped - descriptor.lower_bound) / (
            descriptor.upper_bound - descriptor.lower_bound
        )
        if descriptor.direction is MetricDirection.LOWER:
            normalized = Decimal(1) - normalized
        weighted += normalized * descriptor.weight
    return ScoreOutcome(published_decimal(weighted * Decimal(100)), True, ())


def tie_break_key(metrics: EvaluationMetrics, evaluation_id: str) -> tuple[object, ...]:
    return (-metrics.total_return, metrics.max_drawdown, -metrics.win_rate, evaluation_id)
