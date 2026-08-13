# Feature Specification: Strategy Foundation

**Feature Branch**: `feat/003-strategy-foundation-spec-plan`

**Created**: 2026-08-13

**Status**: Draft

**Input**: User description: "Provide TV3's common strategy contract, MA and RSI strategies, BUY/SELL/HOLD signals, strategy registration and discovery, and immutable strategy versioning for deterministic use by backtesting."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run MA and RSI Strategies (Priority: P1)

As an `ANALYST`, I want to run MA or RSI with valid parameters on normalized market data so that I can obtain deterministic and comparable trading signals. This story narrows SRS story `SE-US-01` to TV3's assigned built-in strategies: MA and RSI.

**Why this priority**: Producing trustworthy signals through one common contract is the smallest independently valuable strategy capability and establishes the input/output boundary required by downstream backtesting.

**Independent Test**: Run each strategy against fixed normalized-candle fixtures using valid, boundary, invalid, warm-up, and insufficient-history cases; verify parameter validation, signal semantics, ordering, look-ahead safety, and repeatability without a registry user interface or backtest execution.

**Acceptance Scenarios**:

1. **Given** an ordered normalized-candle dataset and a valid MA Strategy Definition, **When** the analyst runs it repeatedly, **Then** every run returns the same timestamp-ordered BUY/SELL/HOLD sequence with the same provenance.
2. **Given** an ordered normalized-candle dataset and a valid RSI Strategy Definition, **When** the analyst runs it repeatedly, **Then** every run returns the same timestamp-ordered BUY/SELL/HOLD sequence with the same provenance.
3. **Given** MA or RSI parameters outside the published rules, **When** execution is requested, **Then** the request fails as `INVALID_PARAMETERS` before any signal is generated and identifies every invalid parameter.
4. **Given** fewer candles than the selected strategy needs for an evaluable value, **When** execution is requested, **Then** the result contains deterministic warm-up HOLD signals for supplied valid candles and identifies that the sequence never reached an evaluable state.
5. **Given** a candle whose timestamp is later than the context's decision timestamp, **When** execution is requested, **Then** the complete request fails as `INVALID_CONTEXT` and no signals are returned.
6. **Given** identical input candles up to a decision timestamp but different candles after it, **When** each valid context is evaluated at that decision timestamp, **Then** the signals at or before that time are identical.

---

### User Story 2 - Inspect Strategy Signals (Priority: P2)

As an `ANALYST`, I want to inspect timestamped BUY, SELL, and HOLD signals so that I can understand strategy behavior before those signals are consumed by a backtest. This story traces to SRS story `SE-US-02`.

**Why this priority**: Analysts and downstream consumers need explainable, time-aligned, provenance-rich output before a signal sequence can be trusted or reproduced.

**Independent Test**: Produce signals from known MA and RSI fixtures and verify every signal's identity, timestamp, action, provenance, optional explanation fields, ordering, and boundary behavior without simulating trades.

**Acceptance Scenarios**:

1. **Given** a successful strategy run, **When** the analyst inspects any emitted signal, **Then** it identifies the exact Strategy Definition, immutable strategy version, validated parameters, normalized dataset, UTC candle timestamp, action, and deterministic position in the sequence.
2. **Given** a strategy that supports strength or a human-readable reason, **When** it emits a signal, **Then** those values are visible; **and given** a strategy that does not support them, **Then** their absence does not invalidate the signal.
3. **Given** a valid empty candle input, **When** the strategy runs, **Then** it returns an empty ordered signal sequence with execution provenance and no error.
4. **Given** a candle at an exact MA or RSI decision boundary without a strict crossing, **When** the strategy evaluates it, **Then** it emits HOLD for that timestamp.
5. **Given** signals from more than one Strategy Definition sharing a timestamp, **When** a consumer combines the sequences, **Then** each signal remains distinguishable and can be ordered deterministically without using strategy-specific rules.

---

### User Story 3 - Register and Discover Strategies (Priority: P3)

As a `STRATEGY_DEVELOPER`, I want to register and discover strategies through a common registry so that compatible strategy types can be added without changing downstream consumers. This story covers the TV3 foundation portions of SRS stories `SP-US-01` and `SP-US-03`.

**Why this priority**: Registry-based discovery removes hard-coded strategy-name knowledge and makes the strategy foundation extensible after MA and RSI behavior is available.

