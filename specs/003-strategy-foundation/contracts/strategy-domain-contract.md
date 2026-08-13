# Strategy Domain Contract for TV4

**Owner**: TV3 — Strategy Foundation  
**Consumer**: TV4 — Backtest and Evaluation  
**Initial contract version**: `1.0.0`

This contract defines the in-process business boundary. It does not require HTTP, queue, database, or framework types.

## Consumer Inputs

TV4 supplies:

1. An exact immutable Strategy Definition containing strategy ID, type, strategy version, contract version, and validated parameters.
2. An immutable Strategy Context containing normalized dataset identity/version, provider, Market Pair, Timeframe, UTC range, decision timestamp, completeness, and strictly ordered Candles.
3. A supported contract-version range.

TV4 MUST NOT request “latest” implicitly. It MUST identify an exact strategy version and definition.

## Strategy Operation

```text
analyze(strategy_definition, immutable_strategy_context, supported_contract_range)
    -> StrategyAnalysisResult
    | CategorizedStrategyError
```

The operation is pure with respect to its supplied values: it does not load data, persist results, access a queue, call a provider, read a clock, or use an implicit random source.

## Strategy Context Rules

- All timestamps are UTC instants.
- Candles are closed normalized observations from one provider, pair, timeframe, and immutable dataset.
- Candles are strictly ascending by canonical `openTime` and contain no duplicate `openTime`; a Signal `timestamp` equals its associated Candle `openTime`.
- No Candle is after `decisionTimestamp`.
- The dataset is marked complete for its declared range; a complete empty range is valid.
- Invalid OHLCV, open, incomplete, gap-marked, unsorted, duplicate, future, or misaligned input rejects the whole operation as `INVALID_CONTEXT`.
- Validation never sorts, deduplicates, fills, coerces, or truncates supplied data silently.

## Result Contract

`StrategyAnalysisResult` contains:

| Field | Meaning |
|-------|---------|
| contractVersion | Exact strategy contract used |
| strategyDefinition | Exact definition ID, strategy ID/type/version, and parameter-schema fingerprint |
| validatedParameters | Canonical complete parameter values |
| contextProvenance | Dataset ID/version, context fingerprint, provider, pair, timeframe, range, and decision timestamp |
| historyState | `EMPTY`, `INSUFFICIENT`, or `EVALUABLE` |
| signals | Deterministically ordered immutable Signal sequence |

For complete empty input, `signals` is empty and `historyState` is `EMPTY`. For every valid non-empty input, `signals` has exactly the same length as the Candle sequence and contiguous zero-based sequence positions.

## Signal Contract

| Field | Required | Rule |
|-------|----------|------|
| id | Yes | Stable for identical definition/context/timestamp/position |
| strategyDefinitionId | Yes | Exact immutable definition |
| strategyId / strategyType / strategyVersion | Yes | Exact behavior provenance |
| contractVersion | Yes | Exact contract provenance |
| datasetId / datasetVersion | Yes | Exact market-data provenance |
| timestamp | Yes | Equals the associated Candle `openTime` |
| sequence | Yes | Contiguous zero-based order within the run |
| action | Yes | Exactly `BUY`, `SELL`, or `HOLD` |
| phase | Yes | `WARMUP` or `EVALUATED` |
| strength | No | Finite value on the strategy's declared scale |
| reason | No | Human-readable stable explanation |

Within one result, Signals are ordered by `(timestamp, sequence)`. When combining results, TV4 orders equal-timestamp Signals by `(strategyId, strategyVersion, strategyDefinitionId, sequence)`.

## Warm-up and Insufficient History

- Each valid Candle before the strategy is actionable produces HOLD with phase `WARMUP`.
- MA becomes actionable only when both the current and preceding Candle have an MA value.
- RSI becomes actionable only when both the current and preceding Candle have an RSI value.
- If the final Candle is still warm-up, `historyState` is `INSUFFICIENT`; otherwise it is `EVALUABLE`.
- Warm-up is a successful analysis state, not an error.

## Error Contract

Every error has `category`, human-readable `message`, and structured `issues`. No error returns partial Signals or mutates registry/definition state.

| Category | TV4 handling |
|----------|--------------|
| `INVALID_PARAMETERS` | Reject the run request before simulation |
| `INVALID_CONTEXT` | Reject the run request; do not repair data inside Strategy |
| `UNKNOWN_STRATEGY` | Surface exact missing ID; no fallback |
| `INCOMPATIBLE_CONTRACT_VERSION` | Reject until consumer/strategy contract is reconciled |
| `STRATEGY_VERSION_UNAVAILABLE` | Surface unavailable exact version; no fallback |
| `STRATEGY_VERSION_DEPRECATED` | Block new execution; retain historical provenance |

Registry-only failures `DUPLICATE_STRATEGY_ENTRY` and `INVALID_STRATEGY_METADATA` cannot damage already registered entries.

## Version Compatibility

- Version format is `MAJOR.MINOR.PATCH`.
- Different contract major versions are incompatible.
- A consumer declares an inclusive supported minor range for the shared major.
- Patch changes preserve contract meaning.
- New optional fields require a compatible minor version and safe unknown-field handling.
- Removing fields, changing required-field meaning, changing signal action semantics, or changing ordering/error meaning requires a new major contract version.
- Strategy behavior or parameter-schema semantic changes require a new strategy version.

## Determinism Fitness Fixture

TV3 and TV4 share one fixture containing an exact Strategy Definition, normalized dataset/context fingerprint, decision timestamp, and expected ordered Signals. Both features pass when repeated analysis yields byte-equivalent canonical result content and TV4 consumes it without MA/RSI-specific branching.

