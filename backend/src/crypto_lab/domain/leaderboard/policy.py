"""Versioned ranking policy value objects for the leaderboard projection.

The leaderboard consumes immutable Evaluation Results and their versioned
Scoring Policy. It never recomputes a financial metric or a score.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from crypto_lab.domain.market_data.timeframe import Timeframe, require_utc

MIN_K = 1
MAX_K = 200
DEFAULT_K = 10


class RankMetric(StrEnum):
    """Metric that may determine Top-K membership and authoritative rank."""

    OVERALL_SCORE = "OVERALL_SCORE"
    TOTAL_RETURN = "TOTAL_RETURN"
    WIN_RATE = "WIN_RATE"
    MAX_DRAWDOWN = "MAX_DRAWDOWN"
    SHARPE_RATIO = "SHARPE_RATIO"


class MetricName(StrEnum):
    """Every metric the leaderboard exposes, including non-rankable ones."""

    OVERALL_SCORE = "OVERALL_SCORE"
    TOTAL_RETURN = "TOTAL_RETURN"
    WIN_RATE = "WIN_RATE"
    MAX_DRAWDOWN = "MAX_DRAWDOWN"
    NUMBER_OF_TRADES = "NUMBER_OF_TRADES"
    SHARPE_RATIO = "SHARPE_RATIO"


class SortDirection(StrEnum):
    ASC = "ASC"
    DESC = "DESC"


class MetricUnit(StrEnum):
    PERCENT = "PERCENT"
    RATIO = "RATIO"
    COUNT = "COUNT"
    SCORE = "SCORE"


class ExclusionReason(StrEnum):
    """Documented, visible reason an eligible-looking candidate is not ranked."""

    UPSTREAM_INELIGIBLE = "UPSTREAM_INELIGIBLE"
    METRIC_UNAVAILABLE = "METRIC_UNAVAILABLE"
    METRIC_NOT_FINITE = "METRIC_NOT_FINITE"
    NO_TRADES = "NO_TRADES"
    POLICY_VERSION_MISMATCH = "POLICY_VERSION_MISMATCH"


_SEMANTIC_DIRECTIONS: dict[MetricName, SortDirection] = {
    MetricName.OVERALL_SCORE: SortDirection.DESC,
    MetricName.TOTAL_RETURN: SortDirection.DESC,
    MetricName.WIN_RATE: SortDirection.DESC,
    # Maximum Drawdown is recorded as a non-negative severity magnitude, so a
    # smaller value is better.
    MetricName.MAX_DRAWDOWN: SortDirection.ASC,
    MetricName.NUMBER_OF_TRADES: SortDirection.DESC,
    MetricName.SHARPE_RATIO: SortDirection.DESC,
}

_UNITS: dict[MetricName, MetricUnit] = {
    MetricName.OVERALL_SCORE: MetricUnit.SCORE,
    MetricName.TOTAL_RETURN: MetricUnit.PERCENT,
    MetricName.WIN_RATE: MetricUnit.PERCENT,
    MetricName.MAX_DRAWDOWN: MetricUnit.PERCENT,
    MetricName.NUMBER_OF_TRADES: MetricUnit.COUNT,
    MetricName.SHARPE_RATIO: MetricUnit.RATIO,
}

DEFAULT_TIE_BREAKERS: tuple[MetricName, ...] = (
    MetricName.OVERALL_SCORE,
    MetricName.TOTAL_RETURN,
    MetricName.MAX_DRAWDOWN,
    MetricName.NUMBER_OF_TRADES,
)


def require_finite(value: Decimal | None, *, field_name: str) -> Decimal | None:
    """Reject NaN/infinite input before it can corrupt an ordering."""

    if value is None:
        return None
    if isinstance(value, float):  # pragma: no cover - defensive typing guard
        raise TypeError(f"{field_name} must not be a float")
    if not value.is_finite():
        raise ValueError(f"{field_name} must be finite")
    return value


@dataclass(frozen=True, slots=True)
class MetricDescriptor:
    """Direction and unit metadata returned with every snapshot."""

    metric: MetricName
    direction: SortDirection
    unit: MetricUnit


@dataclass(frozen=True, slots=True)
class ScoringPolicyRef:
    """Immutable logical identity of the policy that produced a score."""

    policy_id: str
    version: str

    def __post_init__(self) -> None:
        if not self.policy_id or len(self.policy_id) > 100:
            raise ValueError("scoring policy id must be 1..100 characters")
        if not self.version or len(self.version) > 50:
            raise ValueError("scoring policy version must be 1..50 characters")


@dataclass(frozen=True, slots=True)
class ProjectionVersion:
    """Monotonically increasing version of one leaderboard projection."""

    value: int

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError("projection version must be non-negative")

    def next(self) -> ProjectionVersion:
        return ProjectionVersion(self.value + 1)

    def is_newer_than(self, other: ProjectionVersion) -> bool:
        return self.value > other.value


@dataclass(frozen=True, slots=True)
class LeaderboardScope:
    """Canonical comparison scope; presentation state is deliberately absent."""

    pair: str | None = None
    timeframe: Timeframe | None = None
    run_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.pair is not None and self.pair != self.pair.upper():
            raise ValueError("pair must be uppercase")

    @property
    def scope_key(self) -> str:
        pair = self.pair or "*"
        timeframe = self.timeframe.value if self.timeframe else "*"
        run = str(self.run_id) if self.run_id else "*"
        return f"pair:{pair}|timeframe:{timeframe}|run:{run}"

    def matches(self, *, pair: str, timeframe: str, run_id: UUID) -> bool:
        if self.pair is not None and self.pair != pair:
            return False
        if self.timeframe is not None and self.timeframe.value != timeframe:
            return False
        return not (self.run_id is not None and self.run_id != run_id)


@dataclass(frozen=True, slots=True)
class LeaderboardIdentity:
    """Complete projection identity: a different K or metric is another projection."""

    scope: LeaderboardScope
    policy: ScoringPolicyRef
    rank_metric: RankMetric
    k: int

    def __post_init__(self) -> None:
        if not MIN_K <= self.k <= MAX_K:
            raise ValueError(f"k must be between {MIN_K} and {MAX_K}")

    @property
    def scope_key(self) -> str:
        return self.scope.scope_key


@dataclass(frozen=True, slots=True)
class EligibilityDecision:
    eligible: bool
    reason: ExclusionReason | None = None

    @classmethod
    def allow(cls) -> EligibilityDecision:
        return cls(True, None)

    @classmethod
    def deny(cls, reason: ExclusionReason) -> EligibilityDecision:
        return cls(False, reason)


@dataclass(frozen=True, slots=True)
class ScoringPolicy:
    """Versioned ranking semantics loaded from the immutable policy record."""

    ref: ScoringPolicyRef
    name: str
    default_rank_metric: RankMetric
    directions: dict[MetricName, SortDirection] = field(default_factory=dict)
    tie_breakers: tuple[MetricName, ...] = DEFAULT_TIE_BREAKERS
    exclude_no_trade: bool = False

    @classmethod
    def from_rules(
        cls,
        ref: ScoringPolicyRef,
        *,
        name: str,
        default_rank_metric: str,
        rules: dict[str, Any] | None = None,
    ) -> ScoringPolicy:
        """Build policy semantics, falling back to the documented defaults."""

        rules = rules or {}
        directions = dict(_SEMANTIC_DIRECTIONS)
        for raw_metric, raw_direction in (rules.get("metricDirections") or {}).items():
            try:
                metric = MetricName(str(raw_metric).upper())
                directions[metric] = SortDirection(str(raw_direction).upper())
            except ValueError:
                continue
        tie_breakers: list[MetricName] = []
        for raw_metric in rules.get("tieBreakers") or ():
            try:
                tie_breakers.append(MetricName(str(raw_metric).upper()))
            except ValueError:
                continue
        eligibility = rules.get("eligibilityRules") or {}
        try:
            default_metric = RankMetric(str(default_rank_metric).upper())
        except ValueError:
            default_metric = RankMetric.OVERALL_SCORE
        return cls(
            ref=ref,
            name=name,
            default_rank_metric=default_metric,
            directions=directions,
            tie_breakers=tuple(tie_breakers) or DEFAULT_TIE_BREAKERS,
            exclude_no_trade=bool(eligibility.get("excludeNoTrade", False)),
        )

    def direction_for(self, metric: MetricName) -> SortDirection:
        return self.directions.get(metric, _SEMANTIC_DIRECTIONS[metric])

    def unit_for(self, metric: MetricName) -> MetricUnit:
        return _UNITS[metric]

    def metric_metadata(self) -> tuple[MetricDescriptor, ...]:
        return tuple(
            MetricDescriptor(metric, self.direction_for(metric), self.unit_for(metric))
            for metric in MetricName
        )


def parse_rank_metric(value: str) -> RankMetric:
    return RankMetric(value.upper())


def as_metric_name(metric: RankMetric) -> MetricName:
    return MetricName(metric.value)


def normalize_instant(value: datetime) -> datetime:
    return require_utc(value)
