# Data Model: Historical Market Data

**Feature**: `001-historical-market-data`  
**Contract version**: `1`

## Conventions

- Domain/Python/database names use `snake_case`; public JSON uses explicit `camelCase` aliases.
- Public timestamps are UTC ISO-8601 with millisecond precision; database timestamps are `TIMESTAMPTZ` normalized to UTC.
- Market numeric values enter as provider strings, use Python `Decimal`, persist as `NUMERIC(38,18)`, and leave as canonical fixed-point strings.
- Range semantics are always `[start_time, end_time)` with aligned UTC boundaries.
- Historical dataset membership contains closed Candles only.

## Value Object: Timeframe

| Serialized value | Duration | Alignment rule |
|---|---:|---|
| `1m` | 60 seconds | UTC minute divisible by 1; second/millisecond zero |
| `5m` | 300 seconds | UTC minute divisible by 5 |
| `15m` | 900 seconds | UTC minute divisible by 15 |
| `30m` | 1,800 seconds | UTC minute divisible by 30 |
| `1h` | 3,600 seconds | UTC hour boundary |
| `2h` | 7,200 seconds | UTC hour divisible by 2 |
| `4h` | 14,400 seconds | UTC hour divisible by 4 |
| `1d` | 86,400 seconds | UTC midnight |

Methods provide duration, aligned-boundary validation, interval close time (`open + duration - 1 ms`), expected Candle count, and next/previous open.

## Value Object: MarketSelection

| Field | Domain type | Rule |
|---|---|---|
| `provider` | uppercase string | Registry-supported; initial `BINANCE` |
| `pair` | uppercase string | Registry-supported; initial `BTCUSDT` |
| `timeframe` | `Timeframe` | One canonical value above |

**Identity**: `(provider, pair, timeframe)`.

User input never supplies a provider URL/channel. Registry configuration resolves adapter/capabilities.

## Value Object: TimeRange

| Field | Domain type | Rule |
|---|---|---|
| `start_time` | aware UTC `datetime` | Inclusive and timeframe-aligned |
| `end_time` | aware UTC `datetime` | Exclusive, timeframe-aligned, later than start |

Derived behavior:

- `expected_count = (end_time - start_time) / timeframe.duration`
- expected opens are `start_time + n * duration` for `0 <= n < expected_count`
- adjacent missing expected opens are coalesced into non-overlapping half-open `TimeRange` values
- a range is closed at `evaluated_at` only when `end_time <= timeframe.floor(evaluated_at)`

## Entity: Candle

The shared domain/public Candle contract permits both open and closed observations because TV2 emits open-Candle revisions. Feature 001's historical provider, repository, range, and dataset paths accept and durably persist only `closed = true`; they must not weaken the shared Candle type or take ownership of TV2 revision behavior.

| Field | Domain type | Database | Required rule |
|---|---|---|---|
| `id` | UUID | `UUID` PK | Internal persistence identity; not Candle business identity |
| `provider` | string | `VARCHAR(32)` | Uppercase canonical provider |
| `pair` | string | `VARCHAR(20)` | Uppercase canonical pair |
| `timeframe` | `Timeframe` | `VARCHAR(8)` | Canonical enum value |
| `open_time` | UTC datetime | `TIMESTAMPTZ` | Aligned to timeframe |
| `close_time` | UTC datetime | `TIMESTAMPTZ` | `open_time + duration - 1 ms` |
| `open` | Decimal | `NUMERIC(38,18)` | Finite, `> 0` |
| `high` | Decimal | `NUMERIC(38,18)` | Finite, `>= open`, `close`, `low` |
| `low` | Decimal | `NUMERIC(38,18)` | Finite, `<= open`, `close`, `high` |
| `close` | Decimal | `NUMERIC(38,18)` | Finite, `> 0` |
| `volume` | Decimal | `NUMERIC(38,18)` | Finite, `>= 0`; base-asset volume in v1 |
| `closed` | bool | `BOOLEAN` | Always true in historical durable storage for v1 |
| `received_at` | UTC datetime | `TIMESTAMPTZ` | Adapter ingestion time |
| `content_hash` | lowercase hex | `CHAR(64)` | SHA-256 canonical content excluding internal ID/received time |
| `created_at` | UTC datetime | `TIMESTAMPTZ` | Persistence audit time |

