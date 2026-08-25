"""PostgreSQL projection primitives and bounded ranked-result reads for TV5."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Select, delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from crypto_lab.application.leaderboard.ports import (
    Availability,
    AvailabilityState,
    CandleView,
    EntryView,
    LeaderboardUpdatedEvent,
    MarkerShape,
    MarkerTone,
    MarkerType,
    MarkerView,
    PendingUpdate,
    ProjectionOutcome,
    ProjectionSnapshot,
    Provenance,
    RankedResultView,
    Recompute,
    RunState,
    TradePage,
    TradeView,
    UnalignedMarker,
    UpdateSource,
    VisualizationAvailability,
    VisualizationView,
)
from crypto_lab.domain.leaderboard.entry import (
    LeaderboardEntry,
    MetricSet,
    ProjectionChange,
    RankableCandidate,
    StrategyMember,
    StrategySummary,
)
from crypto_lab.domain.leaderboard.policy import (
    LeaderboardIdentity,
    LeaderboardScope,
    ProjectionVersion,
    RankMetric,
    ScoringPolicy,
    ScoringPolicyRef,
)
from crypto_lab.domain.leaderboard.ranking import diff_projection
from crypto_lab.domain.market_data.timeframe import Timeframe
from crypto_lab.infrastructure.persistence.backtest_models import (
    BacktestResultRow,
    BacktestRunRow,
    BacktestSignalSnapshotRow,
    BacktestTradeRow,
)
from crypto_lab.infrastructure.persistence.evaluation_models import (
    EvaluationResultRow,
    ScoringPolicyRow,
)
from crypto_lab.infrastructure.persistence.leaderboard_models import (
    LeaderboardEntryRow,
    LeaderboardRow,
    LeaderboardUpdateRecordRow,
)
from crypto_lab.infrastructure.persistence.models import CandleRow
from crypto_lab.infrastructure.persistence.strategy_models import StrategyDefinitionRow

_RUN_STATE_BY_STATUS = {
    "REQUESTED": RunState.QUEUED,
    "RUNNING": RunState.RUNNING,
    "COMPLETED": RunState.COMPLETED,
    "FAILED": RunState.FAILED,
    "CANCELLED": RunState.CANCELLED,
}

OVERLAYS_UNAVAILABLE_REASON = (
    "The upstream backtest result publishes no strategy overlay descriptors."
)


def parse_scope_key(scope_key: str) -> LeaderboardScope:
    """Rebuild the comparison scope stored with a persisted projection."""

    parts = dict(segment.split(":", 1) for segment in scope_key.split("|") if ":" in segment)
    pair = parts.get("pair", "*")
    timeframe = parts.get("timeframe", "*")
    run = parts.get("run", "*")
    return LeaderboardScope(
        pair=None if pair == "*" else pair,
        timeframe=None if timeframe == "*" else Timeframe(timeframe),
        run_id=None if run == "*" else UUID(run),
    )


def _strategy_summary(
    evaluation: EvaluationResultRow,
    definition: StrategyDefinitionRow | None,
) -> StrategySummary:
    """Read composition from the immutable definition without naming a strategy."""

    parameters: dict[str, Any] = dict(definition.parameters) if definition else {}
    display_name = str(parameters.get("displayName") or evaluation.strategy_id)
    members: list[StrategyMember] = []
    for raw in parameters.get("members") or ():
        if not isinstance(raw, dict):
            continue
        member_id = str(raw.get("strategyId", ""))
        member_version = str(raw.get("strategyVersion", ""))
        if not member_id or not member_version:
            continue
        members.append(
            StrategyMember(
                strategy_id=member_id,
                strategy_version=member_version,
                display_name=str(raw.get("displayName") or member_id),
            )
        )
    return StrategySummary(
        strategy_id=evaluation.strategy_id,
        strategy_version=evaluation.strategy_version,
        display_name=display_name,
        members=tuple(members),
    )


def _candidate(
    evaluation: EvaluationResultRow,
    definition: StrategyDefinitionRow | None,
    policy: ScoringPolicyRef,
) -> RankableCandidate:
    return RankableCandidate(
        evaluation_result_id=evaluation.id,
        run_id=evaluation.run_id,
        job_id=evaluation.job_id,
        backtest_result_id=evaluation.backtest_result_id,
        dataset_id=evaluation.dataset_id,
        pair=evaluation.pair,
        timeframe=Timeframe(evaluation.timeframe),
        start_time=evaluation.start_time,
        end_time=evaluation.end_time,
        strategy=_strategy_summary(evaluation, definition),
        metrics=MetricSet(
            total_return=evaluation.total_return,
            win_rate=evaluation.win_rate,
            max_drawdown=evaluation.max_drawdown,
            number_of_trades=evaluation.number_of_trades,
            sharpe_ratio=evaluation.sharpe_ratio,
            score=evaluation.score,
        ),
        policy=policy,
        evaluated_at=evaluation.evaluated_at,
        upstream_eligible=evaluation.eligible,
        upstream_exclusion_reasons=tuple(str(item) for item in evaluation.exclusion_reasons or ()),
    )


class SqlAlchemyLeaderboardRepository:
    """Owns the transaction, locking, and durable update record for a projection."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def ping(self) -> bool:
        try:
            async with self._sessions() as session:
                await session.execute(select(func.count()).select_from(LeaderboardRow))
        except Exception:
            return False
        return True

    async def load_policy(self, ref: ScoringPolicyRef) -> ScoringPolicy | None:
        async with self._sessions() as session:
            row = await self._policy_row(session, ref)
            if row is None:
                return None
            return ScoringPolicy.from_rules(
                ref,
                name=row.name,
                default_rank_metric=row.default_rank_metric,
                rules=dict(row.rules or {}),
            )

    async def mutate_projection(
        self,
        identity: LeaderboardIdentity,
        recompute: Recompute,
        *,
        now: datetime,
        source: UpdateSource | None = None,
    ) -> ProjectionOutcome:
        async with self._sessions() as session, session.begin():
            policy_row = await self._policy_row(session, identity.policy)
            if policy_row is None:
                raise LookupError("scoring policy not found")
            board = await self._lock_or_create(session, identity, policy_row.id, now)
            candidates = await self._fetch_candidates(session, identity, policy_row.id)
            current = await self._current_entries(session, board.id)
            proposed = recompute(candidates, ProjectionVersion(board.projection_version + 1))
            change = diff_projection(current, proposed.entries)
            if not change.changed:
                return ProjectionOutcome(
                    leaderboard_id=board.id,
                    projection_version=board.projection_version,
                    changed=False,
                    change=change,
                    entry_count=len(current),
                    excluded=proposed.excluded,
                    scope_key=board.scope_key,
                )

            next_version = board.projection_version + 1
            await session.execute(
                delete(LeaderboardEntryRow).where(LeaderboardEntryRow.leaderboard_id == board.id)
            )
            await session.flush()
            by_id = {item.evaluation_result_id: item for item in candidates}
            for entry in proposed.entries:
                session.add(
                    LeaderboardEntryRow(
                        id=uuid4(),
                        leaderboard_id=board.id,
                        evaluation_result_id=entry.evaluation_result_id,
                        rank=entry.rank,
                        sort_key={"components": list(entry.sort_key)},
                        projection_version=next_version,
                        entered_at=now,
                        updated_at=now,
                    )
                )
            top_candidate = (
                by_id.get(proposed.entries[0].evaluation_result_id) if proposed.entries else None
            )
            source_evaluation_id = self._source_evaluation_id(source, change, proposed.entries)
            source_run_id = (
                by_id[source_evaluation_id].run_id if source_evaluation_id in by_id else None
            )
            board.projection_version = next_version
            board.entry_count = len(proposed.entries)
            board.updated_at = now
            if source_run_id is not None:
                board.source_run_id = source_run_id

            record_id: UUID | None = None
            if source_evaluation_id is not None:
                record_id = uuid4()
                session.add(
                    LeaderboardUpdateRecordRow(
                        id=record_id,
                        leaderboard_id=board.id,
                        projection_version=next_version,
                        event_type="LEADERBOARD_UPDATED",
                        source_evaluation_result_id=source_evaluation_id,
                        source_run_id=source_run_id,
                        source_job_id=source.job_id if source else None,
                        added_ids=[str(item) for item in change.added],
                        removed_ids=[str(item) for item in change.removed],
                        moved_ids=[str(item) for item in change.moved],
                        occurred_at=now,
                        published_at=None,
                    )
                )
            top_one = (
                EntryView(
                    candidate=top_candidate,
                    rank=1,
                    projection_version=next_version,
                    updated_at=now,
                )
                if top_candidate is not None
                else None
            )
            return ProjectionOutcome(
                leaderboard_id=board.id,
                projection_version=next_version,
                changed=True,
                change=change,
                entry_count=len(proposed.entries),
                excluded=proposed.excluded,
                update_record_id=record_id,
                top_one=top_one,
                scope_key=board.scope_key,
            )

    async def read_snapshot(self, identity: LeaderboardIdentity) -> ProjectionSnapshot | None:
        async with self._sessions() as session:
            policy_row = await self._policy_row(session, identity.policy)
            if policy_row is None:
                return None
            board = await session.scalar(
                select(LeaderboardRow).where(
                    LeaderboardRow.scope_key == identity.scope_key,
                    LeaderboardRow.scoring_policy_id == policy_row.id,
                    LeaderboardRow.scoring_policy_version == identity.policy.version,
                    LeaderboardRow.rank_metric == identity.rank_metric.value,
                    LeaderboardRow.k == identity.k,
                )
            )
            if board is None:
                return None
            return await self._snapshot_of(session, board, identity.policy)

    async def read_snapshot_by_id(self, leaderboard_id: UUID) -> ProjectionSnapshot | None:
        async with self._sessions() as session:
            board = await session.get(LeaderboardRow, leaderboard_id)
            if board is None:
                return None
            policy_row = await session.get(ScoringPolicyRow, board.scoring_policy_id)
            if policy_row is None:  # pragma: no cover - foreign key guard
                return None
            ref = ScoringPolicyRef(policy_row.policy_id, board.scoring_policy_version)
            return await self._snapshot_of(session, board, ref)

    async def find_identities_for_evaluation(
        self,
        evaluation_result_id: UUID,
    ) -> tuple[LeaderboardIdentity, ...]:
        async with self._sessions() as session:
            evaluation = await session.get(EvaluationResultRow, evaluation_result_id)
            if evaluation is None:
                return ()
            policy_row = await session.get(ScoringPolicyRow, evaluation.scoring_policy_id)
            if policy_row is None:  # pragma: no cover - foreign key guard
                return ()
            scope_keys = [
                LeaderboardScope(pair=pair, timeframe=timeframe, run_id=run_id).scope_key
                for pair in (evaluation.pair, None)
                for timeframe in (Timeframe(evaluation.timeframe), None)
                for run_id in (evaluation.run_id, None)
            ]
            rows = (
                await session.scalars(
                    select(LeaderboardRow).where(
                        LeaderboardRow.scoring_policy_id == policy_row.id,
                        LeaderboardRow.scoring_policy_version == evaluation.scoring_policy_version,
                        LeaderboardRow.scope_key.in_(scope_keys),
                    )
                )
            ).all()
            ref = ScoringPolicyRef(policy_row.policy_id, evaluation.scoring_policy_version)
            return tuple(
                LeaderboardIdentity(
                    scope=parse_scope_key(row.scope_key),
                    policy=ref,
                    rank_metric=RankMetric(row.rank_metric),
                    k=row.k,
                )
                for row in rows
            )

    async def claim_pending_updates(self, limit: int) -> tuple[PendingUpdate, ...]:
        """Claim committed, unpublished records so publication can retry safely."""

        async with self._sessions() as session, session.begin():
            rows = (
                await session.scalars(
                    select(LeaderboardUpdateRecordRow)
                    .where(LeaderboardUpdateRecordRow.published_at.is_(None))
                    .order_by(LeaderboardUpdateRecordRow.occurred_at)
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
            ).all()
            pending: list[PendingUpdate] = []
            for row in rows:
                board = await session.get(LeaderboardRow, row.leaderboard_id)
                if board is None:  # pragma: no cover - cascade guard
                    continue
                policy_row = await session.get(ScoringPolicyRow, board.scoring_policy_id)
                if policy_row is None:  # pragma: no cover - foreign key guard
                    continue
                ref = ScoringPolicyRef(policy_row.policy_id, board.scoring_policy_version)
                snapshot = await self._snapshot_of(session, board, ref)
                top_one = snapshot.entries[0] if snapshot.entries else None
                run_state = await self._run_state(session, board.source_run_id)
                pending.append(
                    PendingUpdate(
                        record_id=row.id,
                        event=LeaderboardUpdatedEvent(
                            event_id=row.id,
                            leaderboard_id=board.id,
                            scope_key=board.scope_key,
                            policy=ref,
                            rank_metric=RankMetric(board.rank_metric),
                            k=board.k,
                            projection_version=row.projection_version,
                            updated_at=board.updated_at,
                            occurred_at=row.occurred_at,
                            entry_count=board.entry_count,
                            added=tuple(UUID(item) for item in row.added_ids),
                            removed=tuple(UUID(item) for item in row.removed_ids),
                            moved=tuple(UUID(item) for item in row.moved_ids),
                            top_one=_top_one_payload(top_one),
                            run_state=run_state,
                            run_id=row.source_run_id,
                            job_id=row.source_job_id,
                        ),
                    )
                )
            return tuple(pending)

    async def mark_published(self, record_id: UUID, published_at: datetime) -> None:
        async with self._sessions() as session, session.begin():
            row = await session.get(LeaderboardUpdateRecordRow, record_id)
            if row is not None and row.published_at is None:
                row.published_at = published_at

    # -- internals -----------------------------------------------------------

    async def _policy_row(
        self,
        session: AsyncSession,
        ref: ScoringPolicyRef,
    ) -> ScoringPolicyRow | None:
        row: ScoringPolicyRow | None = await session.scalar(
            select(ScoringPolicyRow).where(
                ScoringPolicyRow.policy_id == ref.policy_id,
                ScoringPolicyRow.version == ref.version,
            )
        )
        return row

    async def _lock_or_create(
        self,
        session: AsyncSession,
        identity: LeaderboardIdentity,
        policy_row_id: UUID,
        now: datetime,
    ) -> LeaderboardRow:
        def locked() -> Select[tuple[LeaderboardRow]]:
            return (
                select(LeaderboardRow)
                .where(
                    LeaderboardRow.scope_key == identity.scope_key,
                    LeaderboardRow.scoring_policy_id == policy_row_id,
                    LeaderboardRow.scoring_policy_version == identity.policy.version,
                    LeaderboardRow.rank_metric == identity.rank_metric.value,
                    LeaderboardRow.k == identity.k,
                )
                .with_for_update()
            )

        board = await session.scalar(locked())
        if board is not None:
            return board
        await session.execute(
            insert(LeaderboardRow)
            .values(
                id=uuid4(),
                scope_key=identity.scope_key,
                scoring_policy_id=policy_row_id,
                scoring_policy_version=identity.policy.version,
                rank_metric=identity.rank_metric.value,
                k=identity.k,
                projection_version=0,
                updated_at=now,
                entry_count=0,
            )
            .on_conflict_do_nothing(constraint="uq_leaderboards_identity")
        )
        created: LeaderboardRow | None = await session.scalar(locked())
        if created is None:  # pragma: no cover - unique constraint guarantees a row
            raise LookupError("leaderboard projection could not be created")
        return created

    async def _fetch_candidates(
        self,
        session: AsyncSession,
        identity: LeaderboardIdentity,
        policy_row_id: UUID,
    ) -> tuple[RankableCandidate, ...]:
        query = (
            select(EvaluationResultRow, StrategyDefinitionRow)
            .join(
                StrategyDefinitionRow,
                StrategyDefinitionRow.id == EvaluationResultRow.strategy_definition_id,
                isouter=True,
            )
            .where(
                EvaluationResultRow.scoring_policy_id == policy_row_id,
                EvaluationResultRow.scoring_policy_version == identity.policy.version,
            )
        )
        scope = identity.scope
        if scope.pair is not None:
            query = query.where(EvaluationResultRow.pair == scope.pair)
        if scope.timeframe is not None:
            query = query.where(EvaluationResultRow.timeframe == scope.timeframe.value)
        if scope.run_id is not None:
            query = query.where(EvaluationResultRow.run_id == scope.run_id)
        rows = (await session.execute(query)).all()
        return tuple(
            _candidate(evaluation, definition, identity.policy) for evaluation, definition in rows
        )

    async def _current_entries(
        self,
        session: AsyncSession,
        leaderboard_id: UUID,
    ) -> tuple[LeaderboardEntry, ...]:
        rows = (
            await session.scalars(
                select(LeaderboardEntryRow)
                .where(LeaderboardEntryRow.leaderboard_id == leaderboard_id)
                .order_by(LeaderboardEntryRow.rank)
            )
        ).all()
        return tuple(
            LeaderboardEntry(
                evaluation_result_id=row.evaluation_result_id,
                rank=row.rank,
                projection_version=ProjectionVersion(row.projection_version),
                sort_key=_sort_key_components(row.sort_key),
            )
            for row in rows
        )

    async def _snapshot_of(
        self,
        session: AsyncSession,
        board: LeaderboardRow,
        ref: ScoringPolicyRef,
    ) -> ProjectionSnapshot:
        rows = (
            await session.execute(
                select(LeaderboardEntryRow, EvaluationResultRow, StrategyDefinitionRow)
                .join(
                    EvaluationResultRow,
                    EvaluationResultRow.id == LeaderboardEntryRow.evaluation_result_id,
                )
                .join(
                    StrategyDefinitionRow,
                    StrategyDefinitionRow.id == EvaluationResultRow.strategy_definition_id,
                    isouter=True,
                )
                .where(LeaderboardEntryRow.leaderboard_id == board.id)
                .order_by(LeaderboardEntryRow.rank)
            )
        ).all()
        entries = tuple(
            EntryView(
                candidate=_candidate(evaluation, definition, ref),
                rank=entry.rank,
                projection_version=entry.projection_version,
                updated_at=entry.updated_at,
            )
            for entry, evaluation, definition in rows
        )
        return ProjectionSnapshot(
            leaderboard_id=board.id,
            scope_key=board.scope_key,
            policy=ref,
            rank_metric=RankMetric(board.rank_metric),
            k=board.k,
            projection_version=board.projection_version,
            updated_at=board.updated_at,
            entries=entries,
            run_state=await self._run_state(session, board.source_run_id),
        )

    async def _run_state(self, session: AsyncSession, run_id: UUID | None) -> RunState | None:
        if run_id is None:
            return None
        run = await session.get(BacktestRunRow, run_id)
        if run is None:  # pragma: no cover - foreign key guard
            return None
        return _RUN_STATE_BY_STATUS.get(run.status)

    @staticmethod
    def _source_evaluation_id(
        source: UpdateSource | None,
        change: ProjectionChange,
        entries: tuple[LeaderboardEntry, ...],
    ) -> UUID | None:
        if source is not None:
            return UUID(str(source.evaluation_result_id))
        for group in (change.added, change.moved, change.removed):
            if group:
                return group[0]
        if entries:  # pragma: no cover - defensive
            return entries[0].evaluation_result_id
        return None


def _sort_key_components(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, dict):
        return ()
    components = raw.get("components", ())
    if not isinstance(components, list | tuple):
        return ()
    return tuple(str(item) for item in components)


def _top_one_payload(entry: EntryView | None) -> dict[str, str] | None:
    if entry is None:
        return None
    from crypto_lab.domain.market_data.candle import canonical_decimal

    return {
        "evaluationResultId": str(entry.candidate.evaluation_result_id),
        "strategyId": entry.candidate.strategy.strategy_id,
        "strategyVersion": entry.candidate.strategy.strategy_version,
        "rank": str(entry.rank),
        "score": canonical_decimal(entry.candidate.metrics.score),
    }


class SqlAlchemyRankedResultReader:
    """Immutable provenance joins and bounded visualization/trade reads."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def read_detail(
        self,
        leaderboard_id: UUID,
        evaluation_result_id: UUID,
    ) -> RankedResultView | None:
        async with self._sessions() as session:
            context = await self._context(session, leaderboard_id, evaluation_result_id)
            if context is None:
                return None
            entry_row, evaluation, definition, board = context
            policy_row = await session.get(ScoringPolicyRow, board.scoring_policy_id)
            ref = ScoringPolicyRef(
                policy_row.policy_id if policy_row else "unknown",
                board.scoring_policy_version,
            )
            result = await session.get(BacktestResultRow, evaluation.backtest_result_id)
            candle_count = await self._candle_count(session, evaluation)
            signal_count = await session.scalar(
                select(func.count())
                .select_from(BacktestSignalSnapshotRow)
                .where(
                    BacktestSignalSnapshotRow.backtest_result_id == evaluation.backtest_result_id
                )
            )
            trade_count = await session.scalar(
                select(func.count())
                .select_from(BacktestTradeRow)
                .where(BacktestTradeRow.backtest_result_id == evaluation.backtest_result_id)
            )
            availability = VisualizationAvailability(
                candles=_availability(candle_count or 0, "No Candle is stored for this range."),
                overlays=Availability(
                    AvailabilityState.UNAVAILABLE,
                    0,
                    OVERLAYS_UNAVAILABLE_REASON,
                ),
                signals=_availability(signal_count or 0, "The result recorded no Signal."),
                trades=_availability(trade_count or 0, "The result produced no simulated Trade."),
            )
            return RankedResultView(
                entry=EntryView(
                    candidate=_candidate(evaluation, definition, ref),
                    rank=entry_row.rank,
                    projection_version=entry_row.projection_version,
                    updated_at=entry_row.updated_at,
                ),
                provenance=Provenance(
                    evaluation_result_id=evaluation.id,
                    backtest_result_id=evaluation.backtest_result_id,
                    run_id=evaluation.run_id,
                    job_id=evaluation.job_id,
                    strategy_id=evaluation.strategy_id,
                    strategy_version=evaluation.strategy_version,
                    dataset_id=evaluation.dataset_id,
                    execution_config=dict(evaluation.execution_config or {}),
                    result_checksum=result.result_checksum if result else "",
                    scoring_policy_id=ref.policy_id,
                    scoring_policy_version=ref.version,
                ),
                availability=availability,
            )

    async def read_visualization(
        self,
        leaderboard_id: UUID,
        evaluation_result_id: UUID,
        start_time: datetime,
        end_time: datetime,
    ) -> VisualizationView | None:
        async with self._sessions() as session:
            context = await self._context(session, leaderboard_id, evaluation_result_id)
            if context is None:
                return None
            _, evaluation, _, _ = context
            candles = await self._candles(session, evaluation, start_time, end_time)
            by_time = {candle.open_time: candle for candle in candles}
            markers: list[MarkerView] = []
            unaligned: list[UnalignedMarker] = []

            signals = (
                await session.scalars(
                    select(BacktestSignalSnapshotRow)
                    .where(
                        BacktestSignalSnapshotRow.backtest_result_id
                        == evaluation.backtest_result_id,
                        BacktestSignalSnapshotRow.timestamp >= start_time,
                        BacktestSignalSnapshotRow.timestamp <= end_time,
                    )
                    .order_by(BacktestSignalSnapshotRow.sequence)
                )
            ).all()
            for signal in signals:
                marker_type = MarkerType(signal.action)
                candle = by_time.get(signal.timestamp)
                marker = MarkerView(
                    id=f"signal-{signal.id}",
                    type=marker_type,
                    time=signal.timestamp,
                    price=candle.close if candle else None,
                    label=marker_type.value,
                    shape=_SIGNAL_SHAPES[marker_type],
                    tone=_SIGNAL_TONES[marker_type],
                    source_strategy_id=signal.strategy_id,
                    source_strategy_version=signal.strategy_version,
                    signal_id=signal.id,
                )
                if candle is None:
                    unaligned.append(
                        UnalignedMarker(
                            marker=marker,
                            reason="No Candle in the loaded range matches this Signal timestamp.",
                        )
                    )
                else:
                    markers.append(marker)

            trades = (
                await session.scalars(
                    select(BacktestTradeRow)
                    .where(
                        BacktestTradeRow.backtest_result_id == evaluation.backtest_result_id,
                        BacktestTradeRow.exit_time >= start_time,
                        BacktestTradeRow.entry_time <= end_time,
                    )
                    .order_by(BacktestTradeRow.sequence)
                )
            ).all()
            for trade in trades:
                number = trade.sequence + 1
                for marker_type, moment, price in (
                    (MarkerType.ENTRY, trade.entry_time, trade.entry_price),
                    (MarkerType.EXIT, trade.exit_time, trade.exit_price),
                ):
                    aligned = moment in by_time
                    marker = MarkerView(
                        id=f"trade-{trade.id}-{marker_type.value.lower()}",
                        type=marker_type,
                        time=moment,
                        price=price if aligned else None,
                        label=f"{marker_type.value} #{number}",
                        shape=_SIGNAL_SHAPES[marker_type],
                        tone=_SIGNAL_TONES[marker_type],
                        source_strategy_id=evaluation.strategy_id,
                        source_strategy_version=evaluation.strategy_version,
                        trade_id=trade.id,
                    )
                    if aligned:
                        markers.append(marker)
                    else:
                        unaligned.append(
                            UnalignedMarker(
                                marker=marker,
                                reason=(
                                    "No Candle in the loaded range matches this Trade timestamp."
                                ),
                            )
                        )

            total_signals = await session.scalar(
                select(func.count())
                .select_from(BacktestSignalSnapshotRow)
                .where(
                    BacktestSignalSnapshotRow.backtest_result_id == evaluation.backtest_result_id
                )
            )
            total_trades = await session.scalar(
                select(func.count())
                .select_from(BacktestTradeRow)
                .where(BacktestTradeRow.backtest_result_id == evaluation.backtest_result_id)
            )
            availability = VisualizationAvailability(
                candles=_availability(len(candles), "No Candle is stored for this range."),
                overlays=Availability(
                    AvailabilityState.UNAVAILABLE,
                    0,
                    OVERLAYS_UNAVAILABLE_REASON,
                ),
                signals=_partial_availability(len(signals), total_signals or 0, "Signal"),
                trades=_partial_availability(len(trades), total_trades or 0, "Trade"),
            )
            return VisualizationView(
                pair=evaluation.pair,
                timeframe=evaluation.timeframe,
                start_time=start_time,
                end_time=end_time,
                availability=availability,
                candles=tuple(
                    CandleView(
                        open_time=candle.open_time,
                        open=candle.open,
                        high=candle.high,
                        low=candle.low,
                        close=candle.close,
                        volume=candle.volume,
                    )
                    for candle in candles
                ),
                overlays=(),
                markers=tuple(markers),
                unaligned_markers=tuple(unaligned),
            )

    async def read_trades(
        self,
        leaderboard_id: UUID,
        evaluation_result_id: UUID,
        *,
        page: int,
        page_size: int,
        sort_by: str,
        sort_direction: str,
    ) -> TradePage | None:
        async with self._sessions() as session:
            context = await self._context(session, leaderboard_id, evaluation_result_id)
            if context is None:
                return None
            _, evaluation, _, _ = context
            column = {
                "ENTRY_TIME": BacktestTradeRow.entry_time,
                "EXIT_TIME": BacktestTradeRow.exit_time,
                "RETURN_PERCENT": BacktestTradeRow.return_percent,
            }[sort_by]
            ordering = column.desc() if sort_direction == "DESC" else column.asc()
            total = await session.scalar(
                select(func.count())
                .select_from(BacktestTradeRow)
                .where(BacktestTradeRow.backtest_result_id == evaluation.backtest_result_id)
            )
            rows = (
                await session.scalars(
                    select(BacktestTradeRow)
                    .where(BacktestTradeRow.backtest_result_id == evaluation.backtest_result_id)
                    .order_by(ordering, BacktestTradeRow.sequence)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
            return TradePage(
                items=tuple(
                    TradeView(
                        trade_id=row.id,
                        entry_time=row.entry_time,
                        entry_price=row.entry_price,
                        exit_time=row.exit_time,
                        exit_price=row.exit_price,
                        side=row.side,
                        quantity=row.quantity,
                        profit_loss=row.profit_loss,
                        return_percent=row.return_percent,
                        entry_signal_id=row.entry_signal_snapshot_id,
                        exit_signal_id=row.exit_signal_snapshot_id,
                    )
                    for row in rows
                ),
                page=page,
                page_size=page_size,
                total=total or 0,
            )

    # -- internals -----------------------------------------------------------

    async def _context(
        self,
        session: AsyncSession,
        leaderboard_id: UUID,
        evaluation_result_id: UUID,
    ) -> (
        tuple[
            LeaderboardEntryRow, EvaluationResultRow, StrategyDefinitionRow | None, LeaderboardRow
        ]
        | None
    ):
        row = (
            await session.execute(
                select(
                    LeaderboardEntryRow, EvaluationResultRow, StrategyDefinitionRow, LeaderboardRow
                )
                .join(
                    EvaluationResultRow,
                    EvaluationResultRow.id == LeaderboardEntryRow.evaluation_result_id,
                )
                .join(
                    StrategyDefinitionRow,
                    StrategyDefinitionRow.id == EvaluationResultRow.strategy_definition_id,
                    isouter=True,
                )
                .join(LeaderboardRow, LeaderboardRow.id == LeaderboardEntryRow.leaderboard_id)
                .where(
                    LeaderboardEntryRow.leaderboard_id == leaderboard_id,
                    LeaderboardEntryRow.evaluation_result_id == evaluation_result_id,
                )
            )
        ).first()
        if row is None:
            return None
        entry_row, evaluation, definition, board = row
        return entry_row, evaluation, definition, board

    async def _candles(
        self,
        session: AsyncSession,
        evaluation: EvaluationResultRow,
        start_time: datetime,
        end_time: datetime,
    ) -> list[CandleRow]:
        return list(
            (
                await session.scalars(
                    select(CandleRow)
                    .where(
                        CandleRow.pair == evaluation.pair,
                        CandleRow.timeframe == evaluation.timeframe,
                        CandleRow.open_time >= start_time,
                        CandleRow.open_time <= end_time,
                    )
                    .order_by(CandleRow.open_time)
                )
            ).all()
        )

    async def _candle_count(
        self,
        session: AsyncSession,
        evaluation: EvaluationResultRow,
    ) -> int | None:
        count: int | None = await session.scalar(
            select(func.count())
            .select_from(CandleRow)
            .where(
                CandleRow.pair == evaluation.pair,
                CandleRow.timeframe == evaluation.timeframe,
                CandleRow.open_time >= evaluation.start_time,
                CandleRow.open_time <= evaluation.end_time,
            )
        )
        return count


_SIGNAL_SHAPES = {
    MarkerType.BUY: MarkerShape.TRIANGLE_UP,
    MarkerType.SELL: MarkerShape.TRIANGLE_DOWN,
    MarkerType.HOLD: MarkerShape.DIAMOND,
    MarkerType.ENTRY: MarkerShape.ENTRY_OUTLINED,
    MarkerType.EXIT: MarkerShape.EXIT_OUTLINED,
}

_SIGNAL_TONES = {
    MarkerType.BUY: MarkerTone.POSITIVE,
    MarkerType.SELL: MarkerTone.NEGATIVE,
    MarkerType.HOLD: MarkerTone.NEUTRAL,
    MarkerType.ENTRY: MarkerTone.INFO,
    MarkerType.EXIT: MarkerTone.INFO,
}


def _availability(count: int, empty_reason: str) -> Availability:
    if count > 0:
        return Availability(AvailabilityState.AVAILABLE, count)
    return Availability(AvailabilityState.EMPTY, 0, empty_reason)


def _partial_availability(loaded: int, total: int, label: str) -> Availability:
    if total == 0:
        return Availability(AvailabilityState.EMPTY, 0, f"The result recorded no {label}.")
    if loaded == 0:
        return Availability(
            AvailabilityState.PARTIAL,
            0,
            f"No {label} falls inside the requested range.",
        )
    if loaded < total:
        return Availability(
            AvailabilityState.PARTIAL,
            loaded,
            f"{loaded} of {total} {label} records fall inside the requested range.",
        )
    return Availability(AvailabilityState.AVAILABLE, loaded)


__all__ = [
    "SqlAlchemyLeaderboardRepository",
    "SqlAlchemyRankedResultReader",
    "parse_scope_key",
]
