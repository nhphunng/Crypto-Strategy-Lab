# Data Model: Strategy Foundation

## Modeling Rules

- Domain values are immutable after construction; API schemas and persistence rows map explicitly to domain objects.
- Python names use snake_case, public JSON uses camelCase, timestamps use ISO-8601 UTC, and decimal market values serialize as strings.
- Strategy calculation is transient. Only immutable Strategy Definitions and their exact parameter sets are persisted by this feature.
- A registry entry describes available executable behavior; a Strategy Definition describes one reproducible use of that behavior.
- No entity contains trade, position, fee, slippage, profit, metric, score, ranking, or leaderboard behavior.

## Entity: Strategy Registry Entry

Represents one trusted executable strategy version available to consumers.

| Field | Type | Rules |
|-------|------|-------|
| strategyId | string | Stable lowercase identifier; non-empty; unique with strategyVersion |
| strategyType | string | Stable capability family such as `MA` or `RSI` |
| displayName | string | Human-readable and non-empty |
| strategyVersion | semantic version | Immutable behavior version |
| contractVersion | semantic version | Version of the common input/output contract |
| status | enum | `AVAILABLE`, `DEPRECATED`, or `UNAVAILABLE` |
| parameterDefinition | Strategy Parameter Definition | Complete schema owned by this strategy version |
| capabilities | set of enum values | Declares optional support such as strength or reason |

**Identity**: `(strategyId, strategyVersion)`.

**Invariants**:

1. Duplicate identities are rejected atomically.
2. Metadata and parameter definitions validate before the entry becomes visible.
3. `AVAILABLE` permits new analysis; `DEPRECATED` permits historical metadata resolution only; `UNAVAILABLE` cannot be executed or resolved as behavior.
4. Registry entries contain metadata and an executable contract reference, not persistence or concrete downstream behavior.

## Entity: Strategy Parameter Definition

Describes every accepted parameter for one strategy version.

| Field | Type | Rules |
|-------|------|-------|
| name | string | Unique within the owning strategy version |
| description | string | Human-readable business meaning |
| valueType | enum | `INTEGER` or `DECIMAL` for MA/RSI scope |
| required | boolean | Whether omission is invalid |
| defaultValue | typed value or null | Must itself satisfy all constraints |
| minimum / maximum | typed value or null | Bound with explicit inclusive flags |
| allowedValues | set or null | Optional finite domain |
| relationshipRules | ordered rules | Cross-parameter rules such as lower threshold below upper threshold |

### Built-in parameter definitions

| Strategy | Parameter | Type | Default | Validity |
|----------|-----------|------|---------|----------|
| MA | period | integer | 20 | Inclusive `2..500` |
| RSI | period | integer | 14 | Inclusive `2..200` |
| RSI | lowerThreshold | decimal | 30 | Inclusive `0..100`; strictly below upperThreshold |
| RSI | upperThreshold | decimal | 70 | Inclusive `0..100`; strictly above lowerThreshold |

## Entity: Validated Parameter Set

The exact canonical parameter values used by one Strategy Definition.

| Field | Type | Rules |
|-------|------|-------|
| values | immutable ordered map | Contains every effective value after declared defaults; no unknown keys |
| schemaFingerprint | string | Identifies the exact parameter definition used for validation |
| canonicalFingerprint | string | Deterministic digest of canonical names, types, and values |

**Invariants**:

- Validation is all-or-nothing and reports every offending parameter.
- Numerically equivalent accepted input has one canonical representation.
- Once included in a Strategy Definition, the set cannot change.

## Entity: Strategy Definition

An immutable persisted aggregate selecting one exact behavior version and parameter set.

| Field | Type | Rules |
|-------|------|-------|
| id | UUID | Stable immutable identity |
| strategyId | string | Must resolve to a registry entry |
| strategyType | string | Must match the entry |
| strategyVersion | semantic version | Exact; never implicit latest |
| contractVersion | semantic version | Exact contract used by the definition |
| parameters | JSON-compatible immutable map | Canonical Validated Parameter Set values |
| parameterSchemaFingerprint | string | Exact schema used to validate parameters |
| contentFingerprint | string | Deterministic digest of all behavior/parameter identity fields |
| createdAt | UTC instant | Audit time; excluded from content fingerprint |

**Identity and constraints**:

- Primary key `id`.
- Unique `contentFingerprint`; repeated create-or-resolve of identical content returns the same aggregate.
- A reused `id` with different content fails; there is no update of immutable fields.
- Index `(strategyId, strategyVersion)` supports exact historical lookup.
- Database storage uses one insert-only `strategy_definitions` table; delete/update of referenced definitions is outside feature operations.

## Entity: Normalized Candle Reference/Input

An upstream immutable market observation consumed by Strategy Context.

| Field | Type | Rules |
|-------|------|-------|
| provider | string | Matches the owning dataset |
| pair | string | Canonical Market Pair such as `BTCUSDT` |
| timeframe | canonical value | Matches the owning dataset |
| openTime | UTC instant | Strictly increasing within the context; this is the canonical Candle interval-opening timestamp owned by Feature 001 |
| open / high / low / close / volume | decimal | Valid upstream OHLCV invariants; volume non-negative |
| closed | boolean | Strategy analysis uses normalized closed historical observations for this feature |

**Identity**: `(provider, pair, timeframe, openTime)` within the upstream normalized-data contract. Strategy `Signal.timestamp` equals the associated Candle `openTime`; `timestamp` is not a second Candle identity field.

## Entity: Strategy Context

Immutable transient input to one strategy execution.

