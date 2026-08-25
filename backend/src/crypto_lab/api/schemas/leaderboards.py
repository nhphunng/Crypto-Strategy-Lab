"""Request, response, and event DTOs aligned to the TV5 contracts.

JSON is camelCase, decimals are exact strings, and instants are UTC ISO-8601.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import Field

from crypto_lab.api.common import ApiModel
from crypto_lab.application.leaderboard.ports import (
    Availability,
    EntryView,
    LeaderboardUpdatedEvent,
    MarkerView,
    OverlayView,
    Provenance,
    RankedResultView,
    TradePage,
    VisualizationAvailability,
    VisualizationView,
)
from crypto_lab.application.leaderboard.query_leaderboard import LeaderboardPage
from crypto_lab.domain.leaderboard.policy import MetricDescriptor
from crypto_lab.domain.market_data.candle import canonical_decimal, format_utc_millis


def _decimal(value: Decimal | None) -> str | None:
    return None if value is None else canonical_decimal(value)


def _instant(value: datetime) -> str:
    return format_utc_millis(value)


class MetricSetDto(ApiModel):
    total_return: str = Field(alias="totalReturn")
    win_rate: str = Field(alias="winRate")
    max_drawdown: str = Field(alias="maxDrawdown")
    number_of_trades: int = Field(alias="numberOfTrades")
    sharpe_ratio: str | None = Field(default=None, alias="sharpeRatio")


class StrategyMemberDto(ApiModel):
    strategy_id: str = Field(alias="strategyId")
    strategy_version: str = Field(alias="strategyVersion")
    display_name: str = Field(alias="displayName")


class StrategySummaryDto(ApiModel):
    strategy_id: str = Field(alias="strategyId")
    strategy_version: str = Field(alias="strategyVersion")
    display_name: str = Field(alias="displayName")
    members: tuple[StrategyMemberDto, ...] = ()


class MetricDescriptorDto(ApiModel):
    metric: str
    direction: str
    unit: str


class PageMetaDto(ApiModel):
    page: int
    page_size: int = Field(alias="pageSize")
    total: int


class LeaderboardEntryDto(ApiModel):
    evaluation_result_id: str = Field(alias="evaluationResultId")
    rank: int
    projection_version: int = Field(alias="projectionVersion")
    score: str
    strategy: StrategySummaryDto
    pair: str
    timeframe: str
    dataset_id: str = Field(alias="datasetId")
    start_time: str = Field(alias="startTime")
    end_time: str = Field(alias="endTime")
    metrics: MetricSetDto
    scoring_policy_id: str = Field(alias="scoringPolicyId")
    scoring_policy_version: str = Field(alias="scoringPolicyVersion")
    updated_at: str = Field(alias="updatedAt")


class LeaderboardSnapshotDto(ApiModel):
    leaderboard_id: str = Field(alias="leaderboardId")
    scope_key: str = Field(alias="scopeKey")
    scoring_policy_id: str = Field(alias="scoringPolicyId")
    scoring_policy_version: str = Field(alias="scoringPolicyVersion")
    rank_by: str = Field(alias="rankBy")
    k: int
    projection_version: int = Field(alias="projectionVersion")
    updated_at: str = Field(alias="updatedAt")
    run_state: str | None = Field(default=None, alias="runState")
    metric_metadata: tuple[MetricDescriptorDto, ...] = Field(alias="metricMetadata")
    entries: tuple[LeaderboardEntryDto, ...]
    pagination: PageMetaDto
    disclaimer: str


class AvailabilityDto(ApiModel):
    state: str
    count: int = 0
    reason: str | None = None


class VisualizationAvailabilityDto(ApiModel):
    candles: AvailabilityDto
    overlays: AvailabilityDto
    signals: AvailabilityDto
    trades: AvailabilityDto


class ProvenanceDto(ApiModel):
    evaluation_result_id: str = Field(alias="evaluationResultId")
    backtest_result_id: str = Field(alias="backtestResultId")
    run_id: str = Field(alias="runId")
    job_id: str = Field(alias="jobId")
    strategy_id: str = Field(alias="strategyId")
    strategy_version: str = Field(alias="strategyVersion")
    dataset_id: str = Field(alias="datasetId")
    execution_config: dict[str, Any] = Field(alias="executionConfig")
    result_checksum: str = Field(alias="resultChecksum")
    scoring_policy_id: str = Field(alias="scoringPolicyId")
    scoring_policy_version: str = Field(alias="scoringPolicyVersion")


class RankedResultDetailDto(ApiModel):
    entry: LeaderboardEntryDto
    provenance: ProvenanceDto
    candles: AvailabilityDto
    overlays: AvailabilityDto
    signals: AvailabilityDto
    trades: AvailabilityDto
    disclaimer: str


class CandleDto(ApiModel):
    open_time: str = Field(alias="openTime")
    open: str
    high: str
    low: str
    close: str
    volume: str


class OverlayPointDto(ApiModel):
    time: str | None = None
    value: str | None = None
    upper: str | None = None
    middle: str | None = None
    lower: str | None = None
    start_time: str | None = Field(default=None, alias="startTime")
    end_time: str | None = Field(default=None, alias="endTime")


class OverlayDto(ApiModel):
    id: str
    kind: str
    label: str
    style_token: str = Field(alias="styleToken")
    source_strategy_id: str = Field(alias="sourceStrategyId")
    source_strategy_version: str = Field(alias="sourceStrategyVersion")
    points: tuple[OverlayPointDto, ...] = ()


class MarkerDto(ApiModel):
    id: str
    type: str
    time: str
    price: str | None
    label: str
    shape: str
    tone: str | None = None
    source_strategy_id: str = Field(alias="sourceStrategyId")
    source_strategy_version: str = Field(alias="sourceStrategyVersion")
    signal_id: str | None = Field(default=None, alias="signalId")
    trade_id: str | None = Field(default=None, alias="tradeId")


class UnalignedMarkerDto(ApiModel):
    marker: MarkerDto
    reason: str


class VisualizationDataDto(ApiModel):
    pair: str
    timeframe: str
    start_time: str = Field(alias="startTime")
    end_time: str = Field(alias="endTime")
    availability: VisualizationAvailabilityDto
    candles: tuple[CandleDto, ...]
    overlays: tuple[OverlayDto, ...]
    markers: tuple[MarkerDto, ...]
    unaligned_markers: tuple[UnalignedMarkerDto, ...] = Field(alias="unalignedMarkers")


class TradeDto(ApiModel):
    trade_id: str = Field(alias="tradeId")
    entry_signal_id: str | None = Field(default=None, alias="entrySignalId")
    exit_signal_id: str | None = Field(default=None, alias="exitSignalId")
    entry_time: str = Field(alias="entryTime")
    entry_price: str = Field(alias="entryPrice")
    exit_time: str = Field(alias="exitTime")
    exit_price: str = Field(alias="exitPrice")
    side: str
    quantity: str
    profit_loss: str = Field(alias="profitLoss")
    return_percent: str = Field(alias="returnPercent")


class TradePageDto(ApiModel):
    items: tuple[TradeDto, ...]
    pagination: PageMetaDto


class LeaderboardChangedSetDto(ApiModel):
    added_evaluation_result_ids: tuple[str, ...] = Field(alias="addedEvaluationResultIds")
    removed_evaluation_result_ids: tuple[str, ...] = Field(alias="removedEvaluationResultIds")
    moved_evaluation_result_ids: tuple[str, ...] = Field(alias="movedEvaluationResultIds")


class LeaderboardTopOneDto(ApiModel):
    evaluation_result_id: str = Field(alias="evaluationResultId")
    strategy_id: str = Field(alias="strategyId")
    strategy_version: str = Field(alias="strategyVersion")
    rank: int
    score: str


class LeaderboardUpdatedPayloadDto(ApiModel):
    leaderboard_id: str = Field(alias="leaderboardId")
    scope_key: str = Field(alias="scopeKey")
    scoring_policy_id: str = Field(alias="scoringPolicyId")
    scoring_policy_version: str = Field(alias="scoringPolicyVersion")
    rank_by: str = Field(alias="rankBy")
    k: int
    projection_version: int = Field(alias="projectionVersion")
    updated_at: str = Field(alias="updatedAt")
    entry_count: int = Field(alias="entryCount")
    changed: LeaderboardChangedSetDto
    top_one: LeaderboardTopOneDto | None = Field(default=None, alias="topOne")
    run_state: str | None = Field(default=None, alias="runState")


class LeaderboardUpdatedEventDto(ApiModel):
    event_type: Literal["LEADERBOARD_UPDATED"] = Field(
        default="LEADERBOARD_UPDATED", alias="eventType"
    )
    version: Literal[1] = 1
    event_id: str = Field(alias="eventId")
    occurred_at: str = Field(alias="occurredAt")
    request_id: str | None = Field(default=None, alias="requestId")
    run_id: str | None = Field(default=None, alias="runId")
    job_id: str | None = Field(default=None, alias="jobId")
    payload: LeaderboardUpdatedPayloadDto


class LeaderboardSubscribePayload(ApiModel):
    scoring_policy_id: str = Field(alias="scoringPolicyId")
    scoring_policy_version: str = Field(alias="scoringPolicyVersion")
    rank_by: str = Field(alias="rankBy")
    k: int = 10
    pair: str | None = None
    timeframe: str | None = None
    run_id: str | None = Field(default=None, alias="runId")
    last_projection_version: int | None = Field(default=None, alias="lastProjectionVersion")


class LeaderboardSubscribeMessage(ApiModel):
    event_type: str = Field(alias="eventType")
    version: int = 1
    request_id: str | None = Field(default=None, alias="requestId")
    payload: LeaderboardSubscribePayload


class EventErrorPayloadDto(ApiModel):
    code: str
    message: str
    request_id: str | None = Field(default=None, alias="requestId")


class EventErrorDto(ApiModel):
    event_type: Literal["ERROR"] = Field(default="ERROR", alias="eventType")
    version: Literal[1] = 1
    payload: EventErrorPayloadDto


ANALYSIS_DISCLAIMER = (
    "Simulated historical analysis only. Past simulated performance is not investment "
    "advice and does not guarantee future results."
)


def metric_descriptor_to_dto(descriptor: MetricDescriptor) -> MetricDescriptorDto:
    return MetricDescriptorDto(
        metric=descriptor.metric.value,
        direction=descriptor.direction.value,
        unit=descriptor.unit.value,
    )


def entry_to_dto(entry: EntryView) -> LeaderboardEntryDto:
    candidate = entry.candidate
    metrics = candidate.metrics
    return LeaderboardEntryDto(
        evaluationResultId=str(candidate.evaluation_result_id),
        rank=entry.rank,
        projectionVersion=entry.projection_version,
        score=canonical_decimal(metrics.score),
        strategy=StrategySummaryDto(
            strategyId=candidate.strategy.strategy_id,
            strategyVersion=candidate.strategy.strategy_version,
            displayName=candidate.strategy.display_name,
            members=tuple(
                StrategyMemberDto(
                    strategyId=member.strategy_id,
                    strategyVersion=member.strategy_version,
                    displayName=member.display_name,
                )
                for member in candidate.strategy.members
            ),
        ),
        pair=candidate.pair,
        timeframe=candidate.timeframe.value,
        datasetId=str(candidate.dataset_id),
        startTime=_instant(candidate.start_time),
        endTime=_instant(candidate.end_time),
        metrics=MetricSetDto(
            totalReturn=canonical_decimal(metrics.total_return),
            winRate=canonical_decimal(metrics.win_rate),
            maxDrawdown=canonical_decimal(metrics.max_drawdown),
            numberOfTrades=metrics.number_of_trades,
            sharpeRatio=_decimal(metrics.sharpe_ratio),
        ),
        scoringPolicyId=candidate.policy.policy_id,
        scoringPolicyVersion=candidate.policy.version,
        updatedAt=_instant(entry.updated_at),
    )


def page_to_dto(page: LeaderboardPage) -> LeaderboardSnapshotDto:
    return LeaderboardSnapshotDto(
        leaderboardId=str(page.leaderboard_id),
        scopeKey=page.scope_key,
        scoringPolicyId=page.policy.policy_id,
        scoringPolicyVersion=page.policy.version,
        rankBy=page.rank_metric.value,
        k=page.k,
        projectionVersion=page.projection_version,
        updatedAt=_instant(page.updated_at),
        runState=page.run_state.value if page.run_state else None,
        metricMetadata=tuple(metric_descriptor_to_dto(item) for item in page.metric_metadata),
        entries=tuple(entry_to_dto(entry) for entry in page.entries),
        pagination=PageMetaDto(page=page.page, pageSize=page.page_size, total=page.total),
        disclaimer=ANALYSIS_DISCLAIMER,
    )


def availability_to_dto(availability: Availability) -> AvailabilityDto:
    return AvailabilityDto(
        state=availability.state.value,
        count=availability.count,
        reason=availability.reason,
    )


def visualization_availability_to_dto(
    availability: VisualizationAvailability,
) -> VisualizationAvailabilityDto:
    return VisualizationAvailabilityDto(
        candles=availability_to_dto(availability.candles),
        overlays=availability_to_dto(availability.overlays),
        signals=availability_to_dto(availability.signals),
        trades=availability_to_dto(availability.trades),
    )


def provenance_to_dto(provenance: Provenance) -> ProvenanceDto:
    return ProvenanceDto(
        evaluationResultId=str(provenance.evaluation_result_id),
        backtestResultId=str(provenance.backtest_result_id),
        runId=str(provenance.run_id),
        jobId=str(provenance.job_id),
        strategyId=provenance.strategy_id,
        strategyVersion=provenance.strategy_version,
        datasetId=str(provenance.dataset_id),
        executionConfig=provenance.execution_config,
        resultChecksum=provenance.result_checksum,
        scoringPolicyId=provenance.scoring_policy_id,
        scoringPolicyVersion=provenance.scoring_policy_version,
    )


def detail_to_dto(view: RankedResultView) -> RankedResultDetailDto:
    return RankedResultDetailDto(
        entry=entry_to_dto(view.entry),
        provenance=provenance_to_dto(view.provenance),
        candles=availability_to_dto(view.availability.candles),
        overlays=availability_to_dto(view.availability.overlays),
        signals=availability_to_dto(view.availability.signals),
        trades=availability_to_dto(view.availability.trades),
        disclaimer=ANALYSIS_DISCLAIMER,
    )


def marker_to_dto(marker: MarkerView) -> MarkerDto:
    return MarkerDto(
        id=marker.id,
        type=marker.type.value,
        time=_instant(marker.time),
        price=_decimal(marker.price),
        label=marker.label,
        shape=marker.shape.value,
        tone=marker.tone.value if marker.tone else None,
        sourceStrategyId=marker.source_strategy_id,
        sourceStrategyVersion=marker.source_strategy_version,
        signalId=str(marker.signal_id) if marker.signal_id else None,
        tradeId=str(marker.trade_id) if marker.trade_id else None,
    )


def overlay_to_dto(overlay: OverlayView) -> OverlayDto:
    return OverlayDto(
        id=overlay.id,
        kind=overlay.kind.value,
        label=overlay.label,
        styleToken=overlay.style_token,
        sourceStrategyId=overlay.source_strategy_id,
        sourceStrategyVersion=overlay.source_strategy_version,
        points=tuple(
            OverlayPointDto(
                time=_instant(point.time) if point.time else None,
                value=_decimal(point.value),
                upper=_decimal(point.upper),
                middle=_decimal(point.middle),
                lower=_decimal(point.lower),
                startTime=_instant(point.start_time) if point.start_time else None,
                endTime=_instant(point.end_time) if point.end_time else None,
            )
            for point in overlay.points
        ),
    )


def visualization_to_dto(view: VisualizationView) -> VisualizationDataDto:
    return VisualizationDataDto(
        pair=view.pair,
        timeframe=view.timeframe,
        startTime=_instant(view.start_time),
        endTime=_instant(view.end_time),
        availability=visualization_availability_to_dto(view.availability),
        candles=tuple(
            CandleDto(
                openTime=_instant(candle.open_time),
                open=canonical_decimal(candle.open),
                high=canonical_decimal(candle.high),
                low=canonical_decimal(candle.low),
                close=canonical_decimal(candle.close),
                volume=canonical_decimal(candle.volume),
            )
            for candle in view.candles
        ),
        overlays=tuple(overlay_to_dto(overlay) for overlay in view.overlays),
        markers=tuple(marker_to_dto(marker) for marker in view.markers),
        unalignedMarkers=tuple(
            UnalignedMarkerDto(marker=marker_to_dto(item.marker), reason=item.reason)
            for item in view.unaligned_markers
        ),
    )


def trade_page_to_dto(page: TradePage) -> TradePageDto:
    return TradePageDto(
        items=tuple(
            TradeDto(
                tradeId=str(trade.trade_id),
                entrySignalId=str(trade.entry_signal_id) if trade.entry_signal_id else None,
                exitSignalId=str(trade.exit_signal_id) if trade.exit_signal_id else None,
                entryTime=_instant(trade.entry_time),
                entryPrice=canonical_decimal(trade.entry_price),
                exitTime=_instant(trade.exit_time),
                exitPrice=canonical_decimal(trade.exit_price),
                side=trade.side,
                quantity=canonical_decimal(trade.quantity),
                profitLoss=canonical_decimal(trade.profit_loss),
                returnPercent=canonical_decimal(trade.return_percent),
            )
            for trade in page.items
        ),
        pagination=PageMetaDto(page=page.page, pageSize=page.page_size, total=page.total),
    )


def event_to_dto(event: LeaderboardUpdatedEvent) -> LeaderboardUpdatedEventDto:
    top_one = None
    if event.top_one is not None:
        top_one = LeaderboardTopOneDto(
            evaluationResultId=event.top_one["evaluationResultId"],
            strategyId=event.top_one["strategyId"],
            strategyVersion=event.top_one["strategyVersion"],
            rank=int(event.top_one["rank"]),
            score=event.top_one["score"],
        )
    return LeaderboardUpdatedEventDto(
        eventId=str(event.event_id),
        occurredAt=_instant(event.occurred_at),
        requestId=event.request_id,
        runId=str(event.run_id) if event.run_id else None,
        jobId=str(event.job_id) if event.job_id else None,
        payload=LeaderboardUpdatedPayloadDto(
            leaderboardId=str(event.leaderboard_id),
            scopeKey=event.scope_key,
            scoringPolicyId=event.policy.policy_id,
            scoringPolicyVersion=event.policy.version,
            rankBy=event.rank_metric.value,
            k=event.k,
            projectionVersion=event.projection_version,
            updatedAt=_instant(event.updated_at),
            entryCount=event.entry_count,
            changed=LeaderboardChangedSetDto(
                addedEvaluationResultIds=tuple(str(item) for item in event.added),
                removedEvaluationResultIds=tuple(str(item) for item in event.removed),
                movedEvaluationResultIds=tuple(str(item) for item in event.moved),
            ),
            topOne=top_one,
            runState=event.run_state.value if event.run_state else None,
        ),
    )
