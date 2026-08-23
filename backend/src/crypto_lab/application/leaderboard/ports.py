"""Typed ports for the leaderboard projection, readers, and update publication."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID

from crypto_lab.domain.leaderboard.entry import (
    LeaderboardEntry,
    ProjectionChange,
    RankableCandidate,
)
from crypto_lab.domain.leaderboard.policy import (
    LeaderboardIdentity,
    ProjectionVersion,
    RankMetric,
    ScoringPolicy,
    ScoringPolicyRef,
)
from crypto_lab.domain.leaderboard.ranking import ExcludedCandidate, RankingOutcome


class Clock(Protocol):
    def now(self) -> datetime: ...


class RunState(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AvailabilityState(StrEnum):
    AVAILABLE = "AVAILABLE"
    EMPTY = "EMPTY"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"


class MarkerType(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    ENTRY = "ENTRY"
    EXIT = "EXIT"


class MarkerShape(StrEnum):
    ARROW_UP = "ARROW_UP"
    ARROW_DOWN = "ARROW_DOWN"
    TRIANGLE_UP = "TRIANGLE_UP"
    TRIANGLE_DOWN = "TRIANGLE_DOWN"
    DIAMOND = "DIAMOND"
    DOT = "DOT"
    ENTRY_OUTLINED = "ENTRY_OUTLINED"
    EXIT_OUTLINED = "EXIT_OUTLINED"


class MarkerTone(StrEnum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    INFO = "INFO"


class OverlayKind(StrEnum):
    LINE = "LINE"
    BAND = "BAND"
    ZONE = "ZONE"


@dataclass(frozen=True, slots=True)
class Availability:
    state: AvailabilityState
    count: int = 0
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class EntryView:
    """One ranked row joined to its immutable Evaluation Result."""

    candidate: RankableCandidate
    rank: int
    projection_version: int
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ProjectionSnapshot:
    """Authoritative current projection returned by REST reads."""

    leaderboard_id: UUID
    scope_key: str
    policy: ScoringPolicyRef
    rank_metric: RankMetric
    k: int
    projection_version: int
    updated_at: datetime
    entries: tuple[EntryView, ...]
    run_state: RunState | None = None


@dataclass(frozen=True, slots=True)
class ProjectionOutcome:
    """Result of one transactional projection mutation."""

    leaderboard_id: UUID
    projection_version: int
    changed: bool
    change: ProjectionChange
    entry_count: int
    excluded: tuple[ExcludedCandidate, ...] = ()
    update_record_id: UUID | None = None
    top_one: EntryView | None = None
    run_state: RunState | None = None
    scope_key: str = ""


@dataclass(frozen=True, slots=True)
class UpdateSource:
    """Correlation identity of the evaluation that triggered a recomputation."""

    evaluation_result_id: UUID
    run_id: UUID | None = None
    job_id: UUID | None = None
    request_id: str | None = None


@dataclass(frozen=True, slots=True)
class Provenance:
    evaluation_result_id: UUID
    backtest_result_id: UUID
    run_id: UUID
    job_id: UUID
    strategy_id: str
    strategy_version: str
    dataset_id: UUID
    execution_config: dict[str, Any]
    result_checksum: str
    scoring_policy_id: str
    scoring_policy_version: str


@dataclass(frozen=True, slots=True)
class VisualizationAvailability:
    candles: Availability
    overlays: Availability
    signals: Availability
    trades: Availability


@dataclass(frozen=True, slots=True)
class RankedResultView:
    entry: EntryView
    provenance: Provenance
    availability: VisualizationAvailability


@dataclass(frozen=True, slots=True)
class CandleView:
    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True, slots=True)
class OverlayPoint:
    time: datetime | None = None
    value: Decimal | None = None
    upper: Decimal | None = None
    middle: Decimal | None = None
    lower: Decimal | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None


@dataclass(frozen=True, slots=True)
class OverlayView:
    id: str
    kind: OverlayKind
    label: str
    style_token: str
    source_strategy_id: str
    source_strategy_version: str
    points: tuple[OverlayPoint, ...] = ()


@dataclass(frozen=True, slots=True)
class MarkerView:
    id: str
    type: MarkerType
    time: datetime
    price: Decimal | None
    label: str
    shape: MarkerShape
    source_strategy_id: str
    source_strategy_version: str
    tone: MarkerTone | None = None
    signal_id: UUID | None = None
    trade_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class UnalignedMarker:
    marker: MarkerView
    reason: str


@dataclass(frozen=True, slots=True)
class VisualizationView:
    pair: str
    timeframe: str
    start_time: datetime
    end_time: datetime
    availability: VisualizationAvailability
    candles: tuple[CandleView, ...] = ()
    overlays: tuple[OverlayView, ...] = ()
    markers: tuple[MarkerView, ...] = ()
    unaligned_markers: tuple[UnalignedMarker, ...] = ()


@dataclass(frozen=True, slots=True)
class TradeView:
    trade_id: UUID
    entry_time: datetime
    entry_price: Decimal
    exit_time: datetime
    exit_price: Decimal
    side: str
    quantity: Decimal
    profit_loss: Decimal
    return_percent: Decimal
    entry_signal_id: UUID | None = None
    exit_signal_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class TradePage:
    items: tuple[TradeView, ...]
    page: int
    page_size: int
    total: int


@dataclass(frozen=True, slots=True)
class LeaderboardUpdatedEvent:
    """Transport-neutral projection change notification."""

    event_id: UUID
    leaderboard_id: UUID
    scope_key: str
    policy: ScoringPolicyRef
    rank_metric: RankMetric
    k: int
    projection_version: int
    updated_at: datetime
    occurred_at: datetime
    entry_count: int
    added: tuple[UUID, ...] = ()
    removed: tuple[UUID, ...] = ()
    moved: tuple[UUID, ...] = ()
    top_one: dict[str, str] | None = None
    run_state: RunState | None = None
    run_id: UUID | None = None
    job_id: UUID | None = None
    request_id: str | None = None


@dataclass(frozen=True, slots=True)
class PendingUpdate:
    """A committed, not-yet-published durable update record."""

    event: LeaderboardUpdatedEvent
    record_id: UUID


Recompute = Callable[[tuple[RankableCandidate, ...], ProjectionVersion], RankingOutcome]


class LeaderboardRepository(Protocol):
    """Transactional projection primitives and bounded authoritative reads."""

    async def load_policy(self, ref: ScoringPolicyRef) -> ScoringPolicy | None: ...

    async def mutate_projection(
        self,
        identity: LeaderboardIdentity,
        recompute: Recompute,
        *,
        now: datetime,
        source: UpdateSource | None = None,
    ) -> ProjectionOutcome: ...

    async def read_snapshot(
        self,
        identity: LeaderboardIdentity,
    ) -> ProjectionSnapshot | None: ...

    async def read_snapshot_by_id(self, leaderboard_id: UUID) -> ProjectionSnapshot | None: ...

    async def find_identities_for_evaluation(
        self,
        evaluation_result_id: UUID,
    ) -> tuple[LeaderboardIdentity, ...]: ...

    async def claim_pending_updates(self, limit: int) -> tuple[PendingUpdate, ...]: ...

    async def mark_published(self, record_id: UUID, published_at: datetime) -> None: ...

    async def ping(self) -> bool: ...


class RankedResultReader(Protocol):
    """Immutable provenance and bounded visualization reads for one ranked row."""

    async def read_detail(
        self,
        leaderboard_id: UUID,
        evaluation_result_id: UUID,
    ) -> RankedResultView | None: ...

    async def read_visualization(
        self,
        leaderboard_id: UUID,
        evaluation_result_id: UUID,
        start_time: datetime,
        end_time: datetime,
    ) -> VisualizationView | None: ...

    async def read_trades(
        self,
        leaderboard_id: UUID,
        evaluation_result_id: UUID,
        *,
        page: int,
        page_size: int,
        sort_by: str,
        sort_direction: str,
    ) -> TradePage | None: ...


class LeaderboardUpdatePublisher(Protocol):
    async def publish(self, event: LeaderboardUpdatedEvent) -> None: ...


class ProjectionObserver(Protocol):
    """Sanitized observability sink: identifiers and counters only."""

    def projection_changed(
        self,
        outcome: ProjectionOutcome,
        *,
        latency_ms: float,
        source: UpdateSource | None,
    ) -> None: ...

    def projection_unchanged(
        self,
        outcome: ProjectionOutcome,
        *,
        source: UpdateSource | None,
    ) -> None: ...

    def events_published(self, count: int) -> None: ...

    def publication_failed(self, event: LeaderboardUpdatedEvent) -> None: ...


@dataclass(slots=True)
class NullObserver:
    """Default observer used when no observability sink is configured."""

    def projection_changed(
        self,
        outcome: ProjectionOutcome,
        *,
        latency_ms: float,
        source: UpdateSource | None,
    ) -> None:
        return None

    def projection_unchanged(
        self,
        outcome: ProjectionOutcome,
        *,
        source: UpdateSource | None,
    ) -> None:
        return None

    def events_published(self, count: int) -> None:
        return None

    def publication_failed(self, event: LeaderboardUpdatedEvent) -> None:
        return None


@dataclass(slots=True)
class RecordingPublisher:
    """In-memory publisher used by tests and by the local dispatcher default."""

    events: list[LeaderboardUpdatedEvent] = field(default_factory=list)

    async def publish(self, event: LeaderboardUpdatedEvent) -> None:
        self.events.append(event)


__all__ = [
    "Availability",
    "AvailabilityState",
    "CandleView",
    "Clock",
    "EntryView",
    "ExcludedCandidate",
    "LeaderboardEntry",
    "LeaderboardRepository",
    "LeaderboardUpdatePublisher",
    "LeaderboardUpdatedEvent",
    "MarkerShape",
    "MarkerTone",
    "MarkerType",
    "MarkerView",
    "NullObserver",
    "OverlayKind",
    "OverlayPoint",
    "OverlayView",
    "PendingUpdate",
    "ProjectionObserver",
    "ProjectionOutcome",
    "ProjectionSnapshot",
    "Provenance",
    "RankedResultReader",
    "RankedResultView",
    "Recompute",
    "RecordingPublisher",
    "RunState",
    "TradePage",
    "TradeView",
    "UnalignedMarker",
    "UpdateSource",
    "VisualizationAvailability",
    "VisualizationView",
]
