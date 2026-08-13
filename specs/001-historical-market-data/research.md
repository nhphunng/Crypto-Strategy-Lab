# Research and Decisions: Historical Market Data

**Feature**: `001-historical-market-data`  
**Date**: 2026-08-13  
**Decision owner**: TV1; cross-review required from TV2 and TV4

## Decision Summary

| ID | Decision | Selected option | Main trade-off |
|---|---|---|---|
| D01 | System boundary | Provider-neutral adapter and canonical Candle | More mapper/test code in exchange for provider replaceability |
| D02 | Numeric representation | `Decimal` / PostgreSQL `NUMERIC` / JSON decimal strings | More explicit serialization in exchange for exact reproducibility |
| D03 | Time semantics | UTC millisecond instants, timeframe-aligned `[start,end)` | Stricter clients in exchange for no boundary ambiguity |
| D04 | Historical eligibility | Closed intervals only for complete history/datasets | Current open Candle comes from TV2 realtime, not historical dataset |
| D05 | Closed duplicate policy | Ignore exact duplicates; reject conflicting closed content | Provider corrections need explicit revision workflow |
| D06 | Persistence | Canonical immutable Candle + immutable dataset membership in PostgreSQL | One join table in exchange for reproducible dataset provenance |
| D07 | Acquisition | Read-through local coverage, fetch only computed gaps | Gap computation is more complex than refetch-all |
| D08 | Dataset build coordination | Deterministic request key + database build claim/lease | State/lease handling in exchange for cross-process idempotency |
| D09 | API shape | Versioned bounded REST ranges plus dataset resource/pagination | More endpoints in exchange for distinct chart/backfill and backtest needs |
| D10 | Initial execution model | Synchronous bounded materialization | Simpler Feature 001; very large builds defer to measured worker need |
| D11 | Retry policy | Finite timeout and bounded backoff; respect `Retry-After` | Some transient failures surface instead of retrying indefinitely |
| D12 | Scope ownership | TV1 backend history/contract; TV2 chart/realtime | Feature 001 alone has no visual chart, but ownership and merge conflicts are clean |

## D01 — Provider-Neutral Adapter and Canonical Candle

**Decision**: Application code calls a `MarketDataProvider` protocol. The Binance adapter alone knows `/api/v3/klines`, array indexes, millisecond integers, provider limits, and HTTP error shapes. It maps them to a canonical domain Candle before persistence.

**Why selected**:

- Directly satisfies `MD-FR-03`, `BR-02`, Constitution AR-03/AR-04 and the provider-change scenario in the assignment.
- Allows a fake provider and future OKX/Bybit adapter to pass the same contract tests.
- Prevents provider schema changes from propagating into frontend, strategy, and backtest code.

**Alternatives rejected**:

- **Use Binance DTO everywhere**: fastest initial implementation, but provider lock-in makes the architecture trade-off answer wrong and change amplification high.
- **Browser calls Binance**: avoids one backend hop, but breaks security, validation, caching, persistence, shared gap recovery, and deterministic datasets.
- **Generic dictionary-based provider output**: appears flexible but removes compile-time/domain guarantees and merely hides schema coupling in string keys.

## D02 — Exact Decimal End to End

**Decision**: Parse provider number strings directly into `Decimal`; persist with `NUMERIC(38,18)`; serialize canonical non-scientific decimal strings. Domain constructors reject floats and non-finite values.

**Why selected**: Price/volume values become inputs to indicators, trades, metrics, checksums, and reproducibility. IEEE-754 binary float can change equality, duplicate detection, checksum, and later accounting.

**Alternatives rejected**:

- **Python/JSON float**: convenient and fast, but cannot exactly represent most decimal exchange values.
- **Scaled integer**: exact and performant, but requires one fixed scale that differs by asset/provider and complicates public readability.
- **Store raw string only**: preserves text but makes numeric invariants/indexed analysis cumbersome and allows semantically equal spellings to hash differently.

**Canonicalization**: normalize `Decimal`, render fixed-point, remove unnecessary trailing fractional zeroes, retain one `0` for zero, and never emit exponent notation.

## D03 — UTC, Millisecond Precision, and Half-Open Ranges

**Decision**: `openTime` is the identity instant. All public timestamps are UTC ISO-8601 with exactly millisecond precision. Request ranges are timeframe-aligned `[startTime,endTime)`. `closeTime` is the last millisecond before the next interval open.

**Why selected**:

- Half-open adjacent ranges compose without overlap: `[a,b) + [b,c)`.
- Expected interval opens and missing ranges can be calculated deterministically.
- Matches Feature 002 and Binance Kline close-time semantics.

**Alternatives rejected**:

