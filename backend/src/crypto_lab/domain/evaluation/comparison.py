from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from crypto_lab.domain.evaluation.result import EvaluationResult


class ComparisonMode(StrEnum):
    STRICT = "STRICT"
    CONTEXTUAL = "CONTEXTUAL"


@dataclass(frozen=True, slots=True)
class ContextDifference:
    dimension: str
    values: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvaluationComparison:
    compatible: bool
    differences: tuple[ContextDifference, ...]
    results: tuple[EvaluationResult, ...]


class IncompatibleComparisonError(ValueError):
    def __init__(self, differences: tuple[ContextDifference, ...]) -> None:
        super().__init__("evaluation contexts are incompatible")
        self.differences = differences


def compare_evaluations(
    results: tuple[EvaluationResult, ...], mode: ComparisonMode = ComparisonMode.CONTEXTUAL
) -> EvaluationComparison:
    if not 2 <= len(results) <= 20:
        raise ValueError("comparison requires between 2 and 20 results")
    contexts = [result.comparison_context for result in results]
    dimensions = (
        "dataset_id",
        "dataset_checksum",
        "pair",
        "timeframe",
        "start_time",
        "end_time",
        "execution_config_fingerprint",
        "evaluation_policy_version",
        "scoring_policy_version",
    )
    differences = tuple(
        ContextDifference(
            dimension, tuple(sorted({str(getattr(context, dimension)) for context in contexts}))
        )
        for dimension in dimensions
        if len({getattr(context, dimension) for context in contexts}) > 1
    )
    if differences and mode is ComparisonMode.STRICT:
        raise IncompatibleComparisonError(differences)
    ordered = tuple(
        sorted(
            results,
            key=lambda result: (
                -result.score,
                -result.metrics.total_return,
                result.metrics.max_drawdown,
                -result.metrics.win_rate,
                str(result.id),
            ),
        )
    )
    return EvaluationComparison(not differences, differences, ordered)