**Independent Test**: Register valid MA and RSI entries, discover their metadata, attempt invalid and incompatible registrations, and register a compliant example strategy whose calculation is outside this feature; verify existing entries and downstream behavior remain unchanged.

**Acceptance Scenarios**:

1. **Given** valid MA and RSI registry entries, **When** a consumer discovers available strategies, **Then** both are returned through the same mechanism with identity, type, immutable version, contract version, status, and parameter definitions.
2. **Given** a strategy identity and version already registered, **When** a duplicate entry is submitted, **Then** registration fails as `DUPLICATE_STRATEGY_ENTRY` and the original entry remains unchanged and usable.
3. **Given** invalid metadata or an invalid parameter definition, **When** registration is attempted, **Then** it fails as `INVALID_STRATEGY_METADATA` and all previously registered strategies remain available.
4. **Given** a strategy using an unsupported contract version, **When** registration is attempted, **Then** it fails as `INCOMPATIBLE_CONTRACT_VERSION` and all previously registered strategies remain available.
5. **Given** a compliant example strategy such as MACD metadata and behavior supplied outside this feature, **When** it is registered, **Then** consumers can discover and request it without MA-, RSI-, or MACD-specific changes to Backtester, Evaluator, or Leaderboard behavior.

---

### User Story 4 - Preserve Immutable Strategy Versions (Priority: P4)

As a `STRATEGY_DEVELOPER`, I want behavior and parameter changes to create a new immutable strategy version or definition identity so that previous experiments remain reproducible. This story traces to SRS story `SP-US-02`.

**Why this priority**: Version immutability protects historical provenance once the execution and discovery contracts exist.

**Independent Test**: Register two versions or definitions, resolve both after the newer one exists, attempt to alter a referenced definition, and request unknown, unavailable, deprecated, and incompatible versions; verify explicit results and no fallback.

**Acceptance Scenarios**:

1. **Given** an existing Strategy Definition referenced by a historical consumer, **When** behavior or parameters change, **Then** the original definition remains unchanged and the change is represented by a distinct immutable version or definition identity.
2. **Given** old and new strategy versions are registered, **When** a consumer resolves the old version, **Then** it receives the original behavior metadata and exact parameter set rather than the latest version.
3. **Given** an unknown strategy ID, **When** resolution is requested, **Then** it fails as `UNKNOWN_STRATEGY` without fallback.
4. **Given** a known strategy whose requested historical version is unavailable, **When** resolution is requested, **Then** it fails as `STRATEGY_VERSION_UNAVAILABLE` without fallback.
5. **Given** a deprecated but retained compatible version, **When** a historical consumer resolves its metadata, **Then** the exact version remains traceable with deprecated status; **and when** a new execution requests it, **Then** execution fails as `STRATEGY_VERSION_DEPRECATED` without fallback.
6. **Given** an incompatible version, **When** registration or execution is requested, **Then** it fails as `INCOMPATIBLE_CONTRACT_VERSION` without fallback.

### Edge Cases

