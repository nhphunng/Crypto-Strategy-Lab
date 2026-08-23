"""A new Strategy must rank and render without any strategy-name branch."""

from __future__ import annotations

import ast
import re
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from httpx import AsyncClient

from crypto_lab.infrastructure.database import Database
from tests.fixtures.leaderboard import CandidateSpec, _seed_candidate, _uuid

pytestmark = pytest.mark.integration

SOURCE = Path(__file__).parents[2] / "src" / "crypto_lab"

RANKING_AND_MAPPING_MODULES = (
    SOURCE / "domain" / "leaderboard" / "ranking.py",
    SOURCE / "domain" / "leaderboard" / "policy.py",
    SOURCE / "domain" / "leaderboard" / "entry.py",
    SOURCE / "application" / "leaderboard" / "update_leaderboard.py",
    SOURCE / "application" / "leaderboard" / "query_leaderboard.py",
    SOURCE / "application" / "leaderboard" / "get_ranked_result.py",
    SOURCE / "api" / "schemas" / "leaderboards.py",
    SOURCE / "api" / "routes" / "leaderboards.py",
    SOURCE / "infrastructure" / "persistence" / "repositories" / "leaderboard_repository.py",
)

CONCRETE_STRATEGY_TERMS = (
    "moving_average",
    "movingaverage",
    "ma_cross",
    "rsi",
    "macd",
    "bollinger",
    "sentiment",
    "support_resistance",
)

UNKNOWN_STRATEGY = CandidateSpec(
    30,
    "future-unknown-strategy",
    Decimal("97.5"),
    Decimal("52.3"),
    Decimal("66.0"),
    Decimal("9.8"),
    2,
    Decimal("2.8"),
)


def test_ranking_and_mapping_contain_no_concrete_strategy_branch() -> None:
    for path in RANKING_AND_MAPPING_MODULES:
        text = path.read_text(encoding="utf-8").lower()
        for term in CONCRETE_STRATEGY_TERMS:
            pattern = re.compile(rf"{re.escape(term)}")
            assert not pattern.search(text), f"{path.name} mentions {term}"


def test_leaderboard_modules_never_compare_a_strategy_identifier() -> None:
    """A `strategy_id == "..."` comparison would defeat the extension contract."""

    for path in RANKING_AND_MAPPING_MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            rendered = ast.unparse(node)
            if "strategy_id" in rendered and any(
                isinstance(item, ast.Constant) and isinstance(item.value, str)
                for item in node.comparators
            ):
                raise AssertionError(f"{path.name} branches on a strategy name: {rendered}")


async def test_unknown_strategy_ranks_through_the_same_contract(
    leaderboard_database: Database,
    leaderboard_client: AsyncClient,
    seeded_leaderboard,
) -> None:
    async with leaderboard_database.sessions() as session, session.begin():
        await _seed_candidate(session, UNKNOWN_STRATEGY, _uuid("execution-policy"))

    response = await leaderboard_client.get(
        "/api/v1/leaderboards",
        params={
            "scoringPolicyId": seeded_leaderboard.scoring_policy_id,
            "scoringPolicyVersion": seeded_leaderboard.scoring_policy_version,
            "rankBy": "OVERALL_SCORE",
            "pair": seeded_leaderboard.pair,
            "timeframe": seeded_leaderboard.timeframe,
            "k": 10,
        },
    )
    data = response.json()["data"]
    top = data["entries"][0]

    assert response.status_code == 200
    assert top["strategy"]["strategyId"] == UNKNOWN_STRATEGY.strategy_id
    assert top["rank"] == 1
    assert top["metrics"]["totalReturn"] == "52.3"
    assert top["strategy"]["members"], "composition is read generically from the definition"


async def test_unknown_strategy_visualization_uses_the_generic_marker_contract(
    leaderboard_database: Database,
    leaderboard_client: AsyncClient,
    seeded_leaderboard,
) -> None:
    async with leaderboard_database.sessions() as session, session.begin():
        await _seed_candidate(session, UNKNOWN_STRATEGY, _uuid("execution-policy"))
    snapshot = await leaderboard_client.get(
        "/api/v1/leaderboards",
        params={
            "scoringPolicyId": seeded_leaderboard.scoring_policy_id,
            "scoringPolicyVersion": seeded_leaderboard.scoring_policy_version,
            "rankBy": "OVERALL_SCORE",
            "pair": seeded_leaderboard.pair,
            "timeframe": seeded_leaderboard.timeframe,
            "k": 10,
        },
    )
    board = snapshot.json()["data"]["leaderboardId"]
    evaluation_id: UUID = UNKNOWN_STRATEGY.evaluation_id

    response = await leaderboard_client.get(
        f"/api/v1/leaderboards/{board}/entries/{evaluation_id}/visualization",
        params={
            "startTime": datetime(2026, 7, 1, tzinfo=UTC).isoformat(),
            "endTime": datetime(2026, 7, 2, tzinfo=UTC).isoformat(),
        },
    )
    data = response.json()["data"]

    assert response.status_code == 200
    assert data["markers"]
    for marker in data["markers"]:
        assert marker["type"] in {"BUY", "SELL", "HOLD", "ENTRY", "EXIT"}
        assert marker["sourceStrategyId"] == UNKNOWN_STRATEGY.strategy_id
        assert marker["label"] and marker["shape"]
