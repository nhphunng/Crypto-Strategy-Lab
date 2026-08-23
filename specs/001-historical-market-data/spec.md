# Feature Specification: Historical Market Data

**Feature Branch**: `feat/001-market-data-spec-plan`  
**Feature Context**: `001-historical-market-data`  
**Created**: 2026-08-13  
**Status**: Approved for implementation  
**Owner**: TV1  
**Input**: Build the historical market-data boundary that acquires, normalizes, validates, stores, reuses, and exposes provider-neutral Candle datasets for chart, strategy, realtime recovery, and backtest consumers.

## Scope and Ownership

TV1 owns historical acquisition, the canonical Candle and CandleDataset meanings, durable storage, bounded historical queries, and closed-Candle gap backfill. TV2 owns realtime provider connections, subscription lifecycle, WebSocket events, and chart UI. TV3 and TV4 consume immutable complete datasets. This feature does not implement chart rendering, realtime streaming, strategies, backtesting, news, sentiment, or live trading.

The older roadmap described Feature 001 as “historical market data + single chart.” The current team allocation supersedes that packaging: TV1 delivers the independently testable historical API and dataset contract; TV2 renders it. This avoids duplicate chart ownership without removing the original end-to-end capability from the product roadmap.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Obtain Normalized Historical Candles (Priority: P1)

As an analyst, I want to request a supported market and UTC time range so that I receive chronological, provider-neutral historical candles without understanding Binance fields.

**SRS Traceability**: `MD-US-01`; `MD-FR-01`, `MD-FR-03`, `MD-FR-04`, `MD-FR-06`; `BR-01`, `BR-02`.

**Why this priority**: Every chart, strategy, recovery flow, and backtest depends on one trustworthy Candle meaning.

**Independent Test**: Request a fixture range that is absent locally, then assert the result contains exactly the expected normalized closed candles in chronological order and the provider payload never crosses the public boundary.

**Acceptance Scenarios**:

1. **Given** a valid supported selection and an aligned closed time range that is not stored, **When** the range is requested, **Then** the system acquires the missing candles, validates and stores them, and returns a `COMPLETE` chronological range.
2. **Given** the provider uses provider-specific arrays and millisecond timestamps, **When** candles are acquired, **Then** consumers receive only the versioned canonical fields, UTC instants, and decimal strings.
3. **Given** the requested range already exists locally, **When** it is requested again, **Then** the same logical candles are returned without another provider request.
4. **Given** a malformed, unsupported, unaligned, future, or over-limit range, **When** it is requested, **Then** the request fails before provider access with a stable actionable error.

---

### User Story 2 - Reuse an Immutable Dataset (Priority: P1)

As a strategy or backtest consumer, I want an immutable complete dataset reference so that later work can reproduce the exact historical input without refetching or silently changing it.

**SRS Traceability**: `MD-FR-04`; `BR-03`, `BR-05`; SRS §7.1; Extended Requirement §3.1.

**Why this priority**: A mutable or incomplete input makes backtest comparison and ranking scientifically invalid.

**Independent Test**: Materialize one complete fixture dataset twice, resolve it by ID, page through its candles, and assert the ID, ordered content, count, and checksum remain identical while provider call count remains one.

**Acceptance Scenarios**:

1. **Given** a complete stored range, **When** a dataset is materialized, **Then** it records provider, pair, timeframe, inclusive start, exclusive end, contract version, candle count, content checksum, and ordered Candle membership.
2. **Given** an identical materialization request, **When** it is repeated or submitted concurrently, **Then** callers resolve the same complete dataset rather than creating duplicate datasets.
3. **Given** a complete dataset ID, **When** a consumer reads it later, **Then** its metadata and Candle contents are unchanged and require no provider request.
4. **Given** acquisition ends with missing or conflicting data, **When** materialization finishes, **Then** no `COMPLETE` dataset is published and no consumer receives partial content as reusable input.

---

### User Story 3 - Backfill an Explicit Closed-Candle Gap (Priority: P2)

As the realtime delivery component, I want to request an exact closed interval after reconnect so that I can restore continuity before claiming the stream is live.

**SRS Traceability**: boundary support for `MD-US-03`, `MD-FR-05`; TV2 owns reconnect and connection-state behavior.

**Why this priority**: TV1 must supply recovery data, but must not absorb TV2's socket lifecycle responsibility.