- **Inclusive end**: creates duplicate boundary Candles when paging or backfilling adjacent ranges.
- **Local time**: introduces daylight-saving and client-location ambiguity.
- **Arrival timestamp identity**: out-of-order and retry delivery creates duplicates/time regression.
- **Arbitrary unaligned boundaries**: unclear whether partial intervals belong in results.

## D04 — Closed Historical Datasets

**Decision**: Complete historical range/dataset coverage counts only known closed intervals. TV2 supplies current open-Candle revisions over realtime events. A request ending after the latest closed boundary is rejected for dataset creation.

**Why selected**: Immutable strategy/backtest input cannot include a value that is still changing. This also gives TV2 one clear owner for open-to-closed revision behavior.

**Alternative rejected**: Persist an open Candle in a complete dataset and update it later. This makes the dataset mutable and invalidates checksums/results.

## D05 — Immutable Closed Candle and Conflict Rejection

**Decision**: A repeated identity with identical canonical content is idempotent. Different closed content for the same identity is a data-integrity conflict; trusted storage is not overwritten automatically.

**Why selected**: Silent historical corrections would retroactively change old strategy/backtest inputs. Rejecting creates an observable repair decision rather than hiding it.

**Alternatives rejected**:

- **Last write wins**: easy, but destroys reproducibility and allows out-of-order old data to overwrite newer trusted data.
- **Ignore every duplicate**: preserves storage but hides an important provider disagreement.
- **Full event-sourced Candle revisions now**: supports corrections but adds substantial model/query complexity without an approved correction use case.

**Revisit trigger**: A demonstrated need to ingest official provider corrections. Add explicit Candle revision/dataset versioning; never mutate an old complete dataset.

## D06 — PostgreSQL Canonical Candles and Dataset Membership

**Decision**: Store each logical closed Candle once under its unique identity. Store dataset metadata separately and freeze ordered membership in a join table at completion. Record a deterministic checksum of canonical ordered content.

**Why selected**:

- PostgreSQL 16 is the approved stack and supplies transactions, uniqueness, exact numerics, concurrency, indexes, and durable reuse.
- A membership snapshot makes `datasetId` meaningful and auditable for TV3/TV4.
- Shared Candles avoid copying large OHLCV rows for identical datasets.

**Alternatives rejected**:

- **Dataset metadata only, query canonical range later**: simpler, but later storage changes could silently change the dataset behind an old ID.
- **Copy every Candle into each dataset**: strongest physical snapshot, but multiplies storage and duplicate-write cost.
- **CSV/Parquet files**: useful for analytics export, but adds file/object-store lifecycle and transactional coordination not needed for MVP.
- **TimescaleDB**: valuable at much larger measured time-series scale, but an extra operational dependency without current evidence.
- **Redis/in-memory cache as source**: fast but not durable or sufficient for backtest provenance.

## D07 — Read Local Coverage, Fetch Only Gaps

**Decision**: Compute expected timeframe opens, compare with locally stored identities, coalesce missing opens into half-open ranges, then call the provider only for those ranges. Reread canonical storage before returning completeness.

**Why selected**: Satisfies reuse, reduces provider load/rate-limit risk, and provides the same primitive TV2 needs after reconnect.

**Alternatives rejected**:

- **Always refetch full range**: simpler, but violates the no-repeat provider outcome and increases conflict/rate-limit exposure.
- **Trust one dataset-level complete flag only**: fast but cannot reuse overlapping ranges or repair a single gap.
- **Cache by HTTP query string**: misses equivalent/overlapping range reuse and does not create domain provenance.

## D08 — Deterministic Dataset Claim and Lease

**Decision**: Hash canonical selection/range/version into a request key. Atomically create or claim one dataset build record with a random build token and lease expiry. Only the current token may finalize/fail it; non-owners receive the same dataset ID/state. Expired builds may be reclaimed.

**Why selected**: Database uniqueness alone prevents duplicate rows but not duplicate provider work. An in-process lock fails with multiple API processes. A durable claim makes retries/crashes observable and idempotent.

**Alternatives rejected**:

- **Per-process `asyncio.Lock` only**: not safe across processes/containers.
- **Hold a PostgreSQL transaction/advisory lock during provider HTTP**: blocks a connection and keeps a long transaction open.
- **Distributed Redis lock**: adds infrastructure for a need PostgreSQL can satisfy.

## D09 — Separate Range and Dataset Resources

**Decision**:

- Bounded range endpoint: chart bootstrap and explicit TV2 gap backfill; honest `COMPLETE/PARTIAL/EMPTY`; max 1,000 Candles.
- Dataset materialization endpoint: build/reuse immutable complete input; may process multiple provider pages under a configured expected-count cap.
- Dataset metadata endpoint and cursor-paginated Candle membership endpoint: downstream reproducible reads without provider access.
- Dimensions endpoint: validates/configures clients without an upstream call.

