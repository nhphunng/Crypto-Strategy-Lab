# Contract and Integrity Requirements Checklist: Historical Market Data

**Purpose**: Formal PR-review gate for completeness, clarity, consistency, measurability, and risk coverage of TV1 historical Candle/dataset requirements  
**Created**: 2026-08-13  
**Feature**: [spec.md](../spec.md)  
**Audience/timing**: TV1 author plus TV2/TV4 reviewers before implementation and merge  
**Depth/focus**: Formal; canonical contract, data integrity, provider isolation, reproducibility, and failure behavior

**Note**: Items evaluate the written requirements and design—not whether code already works.

## Requirement Completeness

- [x] CHK001 Are acquisition, normalization, validation, persistence, local reuse, range response, dataset materialization, and dataset resolution requirements all documented? [Completeness, Spec US1–US2, FR-002–FR-021]
- [x] CHK002 Are TV1 responsibilities and exclusions from TV2 realtime/chart, TV3 strategy, and TV4 backtest behavior explicit? [Completeness, Spec §Scope and Ownership, §Explicit Exclusions]
- [x] CHK003 Are all canonical Candle meanings—provenance, interval identity, time, OHLCV, closed status, and ingestion time—required without leaking provider fields? [Completeness, Spec FR-002–FR-005; Data Model §Candle]
- [x] CHK004 Are public range, provider page, and dataset page bounds specified independently? [Completeness, Spec FR-016; Plan §Contract Decisions; OpenAPI]
- [x] CHK005 Are immutable dataset identity, version, market/range provenance, status, count, checksum, ordered membership, and audit times covered? [Completeness, Spec FR-017–FR-021; Data Model §CandleDataset]
- [x] CHK006 Are provider capabilities, server-controlled upstream configuration, timeouts, retries, and stable failure categories documented? [Completeness, Spec FR-022–FR-027; Provider Contract]

## Requirement Clarity

- [x] CHK007 Is Candle identity unambiguously based on provider, pair, timeframe, and UTC interval open rather than arrival time? [Clarity, Spec FR-003; Data Model §Candle]
- [x] CHK008 Are `[startTime,endTime)`, alignment, expected count, latest closed boundary, and close-time semantics mathematically precise? [Clarity, Spec FR-006–FR-008; Data Model §TimeRange]
- [x] CHK009 Is exact decimal behavior clear across provider input, domain comparison, persistence, public serialization, and checksums? [Clarity, Spec FR-005, FR-009; Research D02]
- [x] CHK010 Is base-asset volume meaning explicit for contract version 1? [Clarity, Spec FR-009; Data Model §Candle]
- [x] CHK011 Are `COMPLETE`, `PARTIAL`, and `EMPTY` mutually exclusive and objectively derived from expected opens? [Clarity, Spec FR-014–FR-015; Data Model §HistoricalCandleRange]
- [x] CHK012 Are `BUILDING`, `COMPLETE`, `INCOMPLETE`, and `FAILED` transitions and consumer eligibility unambiguous? [Clarity, Spec FR-021; Data Model §DatasetStatus]
- [x] CHK013 Is “duplicate” split into identical idempotent delivery versus conflicting closed content? [Clarity, Spec FR-012; Research D05]

## Requirement Consistency

- [x] CHK014 Do Candle fields, timeframe enum, UTC precision, decimal strings, identity, and closed marker agree with Feature 002's shared contract? [Consistency, Spec §TV1 ↔ TV2 locked boundary; OpenAPI; Feature 002 Data Model]
- [x] CHK015 Does TV1's closed historical range remain compatible with TV2's open/closed realtime Candle without assigning open-revision ownership to TV1? [Consistency, Spec FR-008, FR-028; §TV2 responsibility]
- [x] CHK016 Do dataset completeness/immutability rules satisfy TV3 Strategy Context and TV4 BacktestJob provenance rather than “latest range” lookup? [Consistency, Spec US2, FR-017–FR-021; Traceability]
- [x] CHK017 Do public camelCase, backend/database snake_case, UTC, enum, error, and version conventions match the Constitution? [Consistency, Plan §Contract Decisions; Data Model §Public DTO Mapping]
- [x] CHK018 Does the chart exclusion reconcile the newer team allocation with the older Feature 001 roadmap without dropping the integrated product outcome? [Consistency, Spec §Scope and Ownership; Research D12]
- [x] CHK019 Do architecture/ADR references identify the Accepted binding decisions consistently? [Consistency, Plan §Architecture Decision References]

