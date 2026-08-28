"""Functional regression test for the leaderboard drill-down user journey.

Walks the same sequence the frontend performs against the real API and a real
PostgreSQL database: load the Top-K snapshot, open the top-ranked result's
provenance, load its bounded visualization, then page through its Trades —
checking that every id and count returned along the way stays consistent with
what the earlier steps promised.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.fixtures.leaderboard import LeaderboardFixture

pytestmark = [pytest.mark.integration, pytest.mark.functional]


async def test_a_visitor_drills_from_the_snapshot_into_trades(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    snapshot_response = await leaderboard_client.get(
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
    assert snapshot_response.status_code == 200, snapshot_response.text
    snapshot = snapshot_response.json()["data"]
    assert snapshot["entries"], "the seeded fixture must qualify at least one candidate"

    top = snapshot["entries"][0]
    assert top["rank"] == 1
    assert top["evaluationResultId"] == str(seeded_leaderboard.top_one_evaluation_id)
    leaderboard_id = snapshot["leaderboardId"]

    detail_response = await leaderboard_client.get(
        f"/api/v1/leaderboards/{leaderboard_id}/entries/{top['evaluationResultId']}"
    )
    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()["data"]
    assert detail["entry"]["evaluationResultId"] == top["evaluationResultId"]
    assert detail["provenance"]["datasetId"] == str(seeded_leaderboard.dataset_id)

    start_time = seeded_leaderboard.start_time.isoformat().replace("+00:00", "Z")
    end_time = seeded_leaderboard.end_time.isoformat().replace("+00:00", "Z")
    visualization_response = await leaderboard_client.get(
        f"/api/v1/leaderboards/{leaderboard_id}/entries/{top['evaluationResultId']}/visualization",
        params={"startTime": start_time, "endTime": end_time},
    )
    assert visualization_response.status_code == 200, visualization_response.text
    visualization = visualization_response.json()["data"]
    assert visualization["candles"], "the drill-down chart must have Candle data to draw"

    trades_response = await leaderboard_client.get(
        f"/api/v1/leaderboards/{leaderboard_id}/entries/{top['evaluationResultId']}/trades",
        params={"pageSize": 1, "sortBy": "ENTRY_TIME", "sortDirection": "ASC"},
    )
    assert trades_response.status_code == 200, trades_response.text
    trades = trades_response.json()["data"]
    assert trades["pagination"]["total"] == detail["trades"]["count"]
    assert len(trades["items"]) == 1

    entry_markers = {
        marker["tradeId"]
        for marker in visualization["markers"]
        if marker["type"] == "ENTRY" and marker["tradeId"] is not None
    }
    assert trades["items"][0]["tradeId"] in entry_markers


async def test_a_no_trade_result_still_exposes_an_empty_but_valid_trades_page(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    snapshot_response = await leaderboard_client.get(
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
    leaderboard_id = snapshot_response.json()["data"]["leaderboardId"]
    no_trade_id = str(seeded_leaderboard.no_trade_evaluation_id)

    trades_response = await leaderboard_client.get(
        f"/api/v1/leaderboards/{leaderboard_id}/entries/{no_trade_id}/trades"
    )

    assert trades_response.status_code == 200, trades_response.text
    trades = trades_response.json()["data"]
    assert trades["items"] == []
    assert trades["pagination"]["total"] == 0
