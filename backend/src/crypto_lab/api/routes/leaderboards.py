"""Thin REST boundary for the leaderboard projection."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from crypto_lab.api.common import SuccessEnvelope, success_envelope
from crypto_lab.api.leaderboard_dependencies import (
    LeaderboardContainer,
    leaderboard_container,
)
from crypto_lab.api.middleware import request_id
from crypto_lab.api.schemas.leaderboards import (
    LeaderboardSnapshotDto,
    RankedResultDetailDto,
    TradePageDto,
    VisualizationDataDto,
    detail_to_dto,
    page_to_dto,
    trade_page_to_dto,
    visualization_to_dto,
)
from crypto_lab.application.leaderboard.errors import query_invalid, range_invalid
from crypto_lab.application.leaderboard.query_leaderboard import (
    DEFAULT_PAGE_SIZE,
    LeaderboardQuery,
    MetricFilters,
)
from crypto_lab.domain.leaderboard.policy import (
    DEFAULT_K,
    LeaderboardIdentity,
    LeaderboardScope,
    RankMetric,
    ScoringPolicyRef,
    SortDirection,
)
from crypto_lab.domain.market_data.timeframe import Timeframe

router = APIRouter(prefix="/api/v1/leaderboards", tags=["leaderboards"])

_PAIR = re.compile(r"^[A-Z0-9]{5,20}$")


def _decimal(value: str | None, field: str) -> Decimal | None:
    if value is None:
        return None
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as error:
        raise query_invalid("Metric filters must be decimal values.", field=field) from error
    if not parsed.is_finite():
        raise query_invalid("Metric filters must be finite.", field=field)
    return parsed


def _identity(
    scoring_policy_id: str,
    scoring_policy_version: str,
    rank_by: str,
    k: int,
    pair: str | None,
    timeframe: str | None,
    run_id: UUID | None,
) -> LeaderboardIdentity:
    if pair is not None and not _PAIR.fullmatch(pair):
        raise query_invalid("pair must be an uppercase market symbol.", pair=pair)
    resolved_timeframe: Timeframe | None = None
    if timeframe is not None:
        try:
            resolved_timeframe = Timeframe(timeframe)
        except ValueError as error:
            raise query_invalid("Unsupported timeframe.", timeframe=timeframe) from error
    try:
        metric = RankMetric(rank_by)
    except ValueError as error:
        raise query_invalid("Unsupported rankBy metric.", rankBy=rank_by) from error
    try:
        policy = ScoringPolicyRef(scoring_policy_id, scoring_policy_version)
        return LeaderboardIdentity(
            scope=LeaderboardScope(pair=pair, timeframe=resolved_timeframe, run_id=run_id),
            policy=policy,
            rank_metric=metric,
            k=k,
        )
    except ValueError as error:
        raise query_invalid(str(error), k=k) from error


@router.get("", response_model=SuccessEnvelope[LeaderboardSnapshotDto])
async def list_leaderboard_entries(
    request: Request,
    scoring_policy_id: str = Query(alias="scoringPolicyId"),
    scoring_policy_version: str = Query(alias="scoringPolicyVersion"),
    rank_by: str = Query(alias="rankBy"),
    k: int = Query(default=DEFAULT_K),
    pair: str | None = Query(default=None),
    timeframe: str | None = Query(default=None),
    run_id: UUID | None = Query(default=None, alias="runId"),
    min_score: str | None = Query(default=None, alias="minScore"),
    min_total_return: str | None = Query(default=None, alias="minTotalReturn"),
    min_win_rate: str | None = Query(default=None, alias="minWinRate"),
    max_drawdown: str | None = Query(default=None, alias="maxDrawdown"),
    min_sharpe_ratio: str | None = Query(default=None, alias="minSharpeRatio"),
    sort_by: str = Query(default="RANK", alias="sortBy"),
    sort_direction: str | None = Query(default=None, alias="sortDirection"),
    page: int = Query(default=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, alias="pageSize"),
    container: LeaderboardContainer = Depends(leaderboard_container),
) -> SuccessEnvelope[LeaderboardSnapshotDto]:
    identity = _identity(
        scoring_policy_id,
        scoring_policy_version,
        rank_by,
        k,
        pair,
        timeframe,
        run_id,
    )
    direction: SortDirection | None = None
    if sort_direction is not None:
        try:
            direction = SortDirection(sort_direction)
        except ValueError as error:
            raise query_invalid(
                "Unsupported sortDirection.",
                sortDirection=sort_direction,
            ) from error
    query = LeaderboardQuery(
        identity=identity,
        filters=MetricFilters(
            min_score=_decimal(min_score, "minScore"),
            min_total_return=_decimal(min_total_return, "minTotalReturn"),
            min_win_rate=_decimal(min_win_rate, "minWinRate"),
            max_drawdown=_decimal(max_drawdown, "maxDrawdown"),
            min_sharpe_ratio=_decimal(min_sharpe_ratio, "minSharpeRatio"),
        ),
        sort_by=sort_by,
        sort_direction=direction,
        page=page,
        page_size=page_size,
    )
    result = await container.queries.execute(query)
    return success_envelope(
        page_to_dto(result),
        "Leaderboard snapshot loaded.",
        request_id(request),
    )


@router.get(
    "/{leaderboard_id}/entries/{evaluation_result_id}",
    response_model=SuccessEnvelope[RankedResultDetailDto],
)
async def ranked_result_detail(
    request: Request,
    leaderboard_id: UUID,
    evaluation_result_id: UUID,
    container: LeaderboardContainer = Depends(leaderboard_container),
) -> SuccessEnvelope[RankedResultDetailDto]:
    view = await container.ranked_results.detail(leaderboard_id, evaluation_result_id)
    return success_envelope(
        detail_to_dto(view),
        "Ranked result detail loaded.",
        request_id(request),
    )


@router.get(
    "/{leaderboard_id}/entries/{evaluation_result_id}/visualization",
    response_model=SuccessEnvelope[VisualizationDataDto],
)
async def ranked_result_visualization(
    request: Request,
    leaderboard_id: UUID,
    evaluation_result_id: UUID,
    start_time: datetime = Query(alias="startTime"),
    end_time: datetime = Query(alias="endTime"),
    container: LeaderboardContainer = Depends(leaderboard_container),
) -> SuccessEnvelope[VisualizationDataDto]:
    view = await container.ranked_results.visualization(
        leaderboard_id,
        evaluation_result_id,
        _as_utc(start_time, "startTime"),
        _as_utc(end_time, "endTime"),
    )
    return success_envelope(
        visualization_to_dto(view),
        "Ranked result visualization loaded.",
        request_id(request),
    )


@router.get(
    "/{leaderboard_id}/entries/{evaluation_result_id}/trades",
    response_model=SuccessEnvelope[TradePageDto],
)
async def ranked_result_trades(
    request: Request,
    leaderboard_id: UUID,
    evaluation_result_id: UUID,
    page: int = Query(default=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, alias="pageSize"),
    sort_by: str = Query(default="ENTRY_TIME", alias="sortBy"),
    sort_direction: str = Query(default="ASC", alias="sortDirection"),
    container: LeaderboardContainer = Depends(leaderboard_container),
) -> SuccessEnvelope[TradePageDto]:
    view = await container.ranked_results.trades(
        leaderboard_id,
        evaluation_result_id,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
    return success_envelope(
        trade_page_to_dto(view),
        "Ranked result Trades loaded.",
        request_id(request),
    )


def _as_utc(value: datetime, field: str) -> datetime:
    if value.tzinfo is None:
        raise range_invalid("Timestamps must carry a UTC offset.", field=field)
    return value.astimezone(UTC)