- **Empty candle input**: Return an empty ordered signal sequence with execution provenance and no error.
- **Unsorted candles**: Reject the complete run as `INVALID_CONTEXT`; do not reorder silently or emit partial signals.
- **Duplicate candle timestamps**: Reject the complete run as `INVALID_CONTEXT`; do not choose one candle or emit partial signals.
- **Missing candles or incomplete input**: If the normalized input is marked incomplete or contains a known gap, reject the complete run as `INVALID_CONTEXT` and identify the completeness or gap issue.
- **Invalid upstream OHLCV values**: Reject the complete run as `INVALID_CONTEXT` before signal generation; do not coerce a value into validity.
- **Insufficient MA or RSI history**: Emit a deterministic HOLD for each valid warm-up candle and indicate that no evaluable strategy value was reached if the entire input is insufficient.
- **MA period outside its valid range**: Reject as `INVALID_PARAMETERS` before signal generation.
- **RSI period or threshold outside valid ranges, or lower threshold not below upper threshold**: Reject as `INVALID_PARAMETERS` before signal generation and identify each violating value.
- **Equal MA/RSI boundary values**: Equality alone is not a crossing and produces HOLD; BUY or SELL requires the strict crossing defined in the strategy rules.
- **Multiple signals sharing a timestamp**: Signals remain distinct through their provenance and signal identity; combined output uses the deterministic ordering stated in the strategy contract.
- **Unknown strategy ID**: Reject as `UNKNOWN_STRATEGY`; do not select a similarly named or latest strategy.
- **Duplicate registry entry**: Reject as `DUPLICATE_STRATEGY_ENTRY`; retain the original entry unchanged.
- **Incompatible contract version**: Reject registration or use as `INCOMPATIBLE_CONTRACT_VERSION`; retain existing compatible entries.
- **Requested historical version unavailable**: Reject as `STRATEGY_VERSION_UNAVAILABLE`; do not silently use the latest version.
- **Deprecated strategy version**: Preserve its metadata for historical traceability, but reject new execution as `STRATEGY_VERSION_DEPRECATED`; do not silently use the latest version.
- **Registration failure**: Make no registry change; every previously available strategy remains discoverable and usable.
- **Repeated evaluation**: Identical normalized candles, dataset identity, decision timestamp, Strategy Definition, and validated parameters produce an identical ordered sequence including actions, timestamps, strength, reasons, and signal identities.
- **Future or misaligned data**: Reject the complete run as `INVALID_CONTEXT` when a candle is after the decision timestamp or differs from the context's provider, pair, timeframe, dataset, or timestamp alignment.
- **Constant-price RSI input**: Once evaluable, equal aggregate gains and losses produce the neutral RSI value of 50 and therefore HOLD unless a prior value and current value form a strict configured crossing.
- **RSI input with gains but no losses, or losses but no gains**: Once evaluable, RSI is treated as 100 or 0 respectively; the configured strict crossing rules still determine the action.

## Requirements *(mandatory)*

### Traceability and Scope

**Authoritative product sources**: `docs/SRS.md` §§3.3, 3.4, 7.3, and the foundation portions of §7.4; `SE-FR-01` through `SE-FR-05`; `SP-FR-01` through `SP-FR-05`; `SE-US-01`; `SE-US-02`; `SP-US-01`; `SP-US-02`; and `SP-US-03`.

**Supporting governance and decision sources**: the project constitution, `docs/team-planning/SPECKIT_TEAM_WORKFLOW.md`, `docs/ARCHITECTURE.md`, and ADRs 003, 004, and 005. The architecture and these ADRs are currently Proposed; they inform this specification but do not independently approve implementation choices.

**In scope**:

- Common strategy behavior and normalized input/output requirements.
- MA and RSI strategy behavior, parameters, validation, and acceptance fixtures.
- BUY/SELL/HOLD signal semantics, determinism, traceability, and error behavior.
- Strategy registration, discovery, compatibility, and immutable versioning.
- The business-level strategy contract required by `BACKTEST_ENGINE` and TV4's `004-backtest-evaluation` feature.

**Out of scope**:

- Bollinger Bands and Support/Resistance implementation for this TV3 assignment.
- Complete MACD calculation; MACD is only an extensibility acceptance example unless separately approved.
- Composite strategies, majority voting, weights, thresholds, strategy search, and candidate generation.
- Backtest execution, trade simulation, position accounting, fees, slippage, profit and loss, equity curves, evaluation metrics, scoring, ranking, leaderboard behavior, and visualization.
- Realtime chart behavior, market-data acquisition or persistence, news and sentiment analysis, dynamic third-party code upload, untrusted plugin execution, live trading, and exchange order placement.
- Technology selection, code structure, storage design, endpoints, transports, and message formats.

### Functional Requirements

#### Common Strategy Execution and Input

- **FR-001**: Every strategy in this feature MUST accept the same business-level inputs: an exact Strategy Definition, its validated parameter set, and an immutable Strategy Context containing normalized market data.
- **FR-002**: A Strategy Context MUST identify the normalized dataset by provider, market pair, timeframe, dataset identity and version or equivalent immutable fingerprint, covered time range, completeness status, and decision timestamp.
- **FR-003**: Strategy input candles MUST retain their normalized identity and UTC timestamp, belong to the context's provider, pair, timeframe, and dataset, and be ordered strictly from earliest to latest with no duplicate timestamp.
- **FR-004**: The system MUST validate all parameters and the complete Strategy Context before calculation and MUST return no partial signals when either is invalid.
- **FR-005**: Strategy execution MUST use only the immutable context supplied for that run and MUST NOT acquire or mutate market data or access persistence, queues, network services, providers, or other external services during calculation.
- **FR-006**: No signal at a decision timestamp may depend on a candle later than that timestamp, and a context containing data later than its declared decision timestamp MUST be rejected.
- **FR-007**: The same exact Strategy Definition, validated parameters, immutable context, and normalized candles MUST produce the same ordered signal sequence on every execution.
- **FR-008**: Valid empty candle input MUST produce an empty signal sequence; valid non-empty input MUST produce exactly one signal for each input candle, including deterministic HOLD signals during warm-up.