**Independent Test**: Remove one closed Candle from a stored fixture, request the exact gap, and assert the range becomes `COMPLETE`; when the provider cannot supply it, assert a bounded `PARTIAL` result lists that exact missing interval.

**Acceptance Scenarios**:

1. **Given** a closed interval is absent locally but available upstream, **When** that interval is queried, **Then** only missing coverage is acquired and the final result is continuous.
2. **Given** one or more expected closed intervals remain absent, **When** acquisition ends, **Then** the response is `PARTIAL` with bounded non-overlapping missing ranges.
3. **Given** no Candle exists for the requested closed range, **When** the provider returns no valid data, **Then** the response is `EMPTY` and does not claim completeness.

---

### User Story 4 - Replace a Provider Without Changing Consumers (Priority: P3)

As a market-data maintainer, I want provider-specific behavior isolated behind one contract so that adding another provider does not change chart, strategy, or backtest code.

**SRS Traceability**: `MD-FR-03`; `BR-02`; ADR-003 validation.

**Why this priority**: Binance is the MVP provider, while provider neutrality is the principal extensibility trade-off in the assignment.

**Independent Test**: Run the same provider contract suite against a deterministic fake provider and the Binance mapper, then assert both produce equal canonical Candle values and error categories.

**Acceptance Scenarios**:

1. **Given** a conforming provider adapter, **When** it supplies valid raw candles, **Then** downstream use cases consume the same canonical contract without provider-specific branching.
2. **Given** malformed provider data, **When** mapping occurs, **Then** the adapter rejects it at the boundary and no invalid Candle is stored.

## Edge Cases

