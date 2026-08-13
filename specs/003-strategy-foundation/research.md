# Research: Strategy Foundation

## Decision 1: Keep strategy calculation in a pure Python domain

**Decision**: Represent Strategy, Strategy Context, parameters, definitions, registry metadata, and Signals as immutable domain values. Strategy calculation accepts all data explicitly and uses no database, HTTP, queue, provider, clock, or random source.

**Rationale**: Pure calculation directly satisfies determinism, look-ahead safety, unit-testability, and TV4 reuse. Python 3.12 is the constitution-approved backend language, while framework-neutral domain values preserve layered boundaries.

**Alternatives considered**:

- Let each strategy fetch its own data: rejected because it hides provenance and breaks deterministic tests.
- Put indicator logic in API or worker handlers: rejected because it duplicates business rules across consumers.
- Split strategy execution into a service: rejected as unnecessary operational complexity for the MVP.

## Decision 2: Use Decimal domain arithmetic and explicit MA/RSI conventions

**Decision**: Convert validated Candle prices to `Decimal` domain values. MA is the arithmetic mean of the last `period` closes. RSI uses close-to-close gains/losses and Wilder initialization/smoothing. Do not round intermediate values; apply a documented comparison precision only at serialization/fixture assertion boundaries.

**Rationale**: The spec defines exact crossing/equality behavior. Decimal arithmetic avoids binary-float boundary surprises and makes repeated fixtures stable. The algorithm conventions remove the common ambiguity between RSI variants.

**Alternatives considered**:

- Pandas/NumPy float calculations: convenient, but adds boundary and dtype behavior that is unnecessary for two linear indicators.
- A third-party technical-analysis library: rejected because it adds a core dependency and may hide version-specific formula behavior.
- Recompute each window independently: simple but avoidably quadratic for large periods.

## Decision 3: Emit one Signal per Candle with deterministic identities

**Decision**: A valid non-empty analysis returns one Signal per input Candle. Warm-up and non-crossing decisions emit HOLD with explicit reason codes. Signal identity is derived from the Strategy Definition identity, context fingerprint, candle timestamp, and sequence position; output is sorted by candle timestamp and position.

**Rationale**: A lossless one-to-one sequence makes timestamp alignment, warm-up, repeated execution, and TV4 consumption unambiguous. Content-derived identity remains stable across retries and processes.

**Alternatives considered**:

- Emit only BUY/SELL: loses warm-up/non-action traceability and makes empty output ambiguous.
- Random UUID signal IDs: stable only after persistence and violates repeat-output equality.
- Let consumers invent HOLD rows: spreads strategy-specific semantics downstream.

## Decision 4: Use trusted startup registration, not dynamic code upload

**Decision**: Strategy implementations are packaged with the application and registered in a deterministic bootstrap composition function. The registry is an in-process domain catalog keyed by strategy ID and immutable version. Public APIs expose discovery and execution, not arbitrary code upload or runtime registration.

**Rationale**: This satisfies extensibility for team-developed strategies without introducing untrusted execution, sandboxing, signature verification, or deployment complexity. A new compliant strategy adds its own implementation, metadata, registration, and tests.

**Alternatives considered**:

- Dynamic Python module discovery: adds import-order, packaging, and security risks.
- Uploadable strategy code: explicitly outside scope.
- `if/switch` by strategy name: rejected because downstream consumers would require modification.

## Decision 5: Separate registry entries from persisted Strategy Definitions

**Decision**: Registry Entry describes available executable behavior and parameter metadata. Strategy Definition is an immutable persisted aggregate containing exact parameters for one registered behavior version. Definitions use a canonical content fingerprint for idempotent creation and historical lookup.

**Rationale**: Executable code cannot be meaningfully reconstructed from a database row, while experiments need durable exact parameter/version provenance. Separating the concepts keeps the registry free of persistence logic and keeps historical definitions durable.

**Alternatives considered**:

- Persist full registry as mutable rows: risks metadata/code drift and implies database-driven executable loading.
- Keep definitions only in memory: historical experiments could not resolve exact parameter sets after restart.
- Overwrite one definition per strategy: directly violates reproducibility.

## Decision 6: Use semantic versions with explicit compatibility ranges

**Decision**: Contract and strategy versions use canonical `MAJOR.MINOR.PATCH`. A consumer declares one supported contract major and an inclusive minor range. A major mismatch or unsupported minor is `INCOMPATIBLE_CONTRACT_VERSION`; patch differences preserve contract meaning. Strategy behavior or parameter-schema semantic changes require a new strategy version.

**Rationale**: Exact string equality would reject harmless compatible revisions, while unconstrained “latest” behavior would silently change historical meaning. Explicit ranges are discoverable and testable.

**Alternatives considered**:

- Exact contract-version equality: too restrictive for compatible patch/minor evolution.
- Always accept the latest version: non-reproducible and contradicts explicit error behavior.
- Custom version strings: difficult to order and validate consistently.

## Decision 7: Treat deprecated and unavailable versions differently

**Decision**: Deprecated retained versions remain resolvable for historical metadata but are rejected for new analysis with `STRATEGY_VERSION_DEPRECATED`. Unavailable versions return `STRATEGY_VERSION_UNAVAILABLE`. Neither state falls back to latest.

**Rationale**: Historical traceability and safe new execution are different needs. The distinction matches the spec while avoiding silent behavior substitution.

**Alternatives considered**:

- Allow new execution of deprecated versions: weakens retirement controls.
- Delete all deprecated metadata: breaks historical provenance.
- Map deprecated to unavailable: loses actionable lifecycle meaning.

## Decision 8: Use an application dataset port and a shared domain contract for TV4

**Decision**: HTTP analysis accepts an immutable dataset reference; the application obtains normalized Candles through a market-data port and builds Strategy Context. TV4 may supply an already validated immutable Strategy Context through the same application/domain service. Both paths produce the same result contract.

**Rationale**: Strategy code stays independent of storage and transport, HTTP requests remain bounded, and TV4 avoids serializing large candle arrays between modules in the same monolith.

**Alternatives considered**:

- Accept arbitrary raw Candle arrays over the public API: duplicates the market-data trust boundary and permits untraceable datasets.
- Make TV4 call the public HTTP API: adds transport coupling inside the monolith.
- Let TV4 call MA/RSI directly: spreads concrete strategy knowledge downstream.

## Decision 9: Persist definitions with append-only PostgreSQL constraints

**Decision**: Store Strategy Definitions in PostgreSQL using SQLAlchemy and an Alembic migration. Enforce unique definition identity and canonical content fingerprint. Application services expose create-or-resolve and exact lookup; no update/delete operation is provided for immutable content.

**Rationale**: PostgreSQL is the approved durable store and gives concurrent uniqueness guarantees needed for idempotent definition creation. Repository integration tests use a real database as required by the constitution.

**Alternatives considered**:

- JSON files: weak concurrency and deployment semantics.
- Redis: not a durable source of truth and broker selection is unresolved.
- Event sourcing: disproportionate for immutable append-only definitions.

## Decision 10: Expose discovery and bounded analysis through REST

**Decision**: Provide read endpoints for registry discovery and exact strategy-version metadata, plus a synchronous bounded analysis endpoint using dataset reference, decision timestamp, exact strategy version, and parameters. Registration remains an internal trusted composition contract.

**Rationale**: Analysts and UI/search consumers need discoverable metadata and signal inspection. A bounded pure analysis is not a long-running queued workflow and keeps the public contract simple.

**Alternatives considered**:

- Queue every strategy analysis: introduces worker/broker complexity without a stated scale need.
- No HTTP boundary: prevents analyst/UI discovery and direct inspection.
- Public registration endpoint: misleading because metadata alone cannot install trusted executable behavior.

