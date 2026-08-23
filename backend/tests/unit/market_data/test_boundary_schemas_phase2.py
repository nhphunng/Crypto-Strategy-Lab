from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import TypeAdapter, ValidationError

from crypto_lab.api.schemas.market_data import (
    CandleUpdatedEvent,
    MarketDataCommandEnvelope,
    MarketDataErrorEvent,
    MarketDataEventEnvelope,
    RetryMarketDataCommand,
    SubscribeMarketDataCommand,
    SubscriptionStateChangedEvent,
    UnsubscribeMarketDataCommand,
)

SELECTION = {
    "provider": "BINANCE",
    "pair": "BTCUSDT",
    "timeframe": "5m",
}

CANDLE = {
    **SELECTION,
    "openTime": "2026-08-13T10:00:00Z",
    "closeTime": "2026-08-13T10:04:59.999Z",
    "open": "67234.12",
    "high": "67250.00",
    "low": "67220.50",
    "close": "67241.30",
    "volume": "12.50",
    "closed": False,
    "receivedAt": "2026-08-13T10:00:01Z",
}


def command(event_type: str, payload: dict[str, object]) -> dict[str, object]:
    return {
        "eventType": event_type,
        "version": "1",
        "requestId": "req-01",
        "occurredAt": "2026-08-13T10:00:00Z",
        "payload": payload,
    }


def event(event_type: str, payload: dict[str, object]) -> dict[str, object]:
    return {
        "eventType": event_type,
        "version": "1",
        "eventId": "evt-201",
        "requestId": "req-01",
        "occurredAt": "2026-08-13T10:00:01Z",
        "payload": payload,
    }


def test_command_envelope_is_discriminated_versioned_and_utc() -> None:
    adapter = TypeAdapter(MarketDataCommandEnvelope)
    subscribe = command(
        "SUBSCRIBE_MARKET_DATA",
        {"slotId": "slot-1", "selection": SELECTION},
    )

    parsed = adapter.validate_python(subscribe)

    assert isinstance(parsed, SubscribeMarketDataCommand)
    assert parsed.version == "1"
    assert parsed.payload.slot_id == "slot-1"
    assert parsed.payload.selection.pair == "BTCUSDT"

    invalid_event_type = deepcopy(subscribe)
    invalid_event_type["eventType"] = "subscribe_market_data"
    invalid_version = deepcopy(subscribe)
    invalid_version["version"] = "2"
    non_utc = deepcopy(subscribe)
    non_utc["occurredAt"] = "2026-08-13T17:00:00+07:00"

    for invalid in (invalid_event_type, invalid_version, non_utc):
        with pytest.raises(ValidationError):
            adapter.validate_python(invalid)


@pytest.mark.parametrize(
    ("event_type", "expected_type"),
    [
        ("UNSUBSCRIBE_MARKET_DATA", UnsubscribeMarketDataCommand),
        ("RETRY_MARKET_DATA", RetryMarketDataCommand),
    ],
)
def test_slot_only_commands_keep_distinct_typed_payloads(
    event_type: str,
    expected_type: type[UnsubscribeMarketDataCommand] | type[RetryMarketDataCommand],
) -> None:
    parsed = TypeAdapter(MarketDataCommandEnvelope).validate_python(
        command(event_type, {"slotId": "slot-1"})
    )

    assert isinstance(parsed, expected_type)
    assert parsed.payload.slot_id == "slot-1"


def test_state_and_candle_events_validate_typed_payloads() -> None:
    adapter = TypeAdapter(MarketDataEventEnvelope)
    state_payload = {
        "slotIds": ["slot-1", "slot-3"],
        "selection": SELECTION,
        "state": "RECONNECTING",
        "attempt": 2,
        "retryAfterMs": 2034,
        "lastEventAt": "2026-08-13T09:59:30Z",
        "reasonCode": "PROVIDER_DISCONNECTED",
    }
    candle_payload = {"selection": SELECTION, "revision": 7, "candle": CANDLE}

    state = adapter.validate_python(event("SUBSCRIPTION_STATE_CHANGED", state_payload))
    candle = adapter.validate_python(event("CANDLE_UPDATED", candle_payload))

    assert isinstance(state, SubscriptionStateChangedEvent)
    assert state.payload.slot_ids == ("slot-1", "slot-3")
    assert state.payload.reason_code == "PROVIDER_DISCONNECTED"
    assert isinstance(candle, CandleUpdatedEvent)
    assert candle.payload.revision == 7
    assert candle.payload.candle.open_time == "2026-08-13T10:00:00Z"

    bad_reason = event("SUBSCRIPTION_STATE_CHANGED", {**state_payload, "reasonCode": "offline"})
    bad_revision = event("CANDLE_UPDATED", {**candle_payload, "revision": -1})
    non_utc_candle = event(
        "CANDLE_UPDATED",
        {
            **candle_payload,
            "candle": {**CANDLE, "receivedAt": "2026-08-13T17:00:01+07:00"},
        },
    )
    for invalid in (bad_reason, bad_revision, non_utc_candle):
        with pytest.raises(ValidationError):
            adapter.validate_python(invalid)


def test_error_event_requires_uppercase_code_and_serializes_camel_case() -> None:
    adapter = TypeAdapter(MarketDataEventEnvelope)
    message = event(
        "MARKET_DATA_ERROR",
        {
            "slotId": "slot-5",
            "code": "MARKET_SUBSCRIPTION_LIMIT_REACHED",
            "message": "A dashboard can use at most four chart slots.",
            "retryable": False,
        },
    )

    parsed = adapter.validate_python(message)

    assert isinstance(parsed, MarketDataErrorEvent)
    assert parsed.payload.code == "MARKET_SUBSCRIPTION_LIMIT_REACHED"
    serialized = adapter.dump_python(parsed, by_alias=True, mode="json")
    assert serialized["eventType"] == "MARKET_DATA_ERROR"
    assert serialized["occurredAt"] == "2026-08-13T10:00:01Z"
    assert serialized["payload"]["slotId"] == "slot-5"

    lowercase_code = deepcopy(message)
    assert isinstance(lowercase_code["payload"], dict)
    lowercase_code["payload"]["code"] = "market_subscription_limit_reached"
    with pytest.raises(ValidationError):
        adapter.validate_python(lowercase_code)
