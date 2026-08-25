"""REST contract for ranked-result detail, bounded visualization, and Trades."""

from __future__ import annotations

import re

import pytest
from httpx import AsyncClient

from tests.fixtures.leaderboard import LeaderboardFixture

pytestmark = pytest.mark.integration

DECIMAL = re.compile(r"^-?[0-9]+(\.[0-9]+)?$")
INSTANT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


async def leaderboard_id(client: AsyncClient, fixture: LeaderboardFixture) -> str:
    response = await client.get(
        "/api/v1/leaderboards",
        params={
            "scoringPolicyId": fixture.scoring_policy_id,
            "scoringPolicyVersion": fixture.scoring_policy_version,
            "rankBy": "OVERALL_SCORE",
            "pair": fixture.pair,
            "timeframe": fixture.timeframe,
            "k": 10,
        },
    )
    assert response.status_code == 200, response.text
    return str(response.json()["data"]["leaderboardId"])


async def test_detail_returns_complete_immutable_provenance(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    board = await leaderboard_id(leaderboard_client, seeded_leaderboard)

    response = await leaderboard_client.get(
        f"/api/v1/leaderboards/{board}/entries/{seeded_leaderboard.top_one_evaluation_id}"
    )
    data = response.json()["data"]

    assert response.status_code == 200
    assert data["entry"]["rank"] == 1
    provenance = data["provenance"]
    for field in (
        "evaluationResultId",
        "backtestResultId",
        "runId",
        "jobId",
        "strategyId",
        "strategyVersion",
        "datasetId",
        "executionConfig",
        "resultChecksum",
        "scoringPolicyId",
        "scoringPolicyVersion",
    ):
        assert provenance[field], field
    assert provenance["executionConfig"]["initialCapital"] == "10000"
    assert "not investment advice" in data["disclaimer"].lower()


async def test_detail_reports_availability_for_every_visualization_input(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    board = await leaderboard_id(leaderboard_client, seeded_leaderboard)

    response = await leaderboard_client.get(
        f"/api/v1/leaderboards/{board}/entries/{seeded_leaderboard.top_one_evaluation_id}"
    )
    data = response.json()["data"]

    assert data["candles"]["state"] == "AVAILABLE"
    assert data["signals"]["state"] == "AVAILABLE"
    assert data["trades"]["state"] == "AVAILABLE"
    assert data["overlays"]["state"] == "UNAVAILABLE"
    assert data["overlays"]["reason"]


async def test_no_trade_entry_reports_an_explicit_empty_trade_state(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    board = await leaderboard_id(leaderboard_client, seeded_leaderboard)

    response = await leaderboard_client.get(
        f"/api/v1/leaderboards/{board}/entries/{seeded_leaderboard.no_trade_evaluation_id}"
    )
    data = response.json()["data"]

    assert data["trades"]["state"] == "EMPTY"
    assert data["trades"]["reason"]
    assert data["signals"]["state"] == "AVAILABLE"


async def test_unknown_entry_returns_the_documented_not_found_code(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    board = await leaderboard_id(leaderboard_client, seeded_leaderboard)

    response = await leaderboard_client.get(
        f"/api/v1/leaderboards/{board}/entries/{seeded_leaderboard.ineligible_evaluation_id}"
    )
    body = response.json()

    assert response.status_code == 404
    assert body["error"]["code"] == "LEADERBOARD_ENTRY_NOT_FOUND"


async def test_visualization_returns_bounded_candles_and_aligned_markers(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    board = await leaderboard_id(leaderboard_client, seeded_leaderboard)

    response = await leaderboard_client.get(
        f"/api/v1/leaderboards/{board}/entries/{seeded_leaderboard.top_one_evaluation_id}"
        "/visualization",
        params={
            "startTime": "2026-07-01T00:00:00Z",
            "endTime": "2026-07-01T12:00:00Z",
        },
    )
    data = response.json()["data"]

    assert response.status_code == 200
    assert data["pair"] == seeded_leaderboard.pair
    assert data["timeframe"] == seeded_leaderboard.timeframe
    assert len(data["candles"]) == 49
    for candle in data["candles"]:
        assert INSTANT.fullmatch(candle["openTime"])
        assert DECIMAL.fullmatch(candle["close"])
    types = {marker["type"] for marker in data["markers"]}
    assert {"BUY", "SELL", "ENTRY", "EXIT"}.issubset(types)
    for marker in data["markers"]:
        assert marker["price"] is not None
        assert marker["label"]
        assert marker["shape"]
        assert marker["sourceStrategyVersion"] == "3"


async def test_entry_and_exit_markers_carry_the_trade_number_and_identity(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    board = await leaderboard_id(leaderboard_client, seeded_leaderboard)

    response = await leaderboard_client.get(
        f"/api/v1/leaderboards/{board}/entries/{seeded_leaderboard.top_one_evaluation_id}"
        "/visualization",
        params={"startTime": "2026-07-01T00:00:00Z", "endTime": "2026-07-02T00:00:00Z"},
    )
    markers = response.json()["data"]["markers"]

    entries = [marker for marker in markers if marker["type"] == "ENTRY"]
    exits = [marker for marker in markers if marker["type"] == "EXIT"]
    assert entries and exits
    assert entries[0]["label"].startswith("ENTRY #")
    assert exits[0]["label"].startswith("EXIT #")
    assert entries[0]["tradeId"] == exits[0]["tradeId"]
    assert entries[0]["shape"] != exits[0]["shape"]


async def test_unaligned_signal_is_reported_instead_of_being_moved(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    board = await leaderboard_id(leaderboard_client, seeded_leaderboard)

    response = await leaderboard_client.get(
        f"/api/v1/leaderboards/{board}/entries/{seeded_leaderboard.top_one_evaluation_id}"
        "/visualization",
        params={"startTime": "2026-07-01T00:00:00Z", "endTime": "2026-07-02T00:00:00Z"},
    )
    data = response.json()["data"]

    assert len(data["unalignedMarkers"]) == 1
    unaligned = data["unalignedMarkers"][0]
    assert unaligned["marker"]["price"] is None
    assert unaligned["reason"]
    aligned_times = {marker["time"] for marker in data["markers"]}
    assert unaligned["marker"]["time"] not in aligned_times


async def test_visualization_range_is_bounded(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    board = await leaderboard_id(leaderboard_client, seeded_leaderboard)
    url = (
        f"/api/v1/leaderboards/{board}/entries/{seeded_leaderboard.top_one_evaluation_id}"
        "/visualization"
    )

    oversized = await leaderboard_client.get(
        url, params={"startTime": "2020-01-01T00:00:00Z", "endTime": "2026-07-02T00:00:00Z"}
    )
    reversed_range = await leaderboard_client.get(
        url, params={"startTime": "2026-07-02T00:00:00Z", "endTime": "2026-07-01T00:00:00Z"}
    )

    assert oversized.status_code == 422
    assert oversized.json()["error"]["code"] == "LEADERBOARD_RANGE_INVALID"
    assert reversed_range.status_code == 422
    assert reversed_range.json()["error"]["code"] == "LEADERBOARD_RANGE_INVALID"


async def test_trades_are_pageable_and_sortable(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    board = await leaderboard_id(leaderboard_client, seeded_leaderboard)
    url = (
        f"/api/v1/leaderboards/{board}/entries/{seeded_leaderboard.top_one_evaluation_id}/trades"
    )

    first_page = await leaderboard_client.get(url, params={"page": 1, "pageSize": 2})
    descending = await leaderboard_client.get(
        url, params={"sortBy": "RETURN_PERCENT", "sortDirection": "DESC"}
    )
    data = first_page.json()["data"]

    assert data["pagination"] == {"page": 1, "pageSize": 2, "total": 4}
    assert len(data["items"]) == 2
    for trade in data["items"]:
        assert DECIMAL.fullmatch(trade["entryPrice"])
        assert DECIMAL.fullmatch(trade["returnPercent"])
        assert INSTANT.fullmatch(trade["entryTime"])
        assert trade["side"] == "LONG"
        assert trade["entrySignalId"]
    returns = [float(item["returnPercent"]) for item in descending.json()["data"]["items"]]
    assert returns == sorted(returns, reverse=True)


async def test_trade_page_beyond_the_result_set_is_empty(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    board = await leaderboard_id(leaderboard_client, seeded_leaderboard)

    response = await leaderboard_client.get(
        f"/api/v1/leaderboards/{board}/entries/{seeded_leaderboard.top_one_evaluation_id}/trades",
        params={"page": 9, "pageSize": 25},
    )
    data = response.json()["data"]

    assert data["items"] == []
    assert data["pagination"]["page"] == 9


async def test_no_trade_entry_returns_an_empty_trade_page(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    board = await leaderboard_id(leaderboard_client, seeded_leaderboard)

    response = await leaderboard_client.get(
        f"/api/v1/leaderboards/{board}/entries/{seeded_leaderboard.no_trade_evaluation_id}/trades"
    )
    data = response.json()["data"]

    assert data["items"] == []
    assert data["pagination"]["total"] == 0


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"pageSize": 500},
        {"sortBy": "PROFIT"},
        {"sortDirection": "SIDEWAYS"},
    ],
)
async def test_invalid_trade_query_is_rejected(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
    params: dict[str, object],
) -> None:
    board = await leaderboard_id(leaderboard_client, seeded_leaderboard)

    response = await leaderboard_client.get(
        f"/api/v1/leaderboards/{board}/entries/{seeded_leaderboard.top_one_evaluation_id}/trades",
        params=params,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "LEADERBOARD_RANGE_INVALID"
