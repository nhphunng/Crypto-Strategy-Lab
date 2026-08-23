# Feature Specification: Strategy Foundation

**Feature Branch**: `feat/003-strategy-foundation-spec-plan`

**Created**: 2026-08-13

**Status**: Ready for implementation — SRS traceability, ADR-006 isolation and generated-strategy security/source policy approved 2026-08-23

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

---

### User Story 5 - Generate a Strategy from an Existing Strategy Name (Priority: P2)

As an `ANALYST`, I want to provide the name of an existing trading strategy so that the system can produce, validate, and register reusable executable strategy logic without requiring me to write code. This story traces to SRS story `SP-US-04`.

**Why this priority**: A strategy name is the shortest path from an analyst's intent to reusable strategy behavior and directly expands the strategy catalog.

**Independent Test**: Submit well-known, ambiguous, unsupported, duplicate, and misspelled strategy names; verify intent extraction, generated draft provenance, validation, user confirmation, atomic activation, and later discovery without relying on MA or RSI behavior.

**Acceptance Scenarios**:

1. **Given** a sufficiently specific existing strategy name, **When** the analyst requests generation, **Then** the system creates one structured draft containing normalized strategy identity, assumptions, parameters, rules, source provenance, generated executable logic, and validation status.
2. **Given** a name that has multiple materially different interpretations, **When** generation is requested, **Then** the system presents the interpretations and does not generate or activate an arbitrary version until the analyst selects one.
3. **Given** a generated draft that passes contract, safety, determinism, and fixture validation, **When** the analyst confirms activation, **Then** the system stores an immutable Strategy Version and registers it for later discovery and execution.
4. **Given** generated logic that fails any required validation, **When** activation is attempted, **Then** registration fails atomically, the unsafe logic is never executable through the registry, and the analyst receives actionable validation findings.
5. **Given** an already registered strategy with equivalent normalized rules and parameters, **When** another generation request resolves to the same content, **Then** the system identifies the existing reusable version rather than silently creating a duplicate.

---

### User Story 6 - Extract One or More Strategies from Source Content (Priority: P2)

As an `ANALYST`, I want to submit a natural-language description, webpage URL, or equivalent source content so that the system can extract one or more structured strategies for review and reuse. This story traces to SRS story `SP-US-05`.

**Why this priority**: Strategy knowledge commonly appears as prose or web content and may describe several separable strategies or variants.

**Independent Test**: Submit direct prose, a supported webpage, content containing multiple strategies, irrelevant content, inaccessible or unsafe URLs, conflicting rules, and content with incomplete attribution; verify extraction boundaries, provenance, draft separation, and failure isolation.

**Acceptance Scenarios**:

1. **Given** a natural-language description containing one complete strategy, **When** extraction completes, **Then** the system creates one structured draft and identifies which source statements support its entry, exit, parameter, warm-up, and data requirements.
2. **Given** source content containing multiple independently executable strategies or explicit variants, **When** extraction completes, **Then** the system creates separate drafts, preserves their source relationships, and allows each draft to be reviewed, validated, accepted, or rejected independently.
3. **Given** a webpage URL, **When** the page can be retrieved under the source-access policy, **Then** the system records the submitted URL, canonical URL when available, retrieval time, content fingerprint, and extracted strategy evidence.
4. **Given** a page that is inaccessible, unsupported, too large, redirects to a prohibited destination, or cannot be attributed, **When** ingestion is attempted, **Then** the request fails with a source-specific reason and creates no executable strategy.
5. **Given** source content with contradictory or materially incomplete trading rules, **When** extraction completes, **Then** affected drafts remain `NEEDS_REVIEW`, list the contradictions or missing rules, and cannot be activated.
6. **Given** mixed relevant and irrelevant source content, **When** extraction completes, **Then** only supported strategy rules appear in drafts and unsupported LLM additions are labeled as assumptions requiring review.

---

