# Contract: Historical Market Data Consumer Boundaries

**Owner**: TV1 / Feature 001  
**Consumers**: TV2 chart delivery, TV3 strategy foundation, TV4 backtest/evaluation  
**Version**: `1`

## Shared Candle Meaning

All consumers use one identity:

```text
(provider, pair, timeframe, openTime)
```

- `openTime` is the UTC timeframe-aligned interval-opening instant.
- TV3's `Signal.timestamp` equals its associated Candle `openTime`; `timestamp` is not a second Candle identity field.
- Public timestamp precision is milliseconds and UTC (`...SSS Z`).
- Public OHLCV values are exact fixed-point decimal strings; v1 `volume` is provider base-asset volume.
- `closeTime` is one millisecond before the next interval open.
- The canonical shared Candle can be open or closed. Feature 001's historical storage/ranges/datasets contain only closed Candles; TV2 owns open-Candle revisions.

## TV2 Historical Bootstrap

1. TV2 establishes a slot/subscription generation and buffers accepted live events.
2. TV2 calls `GET /api/v1/market-data/candles` for an aligned closed range of at most 1,000 intervals.
3. It validates version, selection, range, completeness, exact missing ranges, ordering, Candle invariants, and fields.
4. It merges historical closed Candles then buffered events by canonical identity/revision.
5. It may present `LIVE` only when its connection is healthy and required historical continuity is `COMPLETE`.

TV2 does not call the provider directly and does not infer completeness from array length alone.

## TV2 Reconnect Backfill

After provider reconnect, TV2 computes:

```text
startTime = last confirmed closed Candle openTime + timeframe
endTime   = latest known closed boundary (exclusive)
```

It requests that exact range through the same historical endpoint. `COMPLETE` permits live continuity; `PARTIAL`/`EMPTY` keep the selection stale/reconnecting or transition it to error according to Feature 002. TV1 does not own retry attempt count, socket state, generation tokens, or UI status.

## TV3/TV4 Immutable Dataset Consumption

1. Materialize or reuse through `POST /api/v1/market-data/datasets`.
2. Retain `datasetId`, schema version, provider, pair, timeframe, `[startTime,endTime)`, Candle count, and checksum.
3. Use only `status=COMPLETE` by default.
4. Resolve metadata and cursor-paginated membership by dataset ID; these reads never call a provider.
5. Validate exact chronological closed membership and checksum. Never ask for “latest” to reinterpret an old experiment.
6. Strategy signals align their `timestamp` to Candle `openTime`; backtest results retain the dataset ID/version/checksum they actually consumed.

## Compatibility Rules

Backward-compatible version 1 changes may add optional fields that consumers ignore safely. A new major version and TV1/TV2/TV3/TV4 review are required to change:

- Candle identity or required fields;
- timeframe serialized values;
- UTC precision or `openTime`/`closeTime` meaning;
- decimal or volume meaning;
- half-open range inclusivity;
- completeness/missing-range semantics;
- complete dataset immutability/checksum meaning;
- stable error categories used for consumer state transitions.

## Locked Limits

- Public range default: 500 Candles.
- Public range maximum: 1,000 Candles; oversized requests fail, never truncate silently.
- Maximum distinct missing ranges: 500, derived from the maximum alternating-gap pattern within 1,000 expected intervals.
- Dataset membership page maximum: 1,000 Candles.
- Larger dataset materialization remains server-bounded and is read through pages.
