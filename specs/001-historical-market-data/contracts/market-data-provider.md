# Contract: Historical Market Data Provider

**Owner**: TV1  
**Consumer**: Historical market-data application service  
**Version**: `1`

## Boundary

A provider adapter performs external historical integration only. It may know upstream endpoints, authentication, rate limits, pagination, and DTO shapes. It must not persist Candles, compute strategy/backtest behavior, choose public HTTP status, or expose raw payloads beyond the adapter.

Conceptual application port:

```python
class MarketDataProvider(Protocol):
    provider: str

    async def iter_historical(
        self,
        selection: MarketSelection,
        time_range: TimeRange,
    ) -> AsyncIterator[tuple[Candle, ...]]: ...
```

The application requests one supported, closed, aligned half-open range. The adapter yields bounded non-empty pages of canonical Candles or raises one categorized provider error.

## Preconditions

- `selection.provider` matches the registered adapter.
- Pair and timeframe pass server-side capability validation.
- Both range boundaries are UTC and timeframe-aligned.
- `start_time < end_time` and the range contains only intervals expected to be closed.
- The application enforces its maximum expected Candle count before calling the adapter.

An adapter may defensively repeat these checks but must not reinterpret them.

## Output Guarantees

For every yielded Candle:

- provider, pair, and timeframe equal the request;
- identity is `(provider, pair, timeframe, open_time)`;
- `open_time` lies within `[start_time,end_time)` and is aligned;
- `close_time` is the last millisecond before the next interval open;
- OHLC prices and volume are exact `Decimal` values satisfying domain invariants;
- `closed` is true;
- `received_at` is an adapter-generated UTC ingestion time;
- provider field names/array positions are absent from the domain object.

Page guarantees:

- at most 1,000 Candles per page for the Binance adapter;
- pages may be defensively sorted and deduplicated by the adapter;
- the application still treats repository identity/immutability as authoritative;
- the iterator terminates after the requested range and cannot loop forever on a repeated provider page.

The provider is allowed to return no Candle for a valid requested interval. The application, not the adapter, derives `COMPLETE/PARTIAL/EMPTY` and missing ranges.

## Binance v1 Mapping

Upstream operation: `GET /api/v3/klines` using server-controlled Binance base URL.

| Query | Meaning |
|---|---|
| `symbol` | Canonical pair, initially `BTCUSDT` |
| `interval` | Canonical timeframe value supported by Binance |
| `startTime` | Inclusive epoch milliseconds |
| `endTime` | Exclusive application end converted to provider's inclusive millisecond bound as `endTime - 1 ms` |
| `limit` | Maximum `1000` |

Required Kline indexes:

| Index | Meaning | Validation/mapping |
|---:|---|---|
| 0 | open time ms | exact integer → aware UTC `open_time` |
| 1 | open | string → `Decimal` |
| 2 | high | string → `Decimal` |
| 3 | low | string → `Decimal` |
| 4 | close | string → `Decimal` |
| 5 | base asset volume | string → `Decimal` |
| 6 | close time ms | exact integer → aware UTC `close_time` |

The mapper ignores unused Binance fields and rejects:

- non-array rows or fewer than seven positions;
- booleans/floats where exact integers/strings are required;
- scientific, non-finite, negative, or invariant-breaking numeric content;
- misaligned or out-of-request opens;
- close time inconsistent with the canonical timeframe;
- a row representing an interval not yet closed at the injected evaluation time.

## Pagination

1. Start cursor at requested `start_time`.
2. Request up to 1,000 rows through the requested exclusive end.
3. Normalize, retain rows in the requested half-open range, sort by open time, and deduplicate identical identities within the page.
4. Yield the validated page.
5. Advance cursor to one timeframe after the greatest returned open time.
6. Stop when cursor reaches end, response is empty, or the provider returns no new open time.

Overlapping/repeated rows do not cause duplicate yield or an infinite loop. A provider row beyond end is discarded and terminates the relevant scan safely.

## Failure Categories

| Adapter exception | Trigger | Retryable by adapter |
|---|---|---|
| `ProviderRateLimited` | HTTP 429 or provider ban/throttle response | Yes within attempt/retry-delay cap; 418 is never hammered |
| `ProviderUnavailable` | timeout, connection failure, HTTP 5xx | Yes, bounded |
| `ProviderPayloadInvalid` | invalid JSON/shape/types/semantics | No |
| `ProviderRequestRejected` | other HTTP 4xx caused by adapter/config mismatch | No |

All exceptions contain sanitized provider code, stable category, optional bounded retry delay, and safe context. They never include credentials, full request URLs, raw response bodies, or stack traces in public mappings.

## Retry Contract

- Default maximum: three total attempts per HTTP page.
- Connection and read timeouts are finite configuration.
- HTTP 429 honors integer/date `Retry-After` when parseable and within the configured maximum delay.
- Otherwise retryable attempts use capped exponential delay with injected jitter/sleep for deterministic tests.
- Semantic validation and non-429 4xx errors are not retried.
- Cancellation propagates immediately.

## Provider Fitness Tests

Every provider adapter must pass the same behavior suite:

1. Valid one-row and multi-page ranges map to equal canonical Candles.
2. Decimal content is exact and never passes through float.
3. Selection, range, ordering, identity, close time, and OHLCV invariants hold.
4. Empty, overlapping, duplicate, repeated, out-of-range, and malformed pages terminate deterministically.
5. Throttle/transient failures use bounded retry and retry hints; terminal categories are stable.
6. Raw provider DTOs do not appear outside provider tests/infrastructure.

Adding OKX/Bybit is successful only when this suite passes without modifying domain Candle, historical application service, public DTOs, chart, strategy, or backtest consumers.
