# Contract: Backtest Domain Boundary

**Owner**: TV4 | **Consumers**: API and future queued worker | **Version**: `1.0.0`

## Operation

```text
execute(run, complete_dataset, strategy_analysis_result, execution_policy)
  -> BacktestResult
  | CategorizedBacktestError
```

Inputs must identify exact versions and contain no implicit latest lookup. Dataset must satisfy Feature 001 contract `1`: `COMPLETE`, immutable, positive `candle_count`, verified checksum, chronological unique closed Candles. Strategy output must satisfy Feature 003 contract `1.0.0`: aligned immutable Signals and matching provenance.

## Execution v1

- Signal at Candle `t` executes at Candle `t+1` open.
- One `LONG` position; all available cash; no leverage or shorting.
- Buy fill = reference open × `(1 + slippageRate)`; sell fill = reference price × `(1 - slippageRate)`.
- Fee = executed notional × `feeRate` on entry and exit.
- Quantity rounds down after reserving entry fee.
- `HOLD`, `WARMUP`, repeated `BUY` while long, and `SELL` while flat are no-ops with stable reasons.
- Final open position force-closes against final Candle close with normal costs and `END_OF_RANGE`.
- Equity is recorded once per Candle after eligible open execution and marked at close.

## Result Invariants

- Signals and Equity Points preserve input order; Trades preserve close order.
- Cash never becomes negative after precision tolerance.
- Every Trade is closed and references exact entry/exit provenance.
- `finalEquity` equals the last Equity Point.
- Result checksum covers complete input provenance and output business content.
- Duplicate `jobId` with identical fingerprint is idempotent; conflicting content is `BACKTEST_JOB_CONFLICT`.
- Public result mappings identify the content as `HISTORICAL_SIMULATION` and include the approved non-investment-advice disclaimer.

## Errors

`BACKTEST_CONFIGURATION_INVALID`, `BACKTEST_DATASET_INELIGIBLE`, `BACKTEST_DATASET_INTEGRITY_FAILED`, `BACKTEST_STRATEGY_INCOMPATIBLE`, `BACKTEST_SIGNAL_MISALIGNED`, `BACKTEST_INSUFFICIENT_CAPITAL`, `BACKTEST_JOB_CONFLICT`, and `BACKTEST_EXECUTION_FAILED`. Errors contain safe message/issues and no partial completed result.
