# Research: Leaderboard and Trade Visualization

## Decision 1: Persist a versioned Top-K projection

**Decision**: Persist current Top-K rows plus projection metadata, while treating immutable `EvaluationResult` and `ScoringPolicy` records as authoritative inputs. A projection is identified by comparison scope, scoring-policy identity/version, selected ranking metric, and K; presentation sorting, metric-range filters, and pagination do not mutate that identity.

**Rationale**: The assignment permits storage or derivation. A persisted bounded projection makes frequent reads and incremental updates cheap, supports an explicit projection version for client reconciliation, and preserves traceability without duplicating financial calculations.

**Alternatives considered**:

- Derive every read from all Evaluation Results: simplest write path but increasingly expensive and awkward for update ordering.
- Cache only in Redis: fast but makes correctness and recovery depend on an ephemeral component.
- Store a denormalized copy of every result: unnecessary duplication beyond Top-K/history needs.

## Decision 2: Serialize ranking updates transactionally

**Decision**: Lock one complete leaderboard identity (scope, policy/version, ranking metric, and K), upsert the candidate by immutable evaluation/policy identity, recompute the bounded deterministic order, replace affected ranks atomically, and increment `projection_version` only when visible state changes.

**Rationale**: This prevents duplicate rows, gaps, and conflicting rank assignments when workers finish concurrently. The database unique constraints are the final idempotency guard.

**Alternatives considered**:

- Last-write-wins updates without locking: can lose a better concurrent candidate.
- Distributed lock in Redis: adds an availability dependency when PostgreSQL already owns the transaction.
- Full event sourcing: disproportionate for this MVP.

## Decision 3: Use REST snapshot plus invalidating WebSocket event

**Decision**: REST returns the authoritative current snapshot/detail; a compact versioned `LEADERBOARD_UPDATED` event carries scope, projection version, changed identities, Top-1 summary, and run context. Clients refetch on version gaps or reconnect.

**Rationale**: It meets no-refresh updates without placing a full leaderboard or large trade/chart graph in every event. Snapshot recovery makes missed or out-of-order delivery explicit.

**Alternatives considered**:

- Full snapshot in every event: excessive payload and still needs reconnect recovery.
- Polling only: conflicts with the assignment's event-driven live update flow.
- JSON Patch: smaller but brittle across client versions and harder to validate.

## Decision 4: Keep ranking semantics in the versioned scoring policy

**Decision**: A policy defines eligibility, direction for each supported ranking metric, normalization/weights for overall score, a default ranking metric, and an ordered deterministic tie-break key. The request selects one supported ranking metric; presentation sorting remains separate. The leaderboard consumes stored score/metrics and policy and does not recompute evaluation metrics.

**Rationale**: This keeps Evaluation separate from Strategy and preserves historical meaning. Required no-trade and non-finite behavior is explicit before ranking.

**Alternatives considered**:

- Hard-code score formula in leaderboard: breaks policy versioning and architecture boundaries.
- Let the UI sort/rank raw metrics: duplicates business rules and can disagree with the backend.
- Random tie resolution: non-reproducible.

## Decision 5: Use generic chart overlay descriptors

**Decision**: Strategies/results expose validated overlay descriptors (`LINE`, `BAND`, `ZONE`) and timestamped markers (`BUY`, `SELL`, `ENTRY`, `EXIT`) with stable IDs and provenance references. The frontend renderer dispatches by primitive kind, never strategy name.

**Rationale**: MA, Bollinger, Support/Resistance, MACD, and future strategies can visualize through the same contract. Label and shape are mandatory so color is not the only cue.

**Alternatives considered**:

- Concrete `if strategy == MA` UI branches: directly violates extensibility.
- Store chart-library-specific series options: couples backend/domain results to a frontend dependency.
- Render only trades: fails the Buy/Sell and strategy explanation requirement.

## Decision 6: Bound chart and trade retrieval separately

**Decision**: Ranked-result summary/detail returns provenance and aggregate data; Candle/overlay/Signal retrieval is bounded by a selected range, while Trades use page pagination (25 default, 200 maximum).

**Rationale**: Large histories and trade collections stay responsive and event payloads remain narrow.

**Alternatives considered**:

- One deeply nested result response: unbounded payload and slow initial rendering.
- Cursor pagination everywhere: good at extreme scale but less convenient for the assignment's numbered trade table; can be revisited without changing domain semantics.

## Decision 7: Preserve numeric precision and UTC instants

**Decision**: Monetary/price/quantity/metric values cross boundaries as decimal strings and timestamps as ISO-8601 UTC. Formatting and local timezone display occur only in the UI.

**Rationale**: Avoids binary floating-point corruption and timestamp ambiguity while keeping exact recorded marker positions.

**Alternatives considered**:

- JSON numbers for every decimal: convenient but can lose precision in JavaScript.
- Local timestamps without offset: cannot be reliably aligned or reproduced.

## Decision 8: Test boundaries with real infrastructure

**Decision**: Unit-test pure ranking; use real PostgreSQL for persistence/concurrency and API/WebSocket integration; use deterministic Candle/signal/trade fixtures for visualization; add browser E2E and a focused k6 benchmark.

**Rationale**: It follows the constitution and tests the high-risk transaction and reconnect behavior that mocks would conceal.

**Alternatives considered**:

- Repository mocks for all integration tests: misses locks, constraints, and transaction behavior.
- End-to-end tests only: slow and weak at pinpointing ranking edge cases.
