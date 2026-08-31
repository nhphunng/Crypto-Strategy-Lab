"""Ranked-result provenance, bounded visualization, and pageable Trade reads."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from crypto_lab.application.leaderboard.errors import entry_not_found, range_invalid
from crypto_lab.application.leaderboard.ports import (
    RankedResultReader,
    RankedResultView,
    TradePage,
    VisualizationView,
)
from crypto_lab.application.leaderboard.query_leaderboard import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
)
from crypto_lab.domain.market_data.timeframe import Timeframe, require_utc

MAX_VISUALIZATION_INTERVALS = 5000
TRADE_SORT_FIELDS = ("ENTRY_TIME", "EXIT_TIME", "RETURN_PERCENT")


class GetRankedResult:
    """Compose one ranked result without recomputing any upstream value."""

    def __init__(self, reader: RankedResultReader) -> None:
        self._reader = reader

    async def detail(self, leaderboard_id: UUID, evaluation_result_id: UUID) -> RankedResultView:
        view = await self._reader.read_detail(leaderboard_id, evaluation_result_id)
        if view is None:
            raise entry_not_found(
                leaderboardId=str(leaderboard_id),
                evaluationResultId=str(evaluation_result_id),
            )
        return view

    async def visualization(
        self,
        leaderboard_id: UUID,
        evaluation_result_id: UUID,
        start_time: datetime,
        end_time: datetime,
    ) -> VisualizationView:
        detail = await self.detail(leaderboard_id, evaluation_result_id)
        timeframe = detail.entry.candidate.timeframe
        self._validate_range(start_time, end_time, timeframe)
        view = await self._reader.read_visualization(
            leaderboard_id,
            evaluation_result_id,
            start_time,
            end_time,
        )
        if view is None:  # pragma: no cover - detail lookup already guarded
            raise entry_not_found(
                leaderboardId=str(leaderboard_id),
                evaluationResultId=str(evaluation_result_id),
            )
        return view

    async def trades(
        self,
        leaderboard_id: UUID,
        evaluation_result_id: UUID,
        *,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        sort_by: str = "ENTRY_TIME",
        sort_direction: str = "ASC",
    ) -> TradePage:
        if page < 1:
            raise range_invalid("page must be 1 or greater.", page=page)
        if not 1 <= page_size <= MAX_PAGE_SIZE:
            raise range_invalid("pageSize must be between 1 and 200.", pageSize=page_size)
        if sort_by not in TRADE_SORT_FIELDS:
            raise range_invalid("Unsupported Trade sort field.", sortBy=sort_by)
        if sort_direction not in ("ASC", "DESC"):
            raise range_invalid("Unsupported sort direction.", sortDirection=sort_direction)
        view = await self._reader.read_trades(
            leaderboard_id,
            evaluation_result_id,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )
        if view is None:
            raise entry_not_found(
                leaderboardId=str(leaderboard_id),
                evaluationResultId=str(evaluation_result_id),
            )
        return view

    @staticmethod
    def _validate_range(start_time: datetime, end_time: datetime, timeframe: Timeframe) -> None:
        start = require_utc(start_time)
        end = require_utc(end_time)
        if end <= start:
            raise range_invalid("endTime must be after startTime.")
        intervals = (end - start).total_seconds() / timeframe.seconds
        if intervals > MAX_VISUALIZATION_INTERVALS:
            raise range_invalid(
                "The requested range exceeds the bounded visualization window.",
                maxIntervals=MAX_VISUALIZATION_INTERVALS,
                timeframe=timeframe.value,
            )