### User Story 7 - Reuse Generated Strategies in Later Workflows (Priority: P1)

As an `ANALYST`, I want every approved generated strategy to remain stored and discoverable so that I can use the exact version in later analysis, backtest, search, and composite-strategy workflows. This story traces to SRS story `SP-US-06`.

**Why this priority**: Generation has durable value only when approved results enter the same immutable catalog and provenance model as built-in strategies.

**Independent Test**: Activate a generated strategy, restart the application, discover and resolve it, use it through the common Strategy contract, create a revised version, and verify old workflow references remain unchanged.

**Acceptance Scenarios**:

1. **Given** an activated generated Strategy Version, **When** the system restarts or a later workflow lists compatible strategies, **Then** the exact version remains stored, discoverable, and distinguishable as LLM-generated.
2. **Given** a later workflow selects a generated strategy, **When** it resolves the exact Strategy Definition, **Then** it receives the same common contract, parameter schema, executable behavior, provenance, and lifecycle guarantees as a built-in strategy.
3. **Given** a user edits source rules, assumptions, parameters, or generated behavior, **When** the revision is approved, **Then** the system creates a new immutable version and preserves all references to the earlier version.
4. **Given** a generation request produced several drafts, **When** only some are activated, **Then** later workflows discover only activated compatible versions while rejected or review-pending drafts remain non-executable.
5. **Given** the model, prompt, source, or validation policy later changes, **When** an existing generated version is resolved, **Then** its stored behavior and generation provenance remain unchanged.

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
- **Unknown or misspelled strategy name**: Return `STRATEGY_INTENT_UNRESOLVED` with possible matches when confidence is insufficient; do not invent a strategy silently.
- **Ambiguous strategy name**: Preserve the candidate interpretations and require selection before code generation or activation.
- **Prompt injection or instructions embedded in source content**: Treat retrieved content only as untrusted reference material; embedded instructions cannot alter system policy, validation, tool access, or activation rules.
- **Private, local, redirecting, or otherwise prohibited URL**: Reject as `SOURCE_ACCESS_DENIED`; do not fetch internal network resources, local files, credentials, or unsupported schemes.
- **Unavailable, paywalled, script-only, oversized, binary, or unsupported source**: Return a source-specific failure or request user-supplied text; create no executable strategy from partial unseen content.
- **Multiple strategies in one source**: Create separately identifiable drafts with shared source provenance; failure or rejection of one draft does not block valid sibling drafts.
- **Contradictory, incomplete, or non-deterministic rules**: Keep the draft non-executable and enumerate unresolved rules rather than filling them silently.
- **LLM timeout, refusal, malformed output, or provider unavailability**: Preserve the request and safe source snapshot where permitted, record a retryable failure, and do not partially register output.
- **Generated syntax/import/contract/test failure**: Quarantine the artifact, retain validation findings, and leave the active registry unchanged.
- **Disallowed capability or dependency**: Reject logic that attempts network, filesystem, process, environment, credential, clock, randomness, database, queue, or exchange-order access outside the approved strategy sandbox contract.
- **Equivalent generated content**: Resolve the existing immutable version by canonical content fingerprint and retain the new request's provenance link without duplicating executable behavior.
- **Model or prompt changes**: Do not mutate an existing generated version; regeneration produces a new draft and, if activated, a new immutable version.

## Requirements *(mandatory)*

### Traceability and Scope

**Authoritative product sources**: `docs/SRS.md` §§3.3, 3.4, 7.3, and the foundation portions of §7.4; `SE-FR-01` through `SE-FR-05`; `SP-FR-01` through `SP-FR-05`; `SE-US-01`; `SE-US-02`; `SP-US-01`; `SP-US-02`; and `SP-US-03`.

