# Data Model: Realtime Multi-Chart Dashboard

## Ownership

- TV1 owns durable `Candle` and `CandleDataset` storage and the historical query contract.
- TV2 consumes Candle data and owns ephemeral chart/subscription/recovery state.
- No TV2-specific database table is required.

## Candle *(shared, TV1-owned)*

| Field | Type | Required | Rule |
|---|---|---:|---|
| `provider` | enum/string | Yes | Canonical provider code, initially `BINANCE` |
| `pair` | string | Yes | Canonical uppercase pair, initially `BTCUSDT` |
| `timeframe` | enum | Yes | `1m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `1d` |
| `openTime` | UTC instant | Yes | Aligned to timeframe boundary |
| `closeTime` | UTC instant | Yes | Later than `openTime` and aligned to provider interval semantics |
| `open` | decimal string | Yes | Finite and positive |
| `high` | decimal string | Yes | `high >= open`, `close`, and `low` |
| `low` | decimal string | Yes | `low <= open`, `close`, and `high` |
| `close` | decimal string | Yes | Finite and positive |
| `volume` | decimal string | Yes | Finite and non-negative |
| `closed` | boolean | Yes | `false → true` allowed; `true → false` forbidden |
| `receivedAt` | UTC instant | Yes | Backend ingestion timestamp for freshness measurement |

**Identity**: `(provider, pair, timeframe, openTime)`.

**Merge rules**:

1. Newer identity appends within the bounded buffer.
2. Same open identity replaces OHLCV and may transition to closed.
3. Same closed identity with identical values is ignored.
4. A conflicting closed update is rejected from the live series and recorded as a provider-data fault.
5. Older realtime identity is ignored; recovery batches are sorted and merged before publication.

## Historical Candle Range *(shared response)*

| Field | Type | Rule |
|---|---|---|
| `provider` | provider code | Matches request |
| `pair` | pair code | Matches request |
| `timeframe` | timeframe enum | Matches request |
| `rangeStart` | UTC instant | Inclusive |
| `rangeEnd` | UTC instant | Exclusive |
| `completeness` | enum | `COMPLETE`, `PARTIAL`, `EMPTY` |
| `candles` | ordered Candle list | Unique, chronological, maximum 1,000 |
| `missingRanges` | range list | Empty when complete; exact sorted non-overlapping explanation when partial, bounded to at most 500 by the 1,000-Candle request limit |

## Chart Slot *(client-session state)*

| Field | Type | Rule |
|---|---|---|
| `slotId` | stable string | Unique within one dashboard session; not array position |
| `pair` | pair code | Same dashboard-level pair for MVP |
| `timeframe` | timeframe enum | Independently configurable |
| `status` | connection state | Never inferred only from presence of old candles |
| `candles` | bounded Candle buffer | Maximum 1,000, initial target at most 500 |
| `rangeStart` / `rangeEnd` | UTC instant | Explicit visible/requested range |
| `viewport` | client view state | Owned by slot; unaffected by other slots |
| `generation` | increasing integer | Discards late responses/events after reconfiguration |
| `error` | optional error summary | Actionable and sanitized |

**Identity**: `slotId`.

## Market Selection

| Field | Type | Rule |
|---|---|---|
| `provider` | provider code | Supported by backend registry |
| `pair` | pair code | Canonical uppercase value |
| `timeframe` | timeframe enum | Canonical serialized value |

**Identity**: `(provider, pair, timeframe)`.

## Live Subscription *(ephemeral server state)*

| Field | Type | Rule |
|---|---|---|
| `connectionId` | opaque server ID | Sanitized identifier; not a credential |
| `slotId` | client stable ID | At most four active per connection |
| `selection` | Market Selection | Validated before provider access |
| `state` | connection state | Follows transition table below |
| `referenceCount` | positive integer | Number of slots using the unique selection |
| `lastEventAt` | optional UTC instant | Used for freshness/health |
| `lastClosedOpenTime` | optional UTC instant | Recovery checkpoint |
| `attempt` | non-negative integer | Maximum eight automatic attempts per cycle |
| `nextRetryAt` | optional UTC instant | Present while reconnecting |
| `requestId` | correlation ID | Links subscribe/retry lifecycle |

**Logical identity**: `(connectionId, slotId)`.

**Shared upstream identity**: `Market Selection` with a set of referencing `(connectionId, slotId)` values.

## Connection State

```text
LOADING ────────────────→ LIVE
   │                       │
   └────────→ ERROR        ├────────→ STALE
                            │           │
                            │           └────→ RECONNECTING ───→ LIVE
                            │                         │
                            └─────────────────────────┴──────→ ERROR
ERROR ── manual retry ──→ RECONNECTING
any state ── slot removed/reconfigured ──→ RELEASED
```

| State | Meaning |
|---|---|
| `LOADING` | Historical bootstrap or initial subscription is pending |
| `LIVE` | Provider connection is healthy and known closed-candle continuity is restored |
| `STALE` | Last data remains visible but freshness cannot be guaranteed |
| `RECONNECTING` | A bounded automatic or manual recovery cycle is active |
| `ERROR` | Initial load/subscription or recovery failed and requires user action/configuration change |
| `RELEASED` | Slot mapping is removed; no future event may update that generation |

## Validation and Compatibility

- Backend validation is authoritative for pair, timeframe, limit, time range, slot count, event version, and Candle invariants.
- JSON fields use camelCase; backend/domain fields use snake_case with explicit mappers.
- Decimal values remain strings at REST/WebSocket boundaries.
- All public messages declare version `1`; unknown major versions are rejected with an actionable error.
- TV1 and TV2 must approve Candle fields, timestamp precision, range inclusivity, missing-range semantics, and error codes together.
