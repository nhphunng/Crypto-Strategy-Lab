"""Authoritative snapshot, filter, presentation-sort, and page orchestration.

Presentation controls never change Top-K membership, stored metric values, or
the authoritative rank recorded in the projection.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from crypto_lab.application.leaderboard.errors import policy_not_published, query_invalid
from crypto_lab.application.leaderboard.ports import (
    EntryView,
    LeaderboardRepository,
    ProjectionSnapshot,
    RunState,
    ScoringPolicySummary,
)
from crypto_lab.application.leaderboard.update_leaderboard import UpdateLeaderboard
from crypto_lab.domain.leaderboard.policy import (
    MAX_K,
    MIN_K,
    LeaderboardIdentity,
    MetricDescriptor,
    MetricName,
    RankMetric,
    ScoringPolicyRef,
    SortDirection,
)

MAX_PAGE_SIZE = 200
DEFAULT_PAGE_SIZE = 25


@dataclass(frozen=True, slots=True)
class MetricFilters:
    """Bounded presentation filters over the already-selected Top-K."""

    min_score: Decimal | None = None
    min_total_return: Decimal | None = None
    min_win_rate: Decimal | None = None
    max_drawdown: Decimal | None = None
    min_sharpe_ratio: Decimal | None = None

    def keeps(self, entry: EntryView) -> bool:
        metrics = entry.candidate.metrics
        if self.min_score is not None and metrics.score < self.min_score:
            return False
        if self.min_total_return is not None and metrics.total_return < self.min_total_return:
            return False
        if self.min_win_rate is not None and metrics.win_rate < self.min_win_rate:
            return False
        if self.max_drawdown is not None and metrics.max_drawdown > self.max_drawdown:
            return False
        if self.min_sharpe_ratio is not None:
            if metrics.sharpe_ratio is None or metrics.sharpe_ratio < self.min_sharpe_ratio:
                return False
        return True


@dataclass(frozen=True, slots=True)
class LeaderboardQuery:
    identity: LeaderboardIdentity
    filters: MetricFilters = field(default_factory=MetricFilters)
    sort_by: str = "RANK"
    sort_direction: SortDirection | None = None
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE

    def __post_init__(self) -> None:
        if not MIN_K <= self.identity.k <= MAX_K:
            raise query_invalid("k must be between 1 and 200.", k=self.identity.k)
        if self.page < 1:
            raise query_invalid("page must be 1 or greater.", page=self.page)
        if not 1 <= self.page_size <= MAX_PAGE_SIZE:
            raise query_invalid(
                "pageSize must be between 1 and 200.",
                pageSize=self.page_size,
            )


@dataclass(frozen=True, slots=True)
class LeaderboardPage:
    leaderboard_id: UUID
    scope_key: str
    policy: ScoringPolicyRef
    rank_metric: RankMetric
    k: int
    projection_version: int
    updated_at: datetime
    metric_metadata: tuple[MetricDescriptor, ...]
    entries: tuple[EntryView, ...]
    page: int
    page_size: int
    total: int
    run_state: RunState | None = None


class QueryLeaderboard:
    """Read the authoritative projection and apply bounded presentation state."""

    def __init__(
        self,
        repository: LeaderboardRepository,
        updater: UpdateLeaderboard,
    ) -> None:
        self._repository = repository
        self._updater = updater

    async def list_policies(self) -> tuple[ScoringPolicySummary, ...]:
        """Ranking definitions that exist, so a client never guesses one."""

        return await self._repository.list_policies()

    async def execute(self, query: LeaderboardQuery) -> LeaderboardPage:
        policy = await self._repository.load_policy(query.identity.policy)
        if policy is None:
            raise policy_not_published(
                scoringPolicyId=query.identity.policy.policy_id,
                scoringPolicyVersion=query.identity.policy.version,
            )
        snapshot = await self._repository.read_snapshot(query.identity)
        if snapshot is None:
            # First read of a ranking definition materializes it from the
            # authoritative Evaluation Results without altering their values.
            await self._updater.for_identity(query.identity)
            snapshot = await self._repository.read_snapshot(query.identity)
        if snapshot is None:  # pragma: no cover - repository contract guard
            raise query_invalid("The leaderboard projection could not be resolved.")

        self._validate_sort_field(query.sort_by)
        selected = tuple(entry for entry in snapshot.entries if query.filters.keeps(entry))
        ordered = self._sort(selected, query, policy_directions=policy.direction_for)
        total = len(ordered)
        offset = (query.page - 1) * query.page_size
        page_entries = ordered[offset : offset + query.page_size]
        return LeaderboardPage(
            leaderboard_id=snapshot.leaderboard_id,
            scope_key=snapshot.scope_key,
            policy=snapshot.policy,
            rank_metric=snapshot.rank_metric,
            k=snapshot.k,
            projection_version=snapshot.projection_version,
            updated_at=snapshot.updated_at,
            metric_metadata=policy.metric_metadata(),
            entries=page_entries,
            page=query.page,
            page_size=query.page_size,
            total=total,
            run_state=snapshot.run_state,
        )

    @staticmethod
    def _validate_sort_field(sort_by: str) -> None:
        if sort_by == "RANK":
            return
        try:
            metric = MetricName(sort_by)
        except ValueError as error:
            raise query_invalid("Unsupported sortBy field.", sortBy=sort_by) from error
        if metric is MetricName.NUMBER_OF_TRADES:
            raise query_invalid("Unsupported sortBy field.", sortBy=sort_by)

    @staticmethod
    def _sort(
        entries: tuple[EntryView, ...],
        query: LeaderboardQuery,
        *,
        policy_directions: Callable[[MetricName], SortDirection],
    ) -> tuple[EntryView, ...]:
        if query.sort_by == "RANK":
            direction = query.sort_direction or SortDirection.ASC
            reverse = direction is SortDirection.DESC
            return tuple(sorted(entries, key=lambda entry: entry.rank, reverse=reverse))

        metric = MetricName(query.sort_by)
        direction = query.sort_direction or policy_directions(metric)

        def key(entry: EntryView) -> tuple[int, Decimal, int]:
            value = entry.candidate.metrics.value_of(metric)
            missing = 1 if value is None else 0
            resolved = value if value is not None else Decimal(0)
            signed = resolved if direction is SortDirection.ASC else -resolved
            return (missing, signed, entry.rank)

        return tuple(sorted(entries, key=key))


def snapshot_entry(snapshot: ProjectionSnapshot, rank: int) -> EntryView | None:
    for entry in snapshot.entries:
        if entry.rank == rank:
            return entry
    return None