#### MA and RSI Strategy Rules

- **FR-009**: The MA strategy MUST publish one integer `period` parameter with a default of 20 when omitted, a valid inclusive range of 2 through 500, and rejection of non-integer or out-of-range values.
- **FR-010**: MA at a candle MUST be the arithmetic mean of the close values for the configured number of consecutive candles ending at that candle. A candle becomes actionable when the current and immediately preceding candles both have an MA value; all earlier candles MUST produce HOLD.
- **FR-011**: MA MUST emit BUY when the previous close is less than or equal to its moving average and the current close is strictly greater than its moving average; SELL when the previous close is greater than or equal to its moving average and the current close is strictly less; otherwise HOLD. Equality alone MUST produce HOLD.
- **FR-012**: The RSI strategy MUST publish a required integer `period` parameter defaulting to 14 with an inclusive range of 2 through 200, a lower threshold defaulting to 30, and an upper threshold defaulting to 70.
- **FR-013**: RSI thresholds MUST be finite values in the inclusive range 0 through 100, and the lower threshold MUST be strictly less than the upper threshold; invalid period, threshold, type, or relationship values MUST be rejected before execution.
- **FR-014**: RSI MUST use consecutive close-to-close changes and the Wilder convention: the first evaluable average gain and loss are the arithmetic means across the configured period, and each later value carries the preceding averages forward using that same period. A candle becomes actionable only when it and its predecessor both have an RSI value; all earlier candles MUST produce HOLD.
- **FR-015**: RSI MUST emit BUY when the preceding evaluable RSI is less than or equal to the lower threshold and the current RSI is strictly greater than it; SELL when the preceding evaluable RSI is greater than or equal to the upper threshold and the current RSI is strictly less than it; otherwise HOLD. Equality alone MUST produce HOLD.
- **FR-016**: RSI MUST assign a neutral value of 50 when aggregate gains and losses are both zero, 100 when gains exist and losses are zero, and 0 when losses exist and gains are zero, so constant and one-directional boundary fixtures have one deterministic result.
- **FR-017**: MA and RSI MUST publish human-readable parameter definitions containing parameter name, business meaning, required status, accepted value type, default where applicable, inclusive or exclusive bounds, relationship rules, and validation error meaning.

#### Signal Contract for TV4

- **FR-018**: Each Signal MUST contain a stable signal identity, exact strategy ID, strategy type, immutable strategy version, Strategy Definition identity, exact validated parameters or an immutable reference to them, normalized dataset identity, UTC signal timestamp, action, and deterministic sequence position.
- **FR-019**: Signal action MUST be exactly one of `BUY`, `SELL`, or `HOLD`; a signal MAY also include finite strength on a documented strategy-specific scale and a human-readable reason.
- **FR-020**: Each signal timestamp MUST equal the timestamp of the normalized candle on which the decision is made; signals MUST be ordered by ascending candle timestamp within one execution.
- **FR-021**: If a consumer combines signals from multiple Strategy Definitions, equal-timestamp signals MUST be ordered by strategy ID, immutable strategy version, Strategy Definition identity, and sequence position, in that order, so ordering is reproducible.
- **FR-022**: A successful strategy result MUST expose enough execution provenance for `BACKTEST_ENGINE` to identify the contract version, exact Strategy Definition, validated parameters, immutable Strategy Context, input dataset, decision timestamp, warm-up state, and complete ordered signal sequence.
- **FR-023**: Warm-up HOLD signals MUST be distinguishable from evaluated HOLD signals, and an entirely insufficient-history result MUST explicitly state that no evaluable strategy value was reached.
- **FR-024**: `BACKTEST_ENGINE` MUST be able to consume the common result without knowing whether it came from MA, RSI, or another compliant strategy and without relying on strategy-specific conditions.

