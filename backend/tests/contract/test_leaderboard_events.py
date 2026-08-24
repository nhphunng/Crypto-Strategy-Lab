"""WebSocket contract: subscription identity, v1 envelope, and error events."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import WebSocketDisconnect

from crypto_lab.api.schemas.leaderboards import event_to_dto
from crypto_lab.api.websocket.leaderboard_channel import (
    MAX_SUBSCRIPTIONS_PER_CONNECTION,
    LeaderboardEventHub,
    SubscriptionInvalid,
    leaderboard_channel,
    matches,
    parse_subscription,
)
from crypto_lab.application.leaderboard.errors import (
    LEADERBOARD_SUBSCRIPTION_INVALID,
    LEADERBOARD_SUBSCRIPTION_LIMITED,
)
from crypto_lab.application.leaderboard.ports import LeaderboardUpdatedEvent, RunState
from crypto_lab.domain.leaderboard.policy import RankMetric, ScoringPolicyRef


def subscribe_message(**payload: object) -> dict[str, object]:
    body: dict[str, object] = {
        "scoringPolicyId": "balanced",
        "scoringPolicyVersion": "2",
        "rankBy": "OVERALL_SCORE",
        "k": 10,
        "pair": "BTCUSDT",
        "timeframe": "15m",
        "runId": None,
        "lastProjectionVersion": 41,
    }
    body.update(payload)
    return {
        "eventType": "LEADERBOARD_SUBSCRIBE",
        "version": 1,
        "requestId": "req-1",
        "payload": body,
    }


def event(**overrides: object) -> LeaderboardUpdatedEvent:
    values: dict[str, object] = {
        "event_id": UUID(int=7),
        "leaderboard_id": UUID(int=8),
        "scope_key": "pair:BTCUSDT|timeframe:15m|run:*",
        "policy": ScoringPolicyRef("balanced", "2"),
        "rank_metric": RankMetric.OVERALL_SCORE,
        "k": 10,
        "projection_version": 42,
        "updated_at": datetime(2026, 8, 13, 3, 30, tzinfo=UTC),
        "occurred_at": datetime(2026, 8, 13, 3, 30, tzinfo=UTC),
        "entry_count": 10,
        "added": (UUID(int=1),),
        "removed": (),
        "moved": (UUID(int=2),),
        "top_one": {
            "evaluationResultId": str(UUID(int=1)),
            "strategyId": "ma-rsi-sr",
            "strategyVersion": "3",
            "rank": "1",
            "score": "82.1",
        },
        "run_state": RunState.RUNNING,
        "run_id": UUID(int=3),
        "job_id": UUID(int=4),
        "request_id": "req-1",
    }
    values.update(overrides)
    return LeaderboardUpdatedEvent(**values)  # type: ignore[arg-type]


def test_subscription_requires_the_complete_ranking_definition() -> None:
    key = parse_subscription(subscribe_message())

    assert key.scope_key == "pair:BTCUSDT|timeframe:15m|run:*"
    assert key.rank_metric is RankMetric.OVERALL_SCORE
    assert key.k == 10


@pytest.mark.parametrize(
    "message",
    [
        subscribe_message(k=0),
        subscribe_message(k=500),
        subscribe_message(rankBy="PROFIT"),
        subscribe_message(timeframe="3m"),
        subscribe_message(runId="not-a-uuid"),
        {"eventType": "LEADERBOARD_SUBSCRIBE", "version": 2, "payload": {}},
        {"eventType": "SOMETHING_ELSE", "version": 1, "payload": {}},
        {},
    ],
)
def test_invalid_subscription_is_rejected(message: dict[str, object]) -> None:
    with pytest.raises(SubscriptionInvalid) as error:
        parse_subscription(message)

    assert error.value.code == LEADERBOARD_SUBSCRIPTION_INVALID


def test_subscription_limit_is_enforced_per_connection() -> None:
    hub = LeaderboardEventHub()
    connection = hub.connect()
    for index in range(MAX_SUBSCRIPTIONS_PER_CONNECTION):
        connection.subscribe(parse_subscription(subscribe_message(k=index + 1)))

    with pytest.raises(SubscriptionInvalid) as error:
        connection.subscribe(parse_subscription(subscribe_message(k=100)))

    assert error.value.code == LEADERBOARD_SUBSCRIPTION_LIMITED


def test_repeated_identical_subscription_is_idempotent() -> None:
    hub = LeaderboardEventHub()
    connection = hub.connect()
    connection.subscribe(parse_subscription(subscribe_message()))
    connection.subscribe(parse_subscription(subscribe_message()))

    assert len(connection.subscriptions) == 1


def test_event_only_matches_its_exact_ranking_definition() -> None:
    key = parse_subscription(subscribe_message())

    assert matches(key, event()) is True
    assert matches(key, event(k=5)) is False
    assert matches(key, event(rank_metric=RankMetric.TOTAL_RETURN)) is False
    assert matches(key, event(policy=ScoringPolicyRef("balanced", "1"))) is False
    assert matches(key, event(scope_key="pair:ETHUSDT|timeframe:15m|run:*")) is False


async def test_hub_delivers_matching_events_only() -> None:
    hub = LeaderboardEventHub()
    watcher = hub.connect()
    bystander = hub.connect()
    watcher.subscribe(parse_subscription(subscribe_message()))
    bystander.subscribe(parse_subscription(subscribe_message(k=5)))

    await hub.publish(event())

    assert watcher.queue.qsize() == 1
    assert bystander.queue.qsize() == 0
    delivered = await asyncio.wait_for(watcher.queue.get(), timeout=1)
    assert delivered.projection_version == 42


def test_event_envelope_matches_the_v1_contract() -> None:
    payload = event_to_dto(event()).model_dump(by_alias=True, mode="json")

    assert payload["eventType"] == "LEADERBOARD_UPDATED"
    assert payload["version"] == 1
    assert payload["eventId"] == str(UUID(int=7))
    assert payload["occurredAt"].endswith("Z")
    assert payload["runId"] == str(UUID(int=3))
    assert payload["jobId"] == str(UUID(int=4))
    body = payload["payload"]
    assert body["projectionVersion"] == 42
    assert body["entryCount"] == 10
    assert body["rankBy"] == "OVERALL_SCORE"
    assert body["scoringPolicyVersion"] == "2"
    assert body["changed"]["addedEvaluationResultIds"] == [str(UUID(int=1))]
    assert body["changed"]["movedEvaluationResultIds"] == [str(UUID(int=2))]
    assert body["changed"]["removedEvaluationResultIds"] == []
    assert body["topOne"]["score"] == "82.1"
    assert body["runState"] == "RUNNING"


def test_event_without_a_top_one_still_serializes() -> None:
    payload = event_to_dto(event(top_one=None, run_state=None)).model_dump(
        by_alias=True, mode="json"
    )

    assert payload["payload"]["topOne"] is None
    assert payload["payload"]["runState"] is None


def test_events_carry_no_database_or_secret_details() -> None:
    payload = event_to_dto(event()).model_dump(by_alias=True, mode="json")
    rendered = str(payload).lower()

    for forbidden in ("password", "postgres", "traceback", "select ", "sqlalchemy"):
        assert forbidden not in rendered


async def test_disconnected_connection_stops_receiving_events() -> None:
    hub = LeaderboardEventHub()
    connection = hub.connect()
    connection.subscribe(parse_subscription(subscribe_message()))
    connection.close()

    await hub.publish(event(event_id=uuid4()))

    assert hub.connection_count == 0
    assert connection.queue.qsize() == 0


class FakeWebSocket:
    """Minimal transport double so the channel handler can be exercised."""

    def __init__(self, hub: LeaderboardEventHub, messages: list[dict[str, object]]) -> None:
        self.app = SimpleNamespace(
            state=SimpleNamespace(container=SimpleNamespace(leaderboard=SimpleNamespace(hub=hub)))
        )
        self._incoming = list(messages)
        self.sent: list[dict[str, object]] = []
        self.accepted = False

    async def accept(self) -> None:
        self.accepted = True

    async def receive_json(self) -> dict[str, object]:
        if not self._incoming:
            raise WebSocketDisconnect(1000)
        return self._incoming.pop(0)

    async def send_json(self, payload: dict[str, object]) -> None:
        self.sent.append(payload)


async def test_channel_acknowledges_a_valid_subscription() -> None:
    hub = LeaderboardEventHub()
    socket = FakeWebSocket(hub, [subscribe_message()])

    await leaderboard_channel(socket)  # type: ignore[arg-type]

    assert socket.accepted is True
    assert socket.sent[0]["eventType"] == "LEADERBOARD_SUBSCRIBED"
    assert socket.sent[0]["payload"]["k"] == 10
    assert hub.connection_count == 0


async def test_channel_returns_an_error_event_for_an_invalid_scope() -> None:
    hub = LeaderboardEventHub()
    socket = FakeWebSocket(hub, [subscribe_message(rankBy="PROFIT")])

    await leaderboard_channel(socket)  # type: ignore[arg-type]

    assert socket.sent[0]["eventType"] == "ERROR"
    assert socket.sent[0]["payload"]["code"] == LEADERBOARD_SUBSCRIPTION_INVALID
    assert socket.sent[0]["payload"]["requestId"] == "req-1"
