# Research: Deterministic Backtest and Evaluation

## R1 — Execution timing

**Decision**: A Signal aligned to Candle `t` executes only at the opening price of Candle `t+1`. A final-Candle Signal cannot open a Trade.

**Rationale**: The Strategy sees the complete closed Candle at `t`; using its closing price as an executable fill would assume impossible same-instant knowledge. Next-open execution is simple, deterministic, and look-ahead safe.

**Alternatives considered**: Same-close fill (rejected for look-ahead risk); configurable same-close/next-open (deferred because it expands semantics before a demonstrated need).

## R2 — Position, sizing, fees, and slippage

**Decision**: MVP is spot long-only with one position. `BUY` while flat invests all available cash; quantity is rounded down to 18 decimal places after reserving entry fee. `SELL` while long closes all quantity. Fee rate applies to entry/exit notional. Slippage moves buys upward and sells downward. Rates are decimal fractions, non-negative, and versioned in configuration.

**Rationale**: This matches the assignment's buy/sell examples, prevents implicit leverage/borrowing, and produces a complete accounting identity with few hidden choices.

**Alternatives considered**: Fixed quantity/fractional sizing (future policy versions); short selling or multiple positions (out of MVP); ignoring costs (rejected because fees/slippage are required inputs).

## R3 — Redundant Signals and end-of-range

**Decision**: `BUY` while long, `SELL` while flat, `HOLD`, and `WARMUP` are deterministic no-ops with stable reason codes. An open position at range end is force-closed at the final Candle close with normal adverse slippage/fee and `END_OF_RANGE` close reason.

**Rationale**: No-op reasons make every Signal explainable. Forced closure yields final realized equity and comparable metrics while retaining explicit artificial-close provenance.

**Alternatives considered**: Pyramiding/short reversal (out of scope); leave unrealized position open (rejected because Trade metrics and final reconciliation become ambiguous).

## R4 — Decimal and checksum semantics

**Decision**: Domain money, prices, quantities, rates, returns, metrics, and scores use `Decimal`. Persistence uses `NUMERIC(38,18)`. Quantity rounds down to 18 places; published monetary/metric results round half-even to 18 places. Canonical JSON sorts keys, uses UTC millisecond instants and plain decimal strings, excludes database/audit timestamps, and is SHA-256 hashed.

**Rationale**: This matches Feature 001 fixed-point values and avoids platform-dependent binary floating behavior. Excluding audit fields keeps identical business content checksums stable.

**Alternatives considered**: Binary float (rejected); arbitrary per-field precision without a policy (rejected); checksum only IDs (insufficient to prove actual result equivalence).

## R5 — Equity Curve and metric formulas

**Decision**:

- Equity is marked after each Candle's eligible opening execution and valued at that Candle close: `cash + quantity × close`.
- Total Return (%) = `(finalEquity - initialCapital) / initialCapital × 100`.
- Win Rate (%) = `winning closed Trades / closed Trades × 100`; `0` for zero Trades to preserve the TV5 required-decimal contract.
- Maximum Drawdown (%) is the greatest positive peak-to-trough decline across the Equity Curve; `0` when no decline exists.
- Number of Trades is the count of closed Trades.
- Profit Factor = gross positive P/L divided by absolute gross negative P/L; null when there is no gross loss.
- Sharpe Ratio uses per-Candle Equity Curve returns, zero risk-free rate, sample standard deviation, and annualization `sqrt(365 days / Timeframe duration)`; null with fewer than two returns or zero variance.

**Rationale**: Every value derives only from immutable Backtest Result data, has explicit units/direction, and covers constitution-required zero-division cases.

**Alternatives considered**: Daily resampling (adds calendar/data-gap decisions); unannualized Sharpe (less comparable across Timeframes); infinity sentinels (forbidden).

## R6 — Initial scoring policy

**Decision**: Policy `balanced-v1` produces a score in `[0,100]` using clamped fixed bounds: Total Return `[-100%,100%]` at 35%, Win Rate `[0%,100%]` at 25%, inverse Maximum Drawdown `[0%,100%]` at 25%, and Sharpe Ratio `[-3,3]` at 15%. Bounds are policy data, not code constants. Required null metrics make the result ineligible; it retains score `0`, `eligible=false`, and explicit exclusion reasons for Feature 005 compatibility. Tie-break order is higher Total Return, lower Maximum Drawdown, higher Win Rate, then immutable Evaluation Result ID.

**Rationale**: Fixed bounds make a score reproducible without depending on the current candidate population. Versioned policy data allows future changes without rewriting history.

**Alternatives considered**: Population min-max/z-score (score changes when candidates change); raw Total Return only (ignores risk); no score in TV4 (conflicts with TV5's required upstream score).

**Governance note**: `docs/ADR/ADR-006-versioned-scoring-policy.md` records this cross-feature decision as Proposed. `balanced-v1` is not the approved project default until team review accepts ADR-006 or an approved replacement.

## R7 — Direct execution boundary

**Decision**: Feature 004 supports create then explicit start through application/API calls, executing in the API process for the bounded feature demo. It preserves `runId` and `jobId` identities but does not select a broker or implement lease/retry/worker behavior.

**Rationale**: This yields an independently demonstrable slice without preempting Feature 007's worker ADR and contracts.

**Alternatives considered**: Queue now (violates assigned scope and ADR gate); one opaque create-and-run call (makes lifecycle and future worker migration less explicit).
