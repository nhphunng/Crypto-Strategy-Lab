from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from crypto_lab.domain.backtest.configuration import canonical_hash
from crypto_lab.domain.market_data.candle import canonical_decimal


class MetricDirection(StrEnum):
    HIGHER = "HIGHER"
    LOWER = "LOWER"


@dataclass(frozen=True, slots=True)
class EvaluationPolicy:
    id: UUID
    policy_id: str
    version: str
    return_observation: str = "PER_CANDLE_EQUITY"
    risk_free_rate: Decimal = Decimal(0)
    sample_standard_deviation: bool = True

    @property
    def rules(self) -> dict[str, object]:
        return {
            "metrics": [
                "totalReturn",
                "winRate",
                "maxDrawdown",
                "numberOfTrades",
                "profitFactor",
                "sharpeRatio",
            ],
            "precision": 18,
            "returnObservation": self.return_observation,
            "riskFreeRate": canonical_decimal(self.risk_free_rate),
            "sampleStandardDeviation": self.sample_standard_deviation,
        }

    @property
    def fingerprint(self) -> str:
        return canonical_hash(
            {"policyId": self.policy_id, "rules": self.rules, "version": self.version}
        )


@dataclass(frozen=True, slots=True)
class MetricWeight:
    metric: str
    direction: MetricDirection
    lower_bound: Decimal
    upper_bound: Decimal
    weight: Decimal
    required: bool = True

    def __post_init__(self) -> None:
        if self.lower_bound >= self.upper_bound or self.weight < 0:
            raise ValueError("metric bound or weight is invalid")


@dataclass(frozen=True, slots=True)
class ScoringPolicy:
    id: UUID
    policy_id: str
    version: str
    name: str
    metrics: tuple[MetricWeight, ...]
    tie_break: tuple[str, ...]
    default_rank_metric: str = "score"

    def __post_init__(self) -> None:
        if sum((item.weight for item in self.metrics), Decimal(0)) != Decimal(1):
            raise ValueError("scoring weights must total 1")
        if not self.metrics or not self.tie_break:
            raise ValueError("scoring policy must be total")

    @property
    def rules(self) -> dict[str, object]:
        return {
            "metrics": [
                {
                    "direction": item.direction.value,
                    "lowerBound": canonical_decimal(item.lower_bound),
                    "metric": item.metric,
                    "required": item.required,
                    "upperBound": canonical_decimal(item.upper_bound),
                    "weight": canonical_decimal(item.weight),
                }
                for item in self.metrics
            ],
            "tieBreak": list(self.tie_break),
            "undefinedBehavior": "INELIGIBLE_SCORE_ZERO",
        }

    @property
    def fingerprint(self) -> str:
        return canonical_hash(
            {"policyId": self.policy_id, "rules": self.rules, "version": self.version}
        )