**Supporting governance and decision sources**: the project constitution, `docs/team-planning/SPECKIT_TEAM_WORKFLOW.md`, Accepted `docs/ARCHITECTURE.md`, ADRs 002–006, and approved `docs/GENERATED_STRATEGY_SECURITY_POLICY.md`. ADR-006 extends ADR-004 with the required generated-code isolation boundary.

**Canonical amendment traceability**: User Stories 5–7 map to SRS `SP-US-04`, `SP-US-05`, and `SP-US-06`. FR-039–FR-060 map to SRS `SP-FR-06` through `SP-FR-20`: source/name input (`06–07`), extraction/drafts (`08–09`), artifact/validation/activation (`10–12`), web/prompt/source governance (`13–16`), and durable origin-safe immutable reuse (`17–20`).

**In scope**:

- Common strategy behavior and normalized input/output requirements.
- MA and RSI strategy behavior, parameters, validation, and acceptance fixtures.
- BUY/SELL/HOLD signal semantics, determinism, traceability, and error behavior.
- Strategy registration, discovery, compatibility, and immutable versioning.
- LLM-assisted creation from an existing strategy name.
- Extraction of one or more strategy drafts from natural language, webpage URLs, and equivalent supported source content.
- Validation, approval, persistent storage, registration, versioning, provenance, and later reuse of generated strategies.
- The business-level strategy contract required by `BACKTEST_ENGINE` and TV4's `004-backtest-evaluation` feature.

**Out of scope**:

- Bollinger Bands and Support/Resistance implementation for this TV3 assignment.
- Complete MACD calculation; MACD is only an extensibility acceptance example unless separately approved.
- Composite strategies, majority voting, weights, thresholds, strategy search, and candidate generation.
- Backtest execution, trade simulation, position accounting, fees, slippage, profit and loss, equity curves, evaluation metrics, scoring, ranking, leaderboard behavior, and visualization.
- Realtime chart behavior, market-data acquisition or persistence, news and sentiment analysis, arbitrary user-authored code upload, live trading, and exchange order placement.
- Autonomous activation of generated code that has not completed required safety/contract validation and user confirmation.
- Bypassing ADR-006, the approved source-access/security policy, validation, confirmation, or provenance controls.
- Authenticated/private webpage crawling, arbitrary user-authored code upload, public marketplace publication, multi-user ownership/moderation, or second-reviewer workflows.
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

#### LLM-Assisted Strategy Generation and Extraction

- **FR-039**: The system MUST accept a generation request containing exactly one supported source mode: an existing strategy name, natural-language content, a webpage URL, or another explicitly supported source representation.
- **FR-040**: Every request MUST produce a durable Generation Request record with source type, user-supplied input or permitted reference, request time, status, and correlation identity before generated output can be activated.
- **FR-041**: For a strategy name, the system MUST resolve the intended trading concept and MUST stop for user selection when multiple materially different interpretations remain plausible.
- **FR-042**: For source content, the system MUST identify zero, one, or multiple independently executable strategy candidates and MUST preserve evidence linking each extracted rule to the submitted source or label it as an explicit assumption.
- **FR-043**: A generated Strategy Draft MUST contain a normalized name, description, required data, entry/exit/HOLD rules, warm-up behavior, parameter definitions/defaults/ranges, determinism assumptions, risk or position assumptions that affect signals, source provenance, and generation provenance.
- **FR-044**: The system MUST generate executable Python strategy logic that targets the common Strategy contract and MUST NOT grant generated logic capabilities outside that contract.
- **FR-045**: Generated output MUST be treated as untrusted and non-executable until it passes syntax, import allowlist, contract compatibility, parameter-schema, prohibited-capability, determinism, no-look-ahead, resource-bound, and generated-fixture validation.
- **FR-046**: Validation MUST be all-or-nothing per Strategy Draft, MUST retain structured findings, and MUST NOT alter the active registry when any required check fails.
- **FR-047**: The system MUST present extracted rules, explicit assumptions, source evidence, validation findings, and generated version metadata for user review before activation.
- **FR-048**: Only a draft that has passed all required validations and received explicit user confirmation MAY transition to an activated reusable Strategy Version.
- **FR-049**: A source containing multiple strategies MUST produce independently reviewable drafts so that validation, rejection, correction, and activation of one candidate do not determine sibling outcomes.
- **FR-050**: Web source ingestion MUST enforce an approved access policy covering scheme, redirect, destination, size, content type, timeout, and private/local network restrictions before content is supplied to the LLM.
- **FR-051**: Retrieved source content MUST be treated as untrusted data; source instructions MUST NOT modify generation policy, validation rules, system prompts, credentials, tool permissions, or activation decisions.
- **FR-052**: Generated strategy identity and version content MUST include canonical fingerprints of structured rules, parameter schema, executable artifact, contract version, and validation policy so equivalent output can be detected and historical behavior cannot drift.
- **FR-053**: The system MUST record generation provenance sufficient to identify source snapshots or fingerprints, source attribution, model/provider and model version, prompt/template version, generation parameters, generation time, validation-policy version, validation result, and confirming actor or process.
- **FR-054**: Source content and generated artifacts MUST follow configured retention, attribution, privacy, and licensing policies; the system MUST prevent activation when required provenance or permitted-use evidence is missing.

