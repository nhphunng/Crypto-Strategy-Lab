"""Framework-independent leaderboard entries and projection invariants."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from crypto_lab.domain.leaderboard.policy import (
    EligibilityDecision,
    ExclusionReason,
    MetricName,
    ProjectionVersion,
    RankMetric,
    ScoringPolicy,
    ScoringPolicyRef,
    require_finite,
)
from crypto_lab.domain.market_data.timeframe import Timeframe, require_utc


@dataclass(frozen=True, slots=True)
class MetricSet:
    """Immutable metric values copied from one Evaluation Result."""

    total_return: Decimal
    win_rate: Decimal
    max_drawdown: Decimal
    number_of_trades: int
    sharpe_ratio: Decimal | None = None
    score: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        require_finite(self.total_return, field_name="totalReturn")
        require_finite(self.win_rate, field_name="winRate")
        require_finite(self.max_drawdown, field_name="maxDrawdown")
        require_finite(self.sharpe_ratio, field_name="sharpeRatio")
        require_finite(self.score, field_name="score")
        if self.number_of_trades < 0:
            raise ValueError("numberOfTrades must be non-negative")

    def value_of(self, metric: MetricName) -> Decimal | None:
        if metric is MetricName.OVERALL_SCORE:
            return self.score
        if metric is MetricName.TOTAL_RETURN:
            return self.total_return
        if metric is MetricName.WIN_RATE:
            return self.win_rate
        if metric is MetricName.MAX_DRAWDOWN:
            return self.max_drawdown
        if metric is MetricName.NUMBER_OF_TRADES:
            return Decimal(self.number_of_trades)
        return self.sharpe_ratio


@dataclass(frozen=True, slots=True)
class StrategyMember:
    strategy_id: str
    strategy_version: str
    display_name: str


@dataclass(frozen=True, slots=True)
class StrategySummary:
    """Immutable strategy identity referenced by a ranked result."""

    strategy_id: str
    strategy_version: str
    display_name: str
    members: tuple[StrategyMember, ...] = ()


@dataclass(frozen=True, slots=True)
class RankableCandidate:
    """One immutable Evaluation Result presented to the ranking comparator."""

    evaluation_result_id: UUID
    run_id: UUID
    job_id: UUID
    backtest_result_id: UUID
    dataset_id: UUID
    pair: str
    timeframe: Timeframe
    start_time: datetime
    end_time: datetime
    strategy: StrategySummary
    metrics: MetricSet
    policy: ScoringPolicyRef
    evaluated_at: datetime
    upstream_eligible: bool = True
    upstream_exclusion_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_utc(self.start_time)
        require_utc(self.end_time)
        require_utc(self.evaluated_at)

    def eligibility(self, policy: ScoringPolicy, rank_metric: RankMetric) -> EligibilityDecision:
        """Apply documented policy eligibility before the candidate can be ranked."""

        if self.policy != policy.ref:
            return EligibilityDecision.deny(ExclusionReason.POLICY_VERSION_MISMATCH)
        if not self.upstream_eligible:
            return EligibilityDecision.deny(ExclusionReason.UPSTREAM_INELIGIBLE)
        if policy.exclude_no_trade and self.metrics.number_of_trades == 0:
            return EligibilityDecision.deny(ExclusionReason.NO_TRADES)
        value = self.metrics.value_of(MetricName(rank_metric.value))
        if value is None:
            return EligibilityDecision.deny(ExclusionReason.METRIC_UNAVAILABLE)
        if not value.is_finite():
            return EligibilityDecision.deny(ExclusionReason.METRIC_NOT_FINITE)
        return EligibilityDecision.allow()


@dataclass(frozen=True, slots=True)
class LeaderboardEntry:
    """A Top-K projection item bound to one immutable Evaluation Result."""

    evaluation_result_id: UUID
    rank: int
    projection_version: ProjectionVersion
    sort_key: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.rank < 1:
            raise ValueError("rank must be positive")


@dataclass(frozen=True, slots=True)
class ProjectionChange:
    """Compact changed set describing one visible projection transition."""

    added: tuple[UUID, ...] = ()
    removed: tuple[UUID, ...] = ()
    moved: tuple[UUID, ...] = ()

    @property
    def changed(self) -> bool:
        return bool(self.added or self.removed or self.moved)


def assert_projection_invariants(entries: tuple[LeaderboardEntry, ...], k: int) -> None:
    """Entry count never exceeds K, ranks are contiguous, evaluations are unique."""

    if len(entries) > k:
        raise ValueError("projection cannot hold more than k entries")
    ranks = [entry.rank for entry in entries]
    if ranks != list(range(1, len(entries) + 1)):
        raise ValueError("ranks must be contiguous and start at 1")
    identities = {entry.evaluation_result_id for entry in entries}
    if len(identities) != len(entries):
        raise ValueError("an evaluation result may appear at most once per projection")