**Business identity**: `(provider, pair, timeframe, open_time)`.

**Database constraints/indexes**:

- Unique constraint `uq_candles_identity(provider, pair, timeframe, open_time)`.
- Check constraints for positive prices, non-negative volume, high/low invariants, and `closed = true`.
- Covering/range index `(provider, pair, timeframe, open_time)` supports local coverage and ordered reads.
- A conflicting `content_hash` on an existing business identity raises an integrity error; it is never updated.

**Canonical content line** (UTF-8, no spaces):

```text
1|BINANCE|BTCUSDT|5m|2026-08-13T10:00:00.000Z|2026-08-13T10:04:59.999Z|67234.12|67250|67220.5|67241.3|12.5|true
```

`received_at`, database ID, and audit time are excluded so retries produce the same content hash.

## Aggregate: HistoricalCandleRange *(not persisted as a row)*

| Field | Type | Rule |
|---|---|---|
| `schema_version` | string | `1` |
| `selection` | `MarketSelection` | Matches request |
| `range` | `TimeRange` | Requested aligned range |
| `completeness` | enum | `COMPLETE`, `PARTIAL`, `EMPTY` |
| `missing_ranges` | ordered `TimeRange[]` | Empty for complete; max 100 entries at public boundary |
| `candles` | ordered `Candle[]` | Unique, closed, within range, max 1,000 publicly |

Completeness derivation:

- `COMPLETE`: stored Candle opens equal every expected open; `missing_ranges=[]`.
- `EMPTY`: no Candles and every expected open is missing.
- `PARTIAL`: at least one Candle and at least one expected open is missing.

This object can honestly represent provider data gaps. It is not an immutable reusable dataset until complete materialization.

## Entity: CandleDataset

Table: `candle_datasets`

| Field | Domain type | Database | Rule |
|---|---|---|---|
| `id` | UUID | `UUID` PK | Opaque stable dataset identity |
| `request_key` | lowercase hex | `CHAR(64)` unique | SHA-256 of version + selection + range |
| `schema_version` | string | `VARCHAR(16)` | `1` |
| `provider` | string | `VARCHAR(32)` | Matches all members |
| `pair` | string | `VARCHAR(20)` | Matches all members |
| `timeframe` | `Timeframe` | `VARCHAR(8)` | Matches all members |
| `start_time` | UTC datetime | `TIMESTAMPTZ` | Inclusive aligned bound |
| `end_time` | UTC datetime | `TIMESTAMPTZ` | Exclusive aligned bound |
| `status` | `DatasetStatus` | `VARCHAR(16)` | Lifecycle below |
| `candle_count` | integer | `INTEGER` | Null before completion; exact expected count on completion |
| `checksum` | lowercase hex | `CHAR(64)` | Null before completion; ordered canonical SHA-256 on completion |
| `build_token` | UUID | `UUID` nullable | Only active claimant can finalize/fail |
| `lease_expires_at` | UTC datetime | `TIMESTAMPTZ` nullable | Allows recovery of abandoned `BUILDING` |
| `failure_code` | stable string | `VARCHAR(64)` nullable | Sanitized terminal/incomplete category |
| `created_at` | UTC datetime | `TIMESTAMPTZ` | First claim time |
| `updated_at` | UTC datetime | `TIMESTAMPTZ` | State/lease audit time |
| `completed_at` | UTC datetime | `TIMESTAMPTZ` nullable | Set exactly on successful completion |

**Logical identity**: `request_key`, derived from:

```text
1|provider|pair|timeframe|startTime|endTime
```

**Database constraints/indexes**:

