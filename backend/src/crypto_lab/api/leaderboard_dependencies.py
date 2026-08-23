"""Feature 005 composition boundary.

Only wiring lives here: no ranking, evaluation, or presentation business rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import Request

from crypto_lab.application.leaderboard.get_ranked_result import GetRankedResult
from crypto_lab.application.leaderboard.ports import (
    LeaderboardRepository,
    RankedResultReader,
)
from crypto_lab.application.leaderboard.query_leaderboard import QueryLeaderboard
from crypto_lab.application.leaderboard.update_leaderboard import UpdateLeaderboard
from crypto_lab.infrastructure.database import Database
from crypto_lab.infrastructure.observability.leaderboard import LeaderboardMetrics
from crypto_lab.infrastructure.persistence.repositories.leaderboard_repository import (
    SqlAlchemyLeaderboardRepository,
    SqlAlchemyRankedResultReader,
)


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


@dataclass(slots=True)
class LeaderboardContainer:
    repository: LeaderboardRepository
    reader: RankedResultReader
    updater: UpdateLeaderboard
    queries: QueryLeaderboard
    ranked_results: GetRankedResult
    metrics: LeaderboardMetrics


def build_leaderboard_container(database: Database) -> LeaderboardContainer:
    repository = SqlAlchemyLeaderboardRepository(database.sessions)
    reader = SqlAlchemyRankedResultReader(database.sessions)
    updater = UpdateLeaderboard(repository, SystemClock())
    return LeaderboardContainer(
        repository=repository,
        reader=reader,
        updater=updater,
        queries=QueryLeaderboard(repository, updater),
        ranked_results=GetRankedResult(reader),
        metrics=LeaderboardMetrics(),
    )


def leaderboard_container(request: Request) -> LeaderboardContainer:
    container = request.app.state.container.leaderboard
    if not isinstance(container, LeaderboardContainer):  # pragma: no cover - config guard
        raise RuntimeError("leaderboard container is not configured")
    return container
