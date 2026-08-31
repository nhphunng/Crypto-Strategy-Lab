# Contract: Realtime Market Data Commands and Events

**Status**: Accepted
**Version**: `1`
**Cross-review**: TV1/TV2 completed on 2026-08-19; Candle semantics remain owned by Feature 001 and realtime lifecycle remains owned by Feature 002.

## Endpoint and ownership

- Endpoint: `/ws/v1/market-data`
- TV2 owns command/event envelopes and slot/subscription lifecycle.
- TV1 owns the shared Candle fields and historical range semantics.
- The browser never supplies provider channel names or consumes raw provider payloads.
- One connection accepts at most four active `slotId` bindings.

## Client command envelope

```json
{
  "eventType": "SUBSCRIBE_MARKET_DATA",
  "version": "1",
  "requestId": "req-01",
  "occurredAt": "2026-08-13T10:00:00Z",
  "payload": {
    "slotId": "slot-1",
    "selection": {
      "provider": "BINANCE",
      "pair": "BTCUSDT",
      "timeframe": "5m"
    }
  }
}
```

Supported commands:

| `eventType` | Required payload | Effect |
|---|---|---|
| `SUBSCRIBE_MARKET_DATA` | `slotId`, `selection` | Idempotently bind a slot; new selection replaces its old binding |
| `UNSUBSCRIBE_MARKET_DATA` | `slotId` | Release the slot binding; upstream selection closes only when reference count reaches zero |
| `RETRY_MARKET_DATA` | `slotId` | Reset the affected selection's bounded recovery cycle |

Rules:

- `requestId` is unique per client action. Repeating the same command/request ID has the same effect and does not add a reference.
- `slotId` is stable within the connection and contains no credential or user secret.
- A fifth active slot returns `MARKET_SUBSCRIPTION_LIMIT_REACHED` without changing existing bindings.
- Unknown event types or major versions return a contract error and do not alter subscriptions.

## Server event envelope

```json
{
  "eventType": "CANDLE_UPDATED",
  "version": "1",
  "eventId": "evt-201",
  "requestId": "req-01",
  "occurredAt": "2026-08-13T10:00:01Z",
  "payload": {}
}
```

All events require `eventType`, `version`, unique `eventId`, UTC `occurredAt`, and typed `payload`. `requestId` is present when an event directly acknowledges a command. Clients ignore duplicate `eventId` values.

## `SUBSCRIPTION_STATE_CHANGED`

```json
{
  "eventType": "SUBSCRIPTION_STATE_CHANGED",
  "version": "1",
  "eventId": "evt-200",
  "requestId": "req-01",
  "occurredAt": "2026-08-13T10:00:00Z",
  "payload": {
    "slotIds": ["slot-1", "slot-3"],
    "selection": {
      "provider": "BINANCE",
      "pair": "BTCUSDT",
      "timeframe": "5m"
    },
    "state": "RECONNECTING",
    "attempt": 2,
    "retryAfterMs": 2034,
    "lastEventAt": "2026-08-13T09:59:30Z",
    "reasonCode": "PROVIDER_DISCONNECTED"
  }
}
```

`state` is `LOADING`, `LIVE`, `STALE`, `RECONNECTING`, or `ERROR`. `reasonCode` is optional for healthy states and uses a stable uppercase code. Human-facing UI maps codes to safe messages; raw exception text is forbidden.

## `CANDLE_UPDATED`

```json
{
  "eventType": "CANDLE_UPDATED",
  "version": "1",
  "eventId": "evt-201",
  "occurredAt": "2026-08-13T10:00:01Z",
  "payload": {
    "selection": {
      "provider": "BINANCE",
      "pair": "BTCUSDT",
      "timeframe": "5m"
    },
    "revision": 7,
    "candle": {
      "provider": "BINANCE",
      "pair": "BTCUSDT",
      "timeframe": "5m",
      "openTime": "2026-08-13T10:00:00Z",
      "closeTime": "2026-08-13T10:04:59.999Z",
      "open": "67234.12",
      "high": "67250.00",
      "low": "67220.50",
      "close": "67241.30",
      "volume": "12.50",
      "closed": false,
      "receivedAt": "2026-08-13T10:00:01Z"
    }
  }
}
```

- `revision` increases for accepted updates to the same Candle identity during one stream generation.
- Same identity/revision or duplicate `eventId` is ignored.
- A lower revision is ignored.
- `closed: true` is terminal for version 1; later `closed: false` updates are rejected.
- Distinct older Candle identities may enter only through a recovery batch/history merge, never by moving the live tail backward.

## `MARKET_DATA_ERROR`

```json
{
  "eventType": "MARKET_DATA_ERROR",
  "version": "1",
  "eventId": "evt-202",
  "requestId": "req-02",
  "occurredAt": "2026-08-13T10:00:02Z",
  "payload": {
    "slotId": "slot-5",
    "code": "MARKET_SUBSCRIPTION_LIMIT_REACHED",
    "message": "A dashboard can use at most four chart slots.",
    "retryable": false
  }
}
```

Allowed codes include:

- `MARKET_SUBSCRIPTION_LIMIT_REACHED`
- `MARKET_PAIR_UNSUPPORTED`
- `MARKET_TIMEFRAME_UNSUPPORTED`
- `MARKET_EVENT_VERSION_UNSUPPORTED`
- `PROVIDER_RATE_LIMITED`
- `PROVIDER_DISCONNECTED`
- `MARKET_GAP_RECOVERY_FAILED`
- `MARKET_RECOVERY_EXHAUSTED`

## Bootstrap race handling

For a new or changed slot:

1. Open the shared WebSocket and bind the slot.
2. Buffer valid `CANDLE_UPDATED` events for that selection/generation.
3. Request the bounded historical range.
4. Validate and merge the historical response.
5. Replay buffered events by identity/revision and discard events for an obsolete slot generation.
6. Present `LIVE` only when the subscription is healthy and the historical range is not known to contain a missing closed interval.

This sequence prevents an update arriving between the historical request and response from being lost.

## Reconnect and gap recovery

- A provider disconnect immediately changes affected selections to `STALE`, then `RECONNECTING`.
- A missed provider heartbeat for 30 seconds is treated as stale; heartbeat interval target is 15 seconds.
- Automatic attempts use capped exponential backoff with jitter and stop after eight attempts. Default approximate delays are 1, 2, 4, 8, 16, and at most 30 seconds.
- When the browser reports offline, retry waits for connectivity and does not consume the attempt budget.
- After reconnect, the backend backfills from the interval after the last confirmed closed Candle through the latest closed interval.
- `LIVE` is emitted only when the recovery response is `COMPLETE` and expected closed intervals are continuous.
- Exhaustion emits `ERROR`; `RETRY_MARKET_DATA` resets the attempt budget.
- Recovery affects only slots referencing the failed selection.

## Compatibility and limits

- Version `1` accepts only the Candle and enum values documented here and in `openapi.yaml`.
- Adding optional fields is backward compatible; changing required field meaning, identity, enums, or decimal/time encoding requires a new major message version.
- Events exclude unlimited arrays, raw payloads, secrets, stack traces, provider URLs, and internal topology.
- The server enforces four logical slot bindings per connection and reports active logical slots separately from unique upstream selections.