#### Registration, Discovery, Compatibility, and Versions

- **FR-025**: The Strategy Registry MUST expose a Strategy Registry Entry for each available strategy identity and immutable version, including strategy type, contract version, lifecycle status, parameter definition, and supported capability metadata.
- **FR-026**: MA and RSI MUST be registered and discoverable through the same mechanism and MUST NOT require consumers to maintain a hard-coded strategy-name list.
- **FR-027**: Registration MUST validate strategy identity, strategy type, immutable version, contract version, lifecycle status, parameter definition, and uniqueness before making an entry available.
- **FR-028**: Registration MUST reject duplicate identity-and-version entries, invalid metadata, invalid parameter definitions, and incompatible contract versions with an explicit error category and no partial registry change.
- **FR-029**: A failed registration MUST leave all existing registry entries unchanged, discoverable, and usable.
- **FR-030**: Adding another compliant strategy MUST require only that strategy's behavior, registration, metadata, parameter definition, and tests; it MUST NOT require strategy-specific behavior in Backtester, Evaluator, or Leaderboard.
- **FR-031**: Every Strategy Definition MUST identify an exact strategy ID, strategy type, immutable strategy version, contract version, and exact validated parameter set.
- **FR-032**: A Strategy Definition and validated parameter set MUST become immutable once referenced by a consumer; neither may be silently overwritten or reinterpreted.
- **FR-033**: A behavior change MUST create a new immutable strategy version, and a meaningfully different parameter set MUST create a distinct immutable Strategy Definition identity; both choices MUST preserve prior definitions.
- **FR-034**: Historical consumers MUST be able to resolve the exact available Strategy Definition they used after newer versions or definitions are registered.
- **FR-035**: Unknown strategy IDs, unavailable historical versions, deprecated versions requested for new execution, and incompatible contract versions MUST produce `UNKNOWN_STRATEGY`, `STRATEGY_VERSION_UNAVAILABLE`, `STRATEGY_VERSION_DEPRECATED`, and `INCOMPATIBLE_CONTRACT_VERSION` respectively, with no fallback to another or latest version.
- **FR-036**: A deprecated retained version MUST remain resolvable for historical metadata and provenance and MUST expose its deprecated status, but MUST be rejected for new execution; an unavailable version MUST fail rather than masquerade as deprecated.

#### Error Contract

- **FR-037**: The common contract MUST distinguish at least `INVALID_PARAMETERS`, `INVALID_CONTEXT`, `UNKNOWN_STRATEGY`, `DUPLICATE_STRATEGY_ENTRY`, `INVALID_STRATEGY_METADATA`, `INCOMPATIBLE_CONTRACT_VERSION`, `STRATEGY_VERSION_UNAVAILABLE`, and `STRATEGY_VERSION_DEPRECATED`.
- **FR-038**: Every failure MUST identify its category and the offending field, identity, version, or context rule in human-readable terms while returning no partial strategy or registry state.

### Key Entities