#### Storage, Registration, and Reuse of Generated Strategies

- **FR-055**: Every activated generated strategy MUST be durably stored as an immutable Strategy Version and registered through the same discovery mechanism used by built-in strategies.
- **FR-056**: Generated strategies MUST expose the same Strategy Definition, parameter, Signal, compatibility, lifecycle, determinism, and provenance contract to downstream workflows as other registered strategies.
- **FR-057**: Discovery MUST distinguish built-in and LLM-generated origins and MUST expose generation/validation provenance without exposing prompts, source content, or sensitive data that the requester is not permitted to view.
- **FR-058**: Revisions to source rules, assumptions, parameters, generated logic, contract meaning, or validation-relevant behavior MUST create a new immutable draft and activated version; existing versions MUST never be overwritten.
- **FR-059**: Drafts in `PENDING_GENERATION`, `NEEDS_REVIEW`, `VALIDATING`, `VALIDATION_FAILED`, `REJECTED`, or `ARCHIVED` states MUST NOT be executable or discoverable as available strategies in later workflows.
- **FR-060**: The system MUST support exact later resolution of an activated generated version after restart and after model, prompt, source, or validation-policy changes, without regenerating its executable artifact.

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
- **Strategy Generation Request**: A durable request that captures one supported input mode, lifecycle state, correlation, and permitted source reference for producing strategy drafts.
- **Strategy Source Snapshot**: An immutable, attributable representation or fingerprint of the name, text, webpage, or equivalent content used during extraction.
- **Generated Strategy Draft**: A non-executable review object containing structured trading rules, assumptions, parameter metadata, generated artifact reference, source evidence, generation provenance, and validation status.
- **Generated Strategy Artifact**: Immutable Python logic produced for one draft and fingerprinted for validation and later exact execution only after activation.
- **Strategy Validation Report**: Versioned results for contract, safety, determinism, no-look-ahead, resource, import, and fixture checks against one exact artifact.
- **Strategy Generation Provenance**: Immutable metadata linking source, model, prompt/template, artifact, validation policy/result, and activation confirmation.

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
- **SC-013**: In 100% of acceptance fixtures, a sufficiently specific strategy name produces a reviewable structured draft or a clear unresolved-intent outcome; no ambiguous request is silently activated.
- **SC-014**: In 100% of multi-strategy source fixtures, the system creates the expected number of independently reviewable drafts and preserves evidence for every extracted trading rule or labels it as an assumption.
- **SC-015**: Zero generated artifacts that fail a required safety, contract, determinism, no-look-ahead, resource, import, or fixture check become executable through the active registry.
- **SC-016**: In 100% of activation fixtures, only user-confirmed drafts with passing validation become discoverable, and failed or rejected siblings remain non-executable.
- **SC-017**: Every activated generated strategy is discoverable after restart and can be consumed through the common Strategy contract by at least analysis and one downstream workflow without concrete-strategy branching.
- **SC-018**: In 100% of generated-version fixtures, source, model, prompt/template, artifact, contract, and validation-policy provenance is resolvable without changing the stored executable behavior.
- **SC-019**: Duplicate generation of canonically equivalent rules and behavior creates zero duplicate executable versions while retaining traceability to each request.
- **SC-020**: At least 90% of representative analysts can submit a supported source, understand extracted rules and assumptions, identify validation blockers, and activate an eligible draft in under 10 minutes without writing code.

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
- “Any existing strategy” means any strategy the LLM can identify well enough to express within the current normalized-data, deterministic BUY/SELL/HOLD contract; unsupported multi-asset, discretionary, stateful, proprietary, or execution-dependent concepts remain review-blocked rather than being approximated silently.
- The working UX baseline requires explicit user confirmation after reviewing structured rules, assumptions, provenance, and passing validation. Autonomous activation is not assumed.
- A webpage is processed from a policy-compliant immutable source snapshot or fingerprint; later page changes do not mutate a generated version.
- One source may yield zero, one, or many drafts. The system does not force irrelevant content into a strategy.
- Generated logic is never trusted merely because it was produced by the configured LLM; activation depends on independent validation and the approved isolation boundary.

