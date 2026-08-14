# Data Model: Deterministic Backtest and Evaluation

## Modeling Rules

- Domain values are immutable; API DTOs and persistence rows map explicitly.
- JSON uses camelCase, Python/database use snake_case, timestamps are UTC, decimals serialize as plain strings.
- Business-result tables are append-only. Audit timestamps are excluded from content fingerprints.
- Feature 001 owns Candle/Dataset rows; Feature 003 owns Strategy Definition behavior; Feature 004 stores immutable references and consumed Signal snapshots.

## BacktestRun

| Field | Type | Rules |
|---|---|---|
| id / runId | UUID | Stable Backtest Run identity |
| jobId | UUID | Unique idempotency/correlation identity reserved for later workers |
| status | enum | `REQUESTED`, `RUNNING`, `COMPLETED`, `FAILED` |
| datasetId / datasetSchemaVersion / datasetChecksum | identity | Exact Feature 001 `COMPLETE` dataset |
| provider / pair / timeframe / startTime / endTime | values | Must match dataset; range is `[startTime,endTime)` |
| strategyDefinitionId / strategyId / strategyVersion / contractVersion | identity | Exact Feature 003 definition/contract |
| parameterFingerprint / contextFingerprint | string | Exact consumed Strategy provenance |
| executionPolicyId / executionPolicyVersion | identity | Exact immutable rules |
| initialCapital / feeRate / slippageRate | decimal | Capital positive; rates non-negative |
| randomSeed | integer | Explicit even when current engine has no randomness |
| requestedAt / startedAt / completedAt | UTC instant | Audit lifecycle; excluded from result checksum |
| failureCode | nullable stable code | Set only for `FAILED` |

State transitions: `REQUESTED → RUNNING → COMPLETED | FAILED`. Completed/failed runs are terminal in this feature.

## ExecutionPolicy

Immutable versioned value containing `NEXT_CANDLE_OPEN`, `LONG_ONLY`, maximum positions `1`, `ALL_AVAILABLE_CASH`, fee/slippage semantics, redundant-Signal rules, quantity/money precision, and `FORCE_CLOSE_FINAL_CANDLE`.

## SignalSnapshot

Stores an internal UUID deterministically derived from Backtest Result ID plus the exact Feature 003 source Signal ID, while retaining that source ID unchanged. It also copies sequence, timestamp, action, phase, optional strength/reason, Strategy/Dataset versions, and Strategy Analysis Result fingerprint. Trade references use the snapshot UUID required by Feature 005. Unique `(backtest_result_id, sequence)` and `(backtest_result_id, source_signal_id)`.

## Trade

| Field | Type | Rules |
|---|---|---|
| id | UUID | Stable within Backtest Result |
| backtestResultId | UUID | Required parent |
| sequence | integer | Contiguous zero-based closed-Trade order |
| entrySignalId / exitSignalId | nullable ID | Exit null only for forced range close |
| entryTime / exitTime | UTC instant | Actual fill times; ordered |
| entryReferencePrice / exitReferencePrice | decimal | Next-open or final-close reference |
| entryPrice / exitPrice | decimal | Adverse-slippage fill prices |
| side | enum | `LONG` only in v1 |
| quantity | decimal | Positive, max 18 decimal places |
| entryFee / exitFee | decimal | Non-negative |
| profitLoss / returnPercent | decimal | Reconciles with cash changes |
| closeReason | enum | `SELL_SIGNAL`, `END_OF_RANGE` |

## EquityPoint

One point per input Candle, ordered by position. Stores Candle open time, close valuation time, cash, quantity, close price, position value, total equity, and optional event reference. The final point equals Backtest Result final equity.

## BacktestResult

| Field | Type | Rules |
|---|---|---|
| id | UUID | Immutable |
| jobId / runId | UUID | Unique correlation/idempotency |
| inputFingerprint | SHA-256 | Canonical complete input identity |
| resultChecksum | SHA-256 | Canonical provenance, Signals, Trades, Equity Curve, final equity |
| historyState | enum | `EMPTY`, `INSUFFICIENT`, `EVALUABLE` |
| tradeState | enum | `NO_TRADES`, `HAS_TRADES` |
| initialCapital / finalEquity | decimal | Positive/reconcilable |
| signalCount / tradeCount / equityPointCount | integer | Exact child counts |
| executionDurationMs | integer | Observability only; excluded from checksum |
| provenance | immutable fields | Dataset, Strategy, execution policy/configuration |

Unique `jobId`; repeated identical content resolves the same result, conflicting content for the same job fails closed.

## EvaluationPolicy

Immutable ID/version containing metric formulas, units, directions, precision, return observation frequency, annualization rule, and null semantics.

## ScoringPolicy

Immutable ID/version containing required metrics, fixed bounds, weights totaling `1`, normalization direction, eligibility rules, and total deterministic tie-break sequence.

## EvaluationResult

| Field | Type | Rules |
|---|---|---|
| id | UUID | Immutable |
| backtestResultId / jobId / runId | UUID | Exact source/correlation |
| strategyId / strategyVersion / datasetId | identity | Required provenance |
| pair / timeframe / startTime / endTime | values | Comparison context |
| executionPolicyId/version/fingerprint | identity | Comparison context |
| executionConfig | immutable summary | Capital, fee, slippage, sizing, side, timing, close, seed, and precision rules required by TV5 provenance |
| evaluationPolicyId/version | identity | Formula provenance |
| totalReturn | decimal | Finite percent |
| winRate | decimal | Finite percent; `0` for no Trades |
| maxDrawdown | decimal | Finite positive percent |
| numberOfTrades | integer | Non-negative |
| profitFactor / sharpeRatio | nullable decimal | Never NaN/infinity |
| score | decimal | Finite `[0,100]`; `0` when ineligible |
| eligible | boolean | Policy result |
| exclusionReasons | stable code list | Empty when eligible |
| scoringPolicyId/version | identity | Required |
| contentFingerprint | SHA-256 | Unique with exact source/policies |
| evaluatedAt | UTC instant | Audit time; excluded from content fingerprint |

Unique `(backtest_result_id, evaluation_policy_id, evaluation_policy_version, scoring_policy_id, scoring_policy_version)`.

## ComparisonContext

Two results are compatible only when dataset ID/checksum, pair, Timeframe, range, execution policy/config fingerprint, Evaluation Policy version, and Scoring Policy version match. Comparison reports every differing dimension; strict mode rejects any difference and contextual mode returns warnings.

## Persistence Mapping

Tables: `execution_policies`, `backtest_runs`, `backtest_results`, `backtest_signal_snapshots`, `backtest_trades`, `backtest_equity_points`, `evaluation_policies`, `scoring_policies`, and `evaluation_results`. Foreign keys to Feature 001/003 records are retained where available; immutable provenance fields remain directly present to avoid historical reinterpretation.