**Why selected**: A chart wants a small recent range and completeness; a backtest wants a durable identity and pages. Conflating them either returns unbounded data or gives `datasetId` weak semantics.

**Alternative rejected**: One endpoint returning arbitrary-size candles plus optional dataset metadata. It is hard to bound, cache, paginate, and version consistently.

## D10 — Synchronous Bounded Materialization First

**Decision**: The first implementation completes a dataset build within the request, subject to timeouts and a configured maximum expected count. A concurrent caller can receive `BUILDING` with the same dataset ID. No queue/worker is introduced for market-data ingestion.

**Why selected**: The Constitution requires simplicity; queued workers are justified for backtest scale, not yet for historical import. Domain/provider/repository ports make later orchestration replaceable.

**Alternatives rejected**:

- **Celery job immediately**: improves long-build request behavior but adds broker, worker, job state, deployment, and recovery before measured need.
- **Unbounded synchronous build**: simplest code but exposes denial-of-service and request timeout risk.

**Revisit trigger**: measured materialization routinely exceeds the API timeout or configured dataset cap. Move only application orchestration to an accepted worker/job contract; retain Candle/provider/repository contracts.

## D11 — Bounded Provider Retry

**Decision**: Apply connection/read timeouts and at most three attempts for transport errors, HTTP 429, and 5xx responses. Honor a bounded `Retry-After`; use capped exponential delay with jitter otherwise. Do not retry semantic validation errors or HTTP 4xx other than 429.

**Why selected**: Indefinite retries consume resources and hide dependency failure. Immediate failure on every transient fault reduces reliability. Three bounded attempts balance both.

**Special case**: Binance HTTP 418 is treated as rate-limited/unavailable and is not hammered; an available retry hint is honored within the configured cap.

## D12 — TV1/TV2 Scope Split

**Decision**: TV1 implements no frontend chart. It owns the history/Candle/dataset contract and closed-gap data capability. TV2 owns chart UI, WebSocket subscription/reconnect state, and open-Candle merge revisions.

**Why selected**: `docs/team-planning/SPECKIT_TEAM_WORKFLOW.md` is the newer, explicit ownership plan. Feature 002 already has chart contracts/tasks and names TV1 as history owner. Implementing a second chart would create conflicting ownership and duplicated merge risk.

**Alternative rejected**: Keep the older “Feature 001 + single chart” packaging literally. It gives a standalone visual demo, but duplicates TV2 files/decisions and makes later branch integration unsafe.

**Preserved outcome**: Feature 001 is independently demoed through its HTTP/quickstart contract. The integrated historical candlestick remains a project outcome when TV2 consumes it.

## Dependency Rationale

| Dependency | Problem solved | Why standard library/current code is insufficient | Operational/test impact |
|---|---|---|---|
| FastAPI + Pydantic | Versioned HTTP binding, validation, OpenAPI | Standard library has no comparable typed ASGI/OpenAPI boundary | ASGI contract tests; no domain import |
| SQLAlchemy 2 + Alembic + asyncpg | PostgreSQL mapping, transactions, migrations, async driver | Handwritten SQL/migration plumbing increases consistency risk | Real-PostgreSQL repository and migration tests |
| httpx | Async provider HTTP, timeouts, mock transport | `urllib` is synchronous and lacks the selected async ergonomics | Raw provider contract tests without network |
| pytest + pytest-asyncio | TDD and async fixtures | `unittest` can work but is not the approved project test stack | Unit/contract/integration/performance markers |
| Ruff + mypy | Style, import, and type-boundary gates | Runtime tests do not detect all dependency/type drift | CI/local quality commands |

No Redis, Celery, Pandas, NumPy, TimescaleDB, or provider SDK is required by this feature.

## Implementation Fitness Evidence

The completed provider fitness suite runs the same deterministic Kline through the fake provider and Binance adapter and asserts byte-equivalent canonical Candle content. Architecture tests independently reject outer-framework imports from domain/application and Binance Kline terms outside infrastructure. On 2026-08-13 these gates passed as part of the 54-test suite together with raw mapping, pagination, retry, invalid-payload, and provider-port validation cases. Adding a second provider therefore remains adapter plus server-controlled registration; canonical Candle, range, dataset, and public consumer code contain no Binance branch.

Runtime packaging also uses a reviewed dependency-closure lock. No provider SDK is present, and normal INFO logging suppresses dependency request URLs in favor of application-owned sanitized outcome fields.

## Resolved Unknowns

All high-impact design questions are resolved. Items requiring future product evidence—provider corrections, imports beyond the synchronous cap, multiple pairs/providers, and authentication—have explicit revisit triggers rather than placeholder decisions.