## Approved Decisions and Implementation Gate

- **AD-001 — Canonical traceability**: SRS 0.2 approves `SP-US-04..06` and `SP-FR-06..20`; local stories/requirements map as stated above.
- **AD-002 — Generated-code isolation**: Accepted ADR-006 requires an ephemeral non-root, read-only, networkless, secretless, capability-dropped sandbox with 1 CPU, 256 MiB memory, 32 PIDs, 16 MiB temporary storage, 1 MiB output and 5-second invocation timeout.
- **AD-003 — Source rights and retention**: The approved security policy permits public HTTPS/443 and user-supplied text under strict SSRF/redirect/content/rights controls; raw content retention is at most 30 days and activated provenance keeps minimal evidence/fingerprints.
- **AD-004 — Catalog and confirmation**: The trusted single-workspace MVP uses one global catalog and exact requester confirmation. It does not invent RBAC or a second reviewer.
- **AD-005 — LLM service policy**: The application uses a provider-neutral port; live generation is enabled only for a configured provider that excludes submitted content from training and uses minimum available retention. Tests use deterministic recorded outputs.
- **AD-006 — Artifact lifecycle**: Exact artifact digest is verified on load; policy tightening may suspend execution pending immutable revalidation but never rewrites artifact bytes or historical provenance.

**Implementation gate result**: PASS as of 2026-08-23. Any implementation deviation from these approved decisions requires the corresponding SRS/policy/ADR amendment first.

## Dependencies

- Feature 001 or another approved normalized-market-data owner must provide the normalized candle and immutable dataset identity semantics consumed by Strategy Context.
- The approved TV3↔TV4 contract baseline covers Strategy Definition identity/version, validated parameters, Strategy Context, timestamp alignment, signal fields/order, warm-up behavior, errors and compatibility; implementation changes to that boundary require both owners to review the contract and shared fixtures before merge.
- Historical reproducibility depends on downstream consumers retaining the exact Strategy Definition, validated parameters, dataset identity, contract version, and ordered signals they consume.
- LLM-assisted implementation depends on approved model access, prompt/template versioning, a source-ingestion adapter, durable artifact/provenance storage, and an isolated generated-code validation/execution boundary.
- Live-provider configuration is environment-dependent; implementation and deterministic acceptance tests proceed through the provider-neutral port without embedding a provider credential or making the core suite depend on live service availability.