## Acceptance Criteria Quality

- [x] CHK020 Can first acquisition and second-request provider avoidance be objectively measured with fixture call counts? [Measurability, Spec US1; SC-002]
- [x] CHK021 Can dataset immutability/reuse be measured by stable ID, content, count, checksum, and zero provider access? [Measurability, Spec US2; SC-002, SC-004]
- [x] CHK022 Can exact gap behavior be measured from timeframe expected opens and bounded missing ranges? [Measurability, Spec US3; SC-003]
- [x] CHK023 Can provider replaceability be measured through one shared adapter fitness suite with no consumer changes? [Measurability, Spec US4; SC-005]
- [x] CHK024 Are local-read and 10,000-Candle acquisition performance targets quantified with load/data exclusions and documented-environment expectations? [Measurability, Spec NFR-001–NFR-002; SC-007]
- [x] CHK025 Can invalid input before-provider behavior be measured for every unsupported/unaligned/future/oversized category? [Measurability, Spec FR-025; SC-006]

## Scenario and Edge-Case Coverage

- [x] CHK026 Are primary, alternate/cache-hit, partial/empty, exception/provider, recovery/gap, concurrency, and non-functional scenarios represented? [Coverage, Spec US1–US4, §Edge Cases]
- [x] CHK027 Are exact-limit and one-over-limit boundaries, single-interval ranges, and adjacent range composition addressed? [Coverage, Spec §Edge Cases, FR-007, FR-016]
- [x] CHK028 Are overlapping, duplicate, out-of-order, repeated, empty, and out-of-range provider pages addressed without infinite pagination? [Coverage, Spec §Edge Cases; Provider Contract §Pagination]
- [x] CHK029 Are malformed provider numeric/type/shape, invalid JSON, throttle, timeout, transport, 4xx, and 5xx outcomes categorized? [Coverage, Spec §Edge Cases, FR-022–FR-023; Provider Contract §Failure Categories]
- [x] CHK030 Are concurrent identical dataset requests, crashed/expired builders, partial persistence, and failed finalization covered? [Coverage, Spec §Edge Cases, FR-019–FR-021; Research D08]
- [x] CHK031 Is checksum/membership disagreement specified as fail-closed integrity failure rather than silent repair? [Coverage, Spec §Edge Cases, FR-018; Data Model §Dataset Checksum]

## Non-Functional and Dependency Requirements

- [x] CHK032 Are index, bounded collection, structured observability, sanitized error/log, readiness, and migration requirements represented in plan/test work? [Non-Functional, Spec NFR-001–NFR-006; Plan §Operational Plan]
- [x] CHK033 Is domain/application independence from FastAPI, SQLAlchemy, httpx/Binance, clocks, and provider DTOs explicit and testable? [Architecture, Spec NFR-003; Plan §Dependency direction]
- [x] CHK034 Is every new dependency justified by a named problem plus operational/test impact? [Dependency, Research §Dependency Rationale]
- [x] CHK035 Are deferred choices—provider correction versions, oversized async imports, new pairs/providers, authentication—bounded by explicit revisit triggers rather than unresolved ambiguity? [Assumption, Spec §Assumptions; Research D05, D10]

## Reviewer Result

All 35 requirement-quality gates pass. No unresolved ambiguity, conflict, or missing critical scenario blocks implementation. Architecture/ADR approval and TV2/TV3/TV4 cross-review were completed on 2026-08-19; their technical compatibility inputs remain fully documented.