| Field | Type | Rules |
|-------|------|-------|
| datasetId | UUID/string | Required immutable dataset identity |
| datasetVersion | string | Required version/checksum/fingerprint |
| provider | string | Same for every Candle |
| pair | string | Same for every Candle |
| timeframe | canonical value | Same for every Candle |
| rangeStart / rangeEnd | UTC instant | Declared covered range; `rangeStart <= rangeEnd` when non-empty |
| decisionTimestamp | UTC instant | No Candle may be later |
| completeness | enum | `COMPLETE` is required for execution |
| candles | immutable ordered sequence | Strictly increasing, no duplicates, aligned to context |
| contextFingerprint | string | Deterministic digest of dataset provenance, decision time, and Candle content identities/values |

**Validation result**: empty complete input is valid; unsorted, duplicate, invalid, incomplete, future, open, or misaligned data produces `INVALID_CONTEXT` and no Signals.

## Entity: Strategy

A stateless behavior registered under one Strategy Registry Entry.

| Operation | Input | Output |
|-----------|-------|--------|
| validate parameters | raw parameter map | Validated Parameter Set or `INVALID_PARAMETERS` |
| analyze | Strategy Definition + Strategy Context | Strategy Analysis Result or categorized error |

The behavior has no persisted fields and cannot read mutable external state.

## Entity: Signal

One immutable analytical decision aligned to one input Candle.

| Field | Type | Rules |
|-------|------|-------|
| id | string | Deterministically derived and stable across identical runs |
| strategyDefinitionId | UUID | Exact persisted definition |
| strategyId / strategyType / strategyVersion | identity fields | Exact registry provenance |
| contractVersion | semantic version | Exact output contract |
| datasetId / datasetVersion | identity fields | Exact normalized-data provenance |
| timestamp | UTC instant | Equals the associated Candle timestamp |
| sequence | non-negative integer | Zero-based position; strictly contiguous |
| action | enum | Exactly `BUY`, `SELL`, or `HOLD` |
| phase | enum | `WARMUP` or `EVALUATED` |
| strength | nullable decimal | Finite and within the strategy's declared scale when present |
| reason | nullable string/code | Human-readable stable reason when provided |

**Identity input**: Strategy Definition ID, context fingerprint, timestamp, and sequence.

## Entity: Strategy Analysis Result

A transient immutable envelope returned to analysts and TV4.

| Field | Type | Rules |
|-------|------|-------|
| strategyDefinition | immutable reference/summary | Exact identity and version |
| validatedParameters | Validated Parameter Set | Exact values used |
| contextProvenance | immutable summary | Dataset, pair, timeframe, range, decision timestamp, fingerprint |
| contractVersion | semantic version | Exact contract |
| historyState | enum | `EMPTY`, `INSUFFICIENT`, or `EVALUABLE` |
| signals | ordered sequence of Signal | Empty only for empty input; otherwise one per Candle |

## Entity: Contract Version

| Component | Rules |
|-----------|-------|
| major | Breaking input/output/error semantic changes |
| minor | Backward-compatible additions within an explicitly supported range |
| patch | Clarifications/fixes that preserve contract meaning |

A consumer declares supported major and minor range. Strategy registration and execution fail as `INCOMPATIBLE_CONTRACT_VERSION` outside that range.

## Error Model

| Category | Observable cause | State guarantee |
|----------|------------------|-----------------|
| `INVALID_PARAMETERS` | Missing, unknown, wrong-type, out-of-range, or relationally invalid parameter | No definition created and no Signals |
| `INVALID_CONTEXT` | Unsorted, duplicate, incomplete, invalid, future, open, or misaligned Candle/context | No Signals |
| `UNKNOWN_STRATEGY` | Strategy ID is not registered | No fallback |
| `DUPLICATE_STRATEGY_ENTRY` | Same registry identity registered twice | Original registry unchanged |
| `INVALID_STRATEGY_METADATA` | Invalid identity, version, capability, or parameter definition | Registry unchanged |
| `INCOMPATIBLE_CONTRACT_VERSION` | Contract version is outside supported range | Registry/definition unchanged; no Signals |
| `STRATEGY_VERSION_UNAVAILABLE` | Exact known/historical version cannot be resolved | No fallback |
| `STRATEGY_VERSION_DEPRECATED` | New analysis requests a deprecated retained version | Historical metadata remains resolvable; no Signals |

## State Transitions

### Registry Entry lifecycle

```text
UNREGISTERED -> AVAILABLE -> DEPRECATED -> UNAVAILABLE
```

- Registration validation failure leaves `UNREGISTERED` and all existing entries unchanged.
- `DEPRECATED` remains metadata-resolvable but blocks new analysis.
- Lifecycle changes never alter behavior, version, or parameter schema identity.

### Strategy Definition lifecycle

```text
VALIDATED -> PERSISTED -> REFERENCED
```

- Identical validated content may resolve the existing `PERSISTED` definition.
- `PERSISTED` and `REFERENCED` content are immutable.
- Behavior changes create a new Strategy Version; parameter changes create a new definition identity.

### Strategy analysis

```text
REQUESTED
  -> REJECTED (categorized error, no Signals)
  -> VALIDATED
  -> ANALYZED (EMPTY | INSUFFICIENT | EVALUABLE, ordered Signals)
```

## Relationships

- One Strategy Registry Entry owns one Strategy Parameter Definition and identifies one Strategy behavior version.
- One Registry Entry may have many immutable Strategy Definitions with different Validated Parameter Sets.
- One Strategy Definition and one Strategy Context produce one Strategy Analysis Result.
- One non-empty Strategy Context Candle corresponds to exactly one Signal in that result.
- TV4 references the exact Strategy Definition, Strategy Context provenance, Contract Version, and ordered Signals without depending on concrete Strategy type.