- **Strategy**: A deterministic signal-producing behavior that follows the common contract. It validates its declared parameters and analyzes only the immutable Strategy Context supplied to it; it does not execute trades or calculate rankings.
- **Strategy Definition**: An immutable, reproducible selection of a strategy ID, strategy type, strategy version, contract version, and exact Validated Parameter Set. Many definitions may refer to the same strategy version with different parameter sets, but each meaningfully distinct set has its own identity.
- **Strategy Context**: The immutable execution input describing one normalized dataset, its provider, market pair, timeframe, identity/version, covered range, completeness, ordered candle input, and decision timestamp. One execution uses one context.
- **Strategy Parameter Definition**: Published metadata describing one accepted parameter's meaning, required status, value type, default, range, relationship constraints, and validation outcomes. A strategy version owns one complete parameter definition.
- **Validated Parameter Set**: The exact parameter values confirmed against a Strategy Parameter Definition. It belongs to one Strategy Definition and becomes immutable when referenced.
- **Signal**: One timestamped analytical decision from a Strategy Definition for one normalized candle. It carries a stable identity, exact provenance, deterministic sequence position, one BUY/SELL/HOLD action, and optional strength and reason; it is not a trade or order.
- **Strategy Registry Entry**: Discoverable metadata connecting a strategy identity and immutable version to its contract version, status, parameter definition, and capabilities. It exposes strategy metadata but not strategy-specific calculation logic.
- **Contract Version**: The identifier for a mutually understood strategy input, output, validation, and error contract. It determines whether a strategy and consumer can interact without changing the contract's meaning.
- **Normalized Candle Reference/Input**: A traceable OHLCV observation identified by provider, market pair, timeframe, and UTC timestamp within an immutable normalized dataset. Strategy input preserves its dataset identity and chronological relationship.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Repeated execution with identical normalized candles, dataset identity, decision timestamp, strategy version, and parameters produces identical ordered signals in 100% of acceptance fixtures.
- **SC-002**: In 100% of successful fixtures, every emitted signal has a valid UTC candle-aligned timestamp, exact strategy and dataset provenance, a stable identity and sequence position, and exactly one of BUY, SELL, or HOLD.
- **SC-003**: Invalid parameters are rejected before signal generation in 100% of invalid-parameter fixtures, with every offending parameter identified.
- **SC-004**: Invalid, unsorted, duplicated, incomplete, future, or misaligned candle contexts are rejected before signal generation in 100% of corresponding fixtures.
- **SC-005**: MA and RSI acceptance suites each cover at least one normal, exact-boundary, crossing, warm-up, invalid-input, insufficient-history, and repeated-execution fixture, with all expected outcomes passing.
- **SC-006**: A compliant example strategy can be registered and discovered with zero changes to Backtester, Evaluator, or Leaderboard behavior and zero strategy-specific branches in those consumers.
- **SC-007**: Incompatible or otherwise failed registrations leave 100% of previously registered strategies discoverable and usable in acceptance tests.
- **SC-008**: Historical Strategy Definitions remain resolvable and unchanged in 100% of versioning fixtures after a newer strategy version or distinct parameterized definition is registered.
- **SC-009**: In 100% of resolution fixtures, unknown, unavailable, deprecated, and incompatible versions produce the documented distinct outcome and never silently fall back to the latest version.
- **SC-010**: TV4 can validate and consume MA, RSI, and one compliant example strategy through one documented input/output contract with zero dependency on MA-specific or RSI-specific behavior.
- **SC-011**: At least 95% of representative analysts can correctly identify a signal's action, decision timestamp, strategy version, parameters, dataset, and warm-up/evaluated status from the exposed result without implementation knowledge.
- **SC-012**: At least 95% of representative strategy developers can identify valid parameters and compatibility status from registry metadata without consulting a hard-coded strategy list or strategy calculation internals.

## Assumptions

- The normalized market-data boundary supplies UTC candles with provider, pair, timeframe, dataset identity/version, completeness, and valid OHLCV values; this feature validates that contract but does not acquire, repair, reorder, deduplicate, or persist market data.
- MA means a simple moving-average close-price crossover strategy for this assignment. Alternative moving-average families or price sources require a distinct strategy version and published parameter definition.
- RSI uses close-to-close changes and the conventional 0-to-100 scale. The exact calculation convention remains stable within an immutable strategy version; changing it requires a new version.
- A valid non-empty run emits one signal per input candle so warm-up and HOLD behavior are visible and candle alignment is lossless; an empty input returns an empty sequence.
- Parameter defaults apply only when a published optional value is omitted; invalid supplied values are never replaced silently.
- Signal strength and reason are optional because not every compliant strategy can provide meaningful values, but their semantics must be documented when present.
- Registry lifecycle status includes at least available and deprecated; status changes do not mutate the behavior or parameter meaning of an immutable version.
- The `BACKTEST_ENGINE` is a downstream consumer only. It supplies or receives the documented contract but trade execution, accounting, and evaluation remain outside this feature.
- SRS requirements for Bollinger Bands, Support/Resistance, and full MACD implementation remain product-level work allocated outside this narrower TV3 feature and are not silently considered complete here.

## Dependencies

- Feature 001 or another approved normalized-market-data owner must provide the normalized candle and immutable dataset identity semantics consumed by Strategy Context.
- TV3 and TV4 must review and agree on Strategy Definition identity/version, validated parameters, Strategy Context, timestamp alignment, signal fields and ordering, warm-up behavior, error categories, and compatibility expectations before planning is approved.
- Historical reproducibility depends on downstream consumers retaining the exact Strategy Definition, validated parameters, dataset identity, contract version, and ordered signals they consume.