- Unique `request_key` prevents duplicate logical datasets.
- Unique selection/range/version constraint is retained as a human-auditable equivalent guard.
- Check status-dependent nullability: complete requires count/checksum/completed time and no build token; building requires token/lease.
- Index `(status, lease_expires_at)` supports stale-build recovery.
- Index `(provider, pair, timeframe, start_time, end_time)` supports provenance discovery.

## Entity: CandleDatasetMember

Table: `candle_dataset_members`

| Field | Database | Rule |
|---|---|---|
| `dataset_id` | UUID FK → `candle_datasets.id` | Cascade delete is permitted only before completion; application never deletes complete datasets |
| `position` | INTEGER | Zero-based chronological position |
| `candle_id` | UUID FK → `candles.id` | Member must be closed and match dataset selection/range |

**Primary key**: `(dataset_id, position)`.  
**Unique**: `(dataset_id, candle_id)`.

Completion transaction inserts exactly `expected_count` positions without gaps, ordered by `open_time`. Dataset pages use `position > cursor`, never mutable offset semantics.

## Enum: DatasetStatus

```text
              complete coverage
BUILDING ─────────────────────────> COMPLETE
    │                                  (terminal immutable)
    ├── successful but gaps ───────> INCOMPLETE
    └── provider/conflict/system ──> FAILED

INCOMPLETE/FAILED ── explicit retry or expired lease claim ──> BUILDING
```

| State | Meaning | Consumer eligibility |
|---|---|---|
| `BUILDING` | One claimant owns a non-expired build lease | Not eligible; callers may poll same ID |
| `COMPLETE` | Exact closed coverage and immutable membership/checksum committed | Eligible by default |
| `INCOMPLETE` | Acquisition ended successfully but expected closed intervals remain missing | Not eligible; missing data must be resolved first |
| `FAILED` | Provider, conflict, validation, integrity, or unexpected failure prevented completion | Not eligible; explicit retry/remediation |

`COMPLETE` has no outgoing transition in contract version 1.

## Dataset Checksum

1. Load membership ordered by `position`.
2. Assert position is contiguous from zero, selection matches, every Candle is closed and within the dataset range, opens equal all expected opens, and each Candle's stored `content_hash` matches recomputation.
3. Join each Candle canonical content line with `\n`, including one final newline.
4. SHA-256 the UTF-8 bytes and store lowercase hexadecimal output.

This checksum captures actual values, not only identities. Two datasets with equal selection/range but changed OHLCV cannot share checksum; contract v1 prevents such silent mutation.

## Provider DTO: Binance Kline *(infrastructure only)*

Expected positional fields used by the adapter:

| Index | Provider meaning | Canonical target |
|---:|---|---|
| 0 | Open time in epoch milliseconds | `open_time` |
| 1 | Open price string | `open` |
| 2 | High price string | `high` |
| 3 | Low price string | `low` |
| 4 | Close price string | `close` |
| 5 | Base asset volume string | `volume` |
| 6 | Close time in epoch milliseconds | `close_time` |

All other fields are deliberately ignored. The adapter validates array length, types, range, timeframe alignment, and canonical invariants before yielding a domain Candle.

## Public DTO Mapping

| Domain | Public JSON |
|---|---|
| `schema_version` | `schemaVersion` |
| `open_time` / `close_time` | `openTime` / `closeTime` |
| `received_at` | `receivedAt` |
| `start_time` / `end_time` | `startTime` / `endTime` |
| `missing_ranges` | `missingRanges` |
| `dataset_id` | `datasetId` |
| `candle_count` | `candleCount` |
| `completed_at` | `completedAt` |
| `next_cursor` / `has_more` | `nextCursor` / `hasMore` |

Mappers are explicit; Pydantic/ORM objects never become domain objects or public responses implicitly.

## Integrity Rules Across Consumers

- TV2 may merge open/realtime revisions in an ephemeral buffer, but its closed value must conform to the same Candle invariant and identity.
- TV3/TV4 receive only `COMPLETE` dataset metadata and ordered closed membership by default.
- A BacktestResult must retain dataset ID, schema version, range, and checksum; it must not resolve “latest data” later.
- No repository method exposes raw Binance fields or permits generic update of a complete dataset/member.
