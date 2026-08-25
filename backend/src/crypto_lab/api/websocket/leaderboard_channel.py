"""Versioned `/ws/v1/leaderboards` subscription and event delivery."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from crypto_lab.api.schemas.leaderboards import (
    EventErrorDto,
    EventErrorPayloadDto,
    LeaderboardSubscribeMessage,
    event_to_dto,
)
from crypto_lab.application.leaderboard.errors import (
    LEADERBOARD_SUBSCRIPTION_INVALID,
    LEADERBOARD_SUBSCRIPTION_LIMITED,
)
from crypto_lab.application.leaderboard.ports import LeaderboardUpdatedEvent
from crypto_lab.domain.leaderboard.policy import (
    MAX_K,
    MIN_K,
    LeaderboardScope,
    RankMetric,
    ScoringPolicyRef,
)
from crypto_lab.domain.market_data.timeframe import Timeframe

logger = logging.getLogger("crypto_lab.leaderboard.ws")

router = APIRouter()

MAX_SUBSCRIPTIONS_PER_CONNECTION = 8
QUEUE_SIZE = 100


class SubscriptionInvalid(ValueError):
    def __init__(self, message: str, code: str = LEADERBOARD_SUBSCRIPTION_INVALID) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class SubscriptionKey:
    """Complete ranking definition a client is watching."""

    scope_key: str
    scoring_policy_id: str
    scoring_policy_version: str
    rank_metric: RankMetric
    k: int


def parse_subscription(message: dict[str, Any]) -> SubscriptionKey:
    """Validate a subscription request against the v1 event contract."""

    try:
        parsed = LeaderboardSubscribeMessage.model_validate(message)
    except ValidationError as error:
        raise SubscriptionInvalid("The subscription payload is invalid.") from error
    if parsed.event_type != "LEADERBOARD_SUBSCRIBE":
        raise SubscriptionInvalid("Unsupported subscription message type.")
    if parsed.version != 1:
        raise SubscriptionInvalid("Unsupported subscription version.")
    payload = parsed.payload
    if not MIN_K <= payload.k <= MAX_K:
        raise SubscriptionInvalid("k must be between 1 and 200.")
    try:
        metric = RankMetric(payload.rank_by)
        policy = ScoringPolicyRef(payload.scoring_policy_id, payload.scoring_policy_version)
        scope = LeaderboardScope(
            pair=payload.pair,
            timeframe=Timeframe(payload.timeframe) if payload.timeframe else None,
            run_id=UUID(payload.run_id) if payload.run_id else None,
        )
    except ValueError as error:
        raise SubscriptionInvalid("The subscription scope is not supported.") from error
    return SubscriptionKey(
        scope_key=scope.scope_key,
        scoring_policy_id=policy.policy_id,
        scoring_policy_version=policy.version,
        rank_metric=metric,
        k=payload.k,
    )


def matches(key: SubscriptionKey, event: LeaderboardUpdatedEvent) -> bool:
    """An event reaches only the exact ranking definition it belongs to."""

    return (
        key.scope_key == event.scope_key
        and key.scoring_policy_id == event.policy.policy_id
        and key.scoring_policy_version == event.policy.version
        and key.rank_metric == event.rank_metric
        and key.k == event.k
    )


class LeaderboardEventHub:
    """Fan-out publisher: at-least-once delivery to matching subscriptions."""

    def __init__(self) -> None:
        self._connections: dict[int, _Connection] = {}
        self._next_id = 0

    def connect(self) -> _Connection:
        self._next_id += 1
        connection = _Connection(self._next_id, self)
        self._connections[connection.id] = connection
        return connection

    def disconnect(self, connection: _Connection) -> None:
        self._connections.pop(connection.id, None)

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    async def publish(self, event: LeaderboardUpdatedEvent) -> None:
        for connection in list(self._connections.values()):
            connection.offer(event)


class _Connection:
    def __init__(self, identifier: int, hub: LeaderboardEventHub) -> None:
        self.id = identifier
        self._hub = hub
        self._subscriptions: list[SubscriptionKey] = []
        self.queue: asyncio.Queue[LeaderboardUpdatedEvent] = asyncio.Queue(maxsize=QUEUE_SIZE)

    @property
    def subscriptions(self) -> tuple[SubscriptionKey, ...]:
        return tuple(self._subscriptions)

    def subscribe(self, key: SubscriptionKey) -> None:
        if key in self._subscriptions:
            return
        if len(self._subscriptions) >= MAX_SUBSCRIPTIONS_PER_CONNECTION:
            raise SubscriptionInvalid(
                "The subscription limit for this connection was reached.",
                LEADERBOARD_SUBSCRIPTION_LIMITED,
            )
        self._subscriptions.append(key)

    def offer(self, event: LeaderboardUpdatedEvent) -> None:
        if not any(matches(key, event) for key in self._subscriptions):
            return
        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:  # pragma: no cover - slow consumer guard
            logger.warning("leaderboard_event_dropped", extra={"fields": {"connection": self.id}})

    def close(self) -> None:
        self._hub.disconnect(self)


def error_event(code: str, message: str, request_id: str | None) -> dict[str, Any]:
    return EventErrorDto(
        payload=EventErrorPayloadDto(code=code, message=message, request_id=request_id)
    ).model_dump(by_alias=True, mode="json")


def acknowledgement(key: SubscriptionKey, request_id: str | None) -> dict[str, Any]:
    return {
        "eventType": "LEADERBOARD_SUBSCRIBED",
        "version": 1,
        "requestId": request_id,
        "payload": {
            "scopeKey": key.scope_key,
            "scoringPolicyId": key.scoring_policy_id,
            "scoringPolicyVersion": key.scoring_policy_version,
            "rankBy": key.rank_metric.value,
            "k": key.k,
        },
    }


@router.websocket("/ws/v1/leaderboards")
async def leaderboard_channel(websocket: WebSocket) -> None:
    hub: LeaderboardEventHub = websocket.app.state.container.leaderboard.hub
    await websocket.accept()
    connection = hub.connect()
    sender = asyncio.create_task(_send_events(websocket, connection))
    try:
        while True:
            message = await websocket.receive_json()
            request_id = message.get("requestId") if isinstance(message, dict) else None
            try:
                key = parse_subscription(message if isinstance(message, dict) else {})
                connection.subscribe(key)
            except SubscriptionInvalid as error:
                logger.info(
                    "leaderboard_subscription_rejected",
                    extra={"fields": {"code": error.code}},
                )
                await websocket.send_json(error_event(error.code, str(error), request_id))
                continue
            await websocket.send_json(acknowledgement(key, request_id))
    except WebSocketDisconnect:
        pass
    except Exception:  # pragma: no cover - transport failure guard
        logger.warning("leaderboard_channel_failed")
    finally:
        sender.cancel()
        connection.close()


async def _send_events(websocket: WebSocket, connection: _Connection) -> None:
    while True:
        event = await connection.queue.get()
        await websocket.send_json(event_to_dto(event).model_dump(by_alias=True, mode="json"))