- `startTime` equals `endTime`, either boundary is not UTC, or a boundary is not aligned to its timeframe.
- A request ends after the latest interval that can be known closed.
- The range contains exactly one interval, exactly the public page limit, or one interval over the limit.
- Binance returns overlapping pages, duplicates, out-of-order rows, an empty page before the requested end, or rows outside the requested half-open range.
- A duplicate closed Candle has identical content versus different OHLCV content.
- Numeric input is zero, negative, non-finite, uses scientific notation, or violates `high >= max(open, close)` / `low <= min(open, close)`.
- The provider responds with throttling, a retry hint, timeout, transport failure, invalid JSON, or a changed payload shape.
- Two callers request or materialize the same range concurrently.
- Storage succeeds for some candles but dataset finalization fails.
- A dataset exists but its ordered membership no longer matches its recorded checksum; the system must treat this as integrity failure, not repair it silently.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The MVP MUST support provider `BINANCE`, pair `BTCUSDT`, and canonical timeframes `1m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, and `1d` when the provider supports them.
- **FR-002**: All historical acquisition MUST occur through a provider-neutral `MarketDataProvider` boundary; no provider DTO or field name may appear in domain, application-consumer, or public response contracts.
- **FR-003**: A Candle MUST be uniquely identified by `(provider, pair, timeframe, openTime)`.
- **FR-004**: A Candle MUST carry market/provider provenance, interval identity, opening and closing instants, OHLCV values, closed status, and ingestion time under a versioned public contract.
- **FR-005**: Provider and pair values MUST be canonical uppercase values; timestamps MUST be ISO-8601 UTC instants with millisecond precision; numeric market values MUST be exact non-scientific decimal values without binary floating-point conversion.
- **FR-006**: `openTime` MUST align to the selected timeframe. `closeTime` MUST represent the final millisecond of the interval and be exactly one millisecond before the next `openTime`.
- **FR-007**: Historical range semantics MUST be `[startTime, endTime)`: start inclusive and end exclusive. Both boundaries MUST be UTC and aligned to the selected timeframe.
- **FR-008**: Historical dataset acquisition MUST include only intervals known to be closed at evaluation time; future or currently open intervals MUST NOT make a dataset complete.
- **FR-009**: `open`, `high`, `low`, and `close` MUST be finite and positive; `volume` MUST be finite and non-negative; `high` MUST be at least every other price; `low` MUST be at most every other price. Volume version `1` means provider base-asset volume.
- **FR-010**: Valid provider data MUST be normalized and validated before persistence; an invalid row MUST never be partially exposed as a Candle.
- **FR-011**: A historical query MUST read local coverage first and acquire only missing closed intervals from the provider.
- **FR-012**: Stored closed Candle content MUST be immutable in contract version `1`. An identical duplicate MUST be ignored; a conflicting duplicate for the same identity MUST produce an integrity fault and MUST NOT overwrite trusted historical content.
- **FR-013**: Returned Candle sequences MUST be unique and strictly chronological by `openTime`, regardless of provider delivery order or page overlap.
- **FR-014**: A historical range MUST declare `COMPLETE`, `PARTIAL`, or `EMPTY`; `PARTIAL` MUST list bounded, sorted, non-overlapping missing half-open ranges and `COMPLETE` MUST contain none.
- **FR-015**: A range MUST be `COMPLETE` only when every expected closed interval in the requested range is present and valid. Partial acquisition MUST remain readable as an honest range response but MUST NOT be materialized as a reusable complete dataset.
- **FR-016**: Public range responses MUST return at most 1,000 Candles; default page size MUST be 500; an over-limit request MUST fail with `MARKET_RANGE_TOO_LARGE` rather than truncate silently.
- **FR-017**: A complete `CandleDataset` MUST retain an opaque identity, contract version, exact market/range provenance, complete status, ordered Candle count, deterministic content checksum, and creation/completion times.
- **FR-018**: Complete dataset metadata and ordered membership MUST be immutable. Integrity validation MUST fail closed when stored membership and checksum disagree.
- **FR-019**: Materializing the same complete selection and range repeatedly or concurrently MUST be idempotent and resolve one logical dataset.
- **FR-020**: Consumers MUST be able to resolve dataset metadata by ID and read its Candle membership in deterministic pages without a provider request.
- **FR-021**: Dataset states MUST be `BUILDING`, `COMPLETE`, `INCOMPLETE`, or `FAILED`; only `COMPLETE` is eligible by default for strategy and backtest consumers.
- **FR-022**: Provider throttling and transient failures MUST use bounded retry behavior that honors an available retry hint; exhausted attempts MUST return distinct stable throttling or provider-unavailable error categories.
- **FR-023**: Validation, provider, conflict, and integrity failures MUST use versioned stable error codes, sanitized messages, request correlation, and no raw provider payload, credential, stack trace, or internal URL.
- **FR-024**: The service MUST list its supported provider, pair, timeframe, range-limit, and contract-version dimensions without requiring a provider call.
- **FR-025**: Unsupported provider, pair, timeframe, version, or invalid range MUST be rejected before any external provider access.
- **FR-026**: Provider base URLs and credentials MUST be server-controlled configuration; user input MUST NOT select an arbitrary upstream host.
- **FR-027**: Adding a conforming provider MUST require a new adapter and registration only; it MUST NOT require changes to canonical Candle behavior or chart, strategy, and backtest consumers.
- **FR-028**: The same historical query capability MUST serve analyst bootstrap and TV2 closed-gap backfill; this feature MUST NOT create realtime subscriptions or connection states.

### Non-Functional Requirements

- **NFR-001**: For a locally complete range of 500 Candles, at least 95% of representative reads MUST complete within 300 ms under the documented single-instance demo load, excluding network transit.
- **NFR-002**: With a deterministic provider fixture, acquiring and persisting 10,000 one-minute Candles MUST complete within 60 seconds on the documented reference environment and use bounded provider pages of at most 1,000 rows.
- **NFR-003**: All domain and application behavior MUST remain executable without a web framework, database library, or provider SDK.
- **NFR-004**: Provider calls, cache hits, acquired counts, completeness, retry outcomes, conflicts, and dataset finalization MUST be observable through structured sanitized records containing request ID and market selection.
- **NFR-005**: Public contracts MUST be explicitly versioned. Adding optional fields is backward compatible; changing identity, required fields, timestamp/decimal/range meaning, or enum meaning requires a new major version and TV1/TV2/TV3/TV4 review.
- **NFR-006**: Test coverage MUST include domain invariants, provider mapping/pagination, missing-range calculation, idempotency, conflicting duplicates, repository behavior against PostgreSQL, public contracts, and the documented quickstart flow.

### Key Entities

- **Candle**: One provider-neutral OHLCV interval with immutable identity, closed-state semantics, provider provenance, and ingestion timestamp.
- **Market Selection**: Provider, pair, and canonical timeframe requested together.
- **Time Range**: UTC timeframe-aligned half-open interval `[startTime, endTime)`.
- **Historical Candle Range**: A bounded ordered response with completeness and explicit missing ranges; it is not necessarily a reusable dataset.
- **CandleDataset**: Immutable identity and provenance for a complete ordered set of closed Candles used by strategy and backtest consumers.
- **Dataset Membership**: Stable ordered association between a CandleDataset and immutable closed Candles.
- **Provider Capability**: Server-controlled supported providers, pairs, timeframes, limits, and contract versions.

## Traceability and Dependencies

| Feature requirement | Upstream source |
|---|---|
| FR-001, FR-024–FR-025 | `MD-FR-06`; SRS §3.1; Feature 002 contract |
| FR-002–FR-010, FR-12–FR-14 | `MD-FR-01`, `MD-FR-03`; `BR-01`, `BR-02`; ADR-003 |
| FR-011, FR-015–FR-16, FR-22, FR-028 | `MD-FR-01`, `MD-FR-04`, `MD-FR-05`; Feature 002 bootstrap/recovery boundary |
| FR-017–FR-021 | `MD-FR-04`; SRS §7.1; TV3 Strategy Context; TV4 BacktestJob `datasetId` |
| FR-023, FR-026–FR-027 | Constitution CT-03, CT-06, SEC-02, OBS-01, DOD-05 |
| NFR-001–NFR-006 | Constitution PF-01, PF-03, QA-01–QA-05, DOD-01–DOD-06 |

- **TV1 ↔ TV2 locked boundary**: Candle fields, version `1`, decimal strings, UTC millisecond timestamps, timeframe enum, `[start, end)` range, 1,000-Candle response limit, completeness, missing ranges, and stable error categories.
- **TV1 ↔ TV3/TV4 locked boundary**: only closed `COMPLETE` immutable datasets, exact dataset ID/version/checksum, deterministic chronological membership, and no conflicting overwrite.
- **TV2 responsibility**: open-Candle revisions, realtime merge generations, subscription lifecycle, WebSocket envelopes, freshness, reconnect state, and chart rendering.
- **TV4 responsibility**: backtest date selection, execution configuration, deterministic simulation, and retention of dataset provenance in results.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of contract fixtures, normalized Candle identity, fields, UTC precision, decimal encoding, timeframe values, and range semantics match the shared TV1/TV2 version `1` contract.
- **SC-002**: Importing the same fixture range twice or through concurrent requests produces one logical Candle per identity, one logical complete dataset, the same checksum, and no second provider fetch once coverage is complete.
- **SC-003**: In all gap fixtures, completeness and missing ranges exactly describe expected closed intervals; no partial, future, open, invalid, or conflicting content is published as a `COMPLETE` dataset.
- **SC-004**: Resolving and paging a complete dataset later returns byte-equivalent canonical Candle content and metadata without provider access in all reproducibility fixtures.
- **SC-005**: Binance payload-shape changes are confined to its adapter tests; canonical domain, application, and public contract tests require no provider-field changes.
- **SC-006**: All unsupported selections and malformed, unaligned, future, or oversized requests fail before provider access with the documented stable code in 100% of negative fixtures.
- **SC-007**: The local-read and 10,000-Candle acquisition performance targets in NFR-001 and NFR-002 pass in the documented reference environment.
- **SC-008**: Automated tests cover every functional requirement and all critical edge cases, and the quickstart demonstrates acquisition, cache reuse, immutable dataset resolution, and explicit gap behavior.

## Assumptions

- Binance Spot public Kline data is the initial upstream source; no API key is required for public historical candles.
- Pair `BTCUSDT` and the eight canonical timeframes are the MVP market dimensions.
- UTC is the only time zone accepted at the public boundary; client-local display conversion belongs to UI features.
- Version `1` stores provider base-asset volume and closed historical Candles. Quote-asset volume, trades, order book, and provider corrections require a future compatible extension or explicit new dataset/contract version.
- Public chart/backfill reads are bounded to 1,000 Candles. Larger reusable datasets are materialized internally in bounded provider pages and consumed through paginated dataset reads.
- Authentication and multi-user ownership are outside this feature; deployment access control remains an application-level concern.
- ADR-003 is `Accepted`; TV1/TV2/TV3/TV4 completed the shared market-data boundary review on 2026-08-19.

## Explicit Exclusions

- Realtime WebSocket connections, open-Candle revision streams, subscription recovery state, and chart rendering.
- Strategy, indicator, backtest, evaluation, leaderboard, news, sentiment, and real-money execution logic.
- Arbitrary provider URLs, user-uploaded adapters, tick/order-book storage, and silent historical correction of immutable closed Candle content.
