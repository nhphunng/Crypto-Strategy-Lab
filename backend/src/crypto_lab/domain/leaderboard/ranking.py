"""Total deterministic ranking comparator and bounded Top-K transition."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from crypto_lab.domain.leaderboard.entry import (
    LeaderboardEntry,
    ProjectionChange,
    RankableCandidate,
    assert_projection_invariants,
)
from crypto_lab.domain.leaderboard.policy import (
    ExclusionReason,
    MetricName,
    ProjectionVersion,
    RankMetric,
    ScoringPolicy,
    SortDirection,
)
from crypto_lab.domain.market_data.candle import canonical_decimal, format_utc_millis


@dataclass(frozen=True, slots=True)
class ExcludedCandidate:
    evaluation_result_id: UUID
    reason: ExclusionReason


@dataclass(frozen=True, slots=True)
class RankingOutcome:
    """Bounded ordering plus the visible reason for every excluded input."""

    entries: tuple[LeaderboardEntry, ...]
    excluded: tuple[ExcludedCandidate, ...]

    @property
    def ranked_ids(self) -> tuple[UUID, ...]:
        return tuple(entry.evaluation_result_id for entry in self.entries)


def _ordering_components(
    policy: ScoringPolicy,
    rank_metric: RankMetric,
) -> tuple[MetricName, ...]:
    """Ranking metric first, then the policy's ordered tie-break key."""

    primary = MetricName(rank_metric.value)
    components = [primary]
    for metric in policy.tie_breakers:
        if metric not in components:
            components.append(metric)
    return tuple(components)


def _directional(value: Decimal, direction: SortDirection) -> Decimal:
    return value if direction is SortDirection.ASC else -value


def _sort_tuple(
    candidate: RankableCandidate,
    policy: ScoringPolicy,
    components: Sequence[MetricName],
) -> tuple[object, ...]:
    values: list[object] = []
    for metric in components:
        raw = candidate.metrics.value_of(metric)
        direction = policy.direction_for(metric)
        # A missing optional metric always sorts last, never silently superior.
        values.append(0 if raw is not None else 1)
        values.append(_directional(raw if raw is not None else Decimal(0), direction))
    values.append(candidate.evaluated_at)
    values.append(str(candidate.evaluation_result_id))
    return tuple(values)


def build_sort_key(
    candidate: RankableCandidate,
    policy: ScoringPolicy,
    rank_metric: RankMetric,
) -> tuple[str, ...]:
    """Human-auditable record of the exact comparison key used for this row."""

    parts: list[str] = []
    for metric in _ordering_components(policy, rank_metric):
        raw = candidate.metrics.value_of(metric)
        direction = policy.direction_for(metric)
        rendered = canonical_decimal(raw) if raw is not None else "null"
        parts.append(f"{metric.value}:{direction.value}:{rendered}")
    parts.append(f"EVALUATED_AT:ASC:{format_utc_millis(candidate.evaluated_at)}")
    parts.append(f"EVALUATION_RESULT_ID:ASC:{candidate.evaluation_result_id}")
    return tuple(parts)


def rank_candidates(
    candidates: Iterable[RankableCandidate],
    *,
    policy: ScoringPolicy,
    rank_metric: RankMetric,
    k: int,
    projection_version: ProjectionVersion,
) -> RankingOutcome:
    """Order eligible candidates deterministically and keep at most K of them."""

    eligible: list[RankableCandidate] = []
    excluded: list[ExcludedCandidate] = []
    for candidate in candidates:
        decision = candidate.eligibility(policy, rank_metric)
        if decision.eligible:
            eligible.append(candidate)
        elif decision.reason is not None:
            excluded.append(ExcludedCandidate(candidate.evaluation_result_id, decision.reason))

    components = _ordering_components(policy, rank_metric)
    ordered = sorted(eligible, key=lambda item: _sort_tuple(item, policy, components))
    entries = tuple(
        LeaderboardEntry(
            evaluation_result_id=candidate.evaluation_result_id,
            rank=index + 1,
            projection_version=projection_version,
            sort_key=build_sort_key(candidate, policy, rank_metric),
        )
        for index, candidate in enumerate(ordered[:k])
    )
    assert_projection_invariants(entries, k)
    return RankingOutcome(entries=entries, excluded=tuple(excluded))


def diff_projection(
    current: Sequence[LeaderboardEntry],
    proposed: Sequence[LeaderboardEntry],
) -> ProjectionChange:
    """Compare two orderings and return the compact changed set."""

    current_ranks = {entry.evaluation_result_id: entry.rank for entry in current}
    proposed_ranks = {entry.evaluation_result_id: entry.rank for entry in proposed}
    added = tuple(
        entry.evaluation_result_id
        for entry in proposed
        if entry.evaluation_result_id not in current_ranks
    )
    removed = tuple(
        entry.evaluation_result_id
        for entry in current
        if entry.evaluation_result_id not in proposed_ranks
    )
    moved = tuple(
        entry.evaluation_result_id
        for entry in proposed
        if entry.evaluation_result_id in current_ranks
        and current_ranks[entry.evaluation_result_id] != entry.rank
    )
    return ProjectionChange(added=added, removed=removed, moved=moved)
