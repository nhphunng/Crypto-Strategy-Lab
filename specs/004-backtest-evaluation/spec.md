# Feature Specification: Deterministic Backtest and Evaluation

**Feature Branch**: `feat/004-backtest-evaluation-spec-plan`

**Created**: 2026-08-13

**Status**: Draft

**Input**: Allow an analyst to run one immutable, versioned Strategy Definition against a fixed historical dataset with explicit capital, fees, slippage, sizing, and seed; produce reproducible simulated Trades, an Equity Curve, deterministic metrics, a versioned score, and comparison-ready Evaluation Results without implementing search or distributed workers.

## Source Traceability

- **Primary assignment**: `docs/REQUIREMENT.md` §§19-20 and MVP §§37 Backtest/Evaluation.
- **Approved SRS feature groups**: `docs/SRS.md` §§7.7-7.8.
- **Canonical SRS stories included**: `BT-US-01`, `BT-US-02`, `EV-US-01`, `EV-US-02`, and `EV-US-03`.
- **Applicable SRS requirements**: `BT-FR-01` through `BT-FR-03`, `BT-FR-06` for result idempotency, and `EV-FR-01` through `EV-FR-03`.
- **Applicable business flows**: `docs/SRS.md` §6.5 steps 4-6 and §6.6 step 1.
- **Cross-cutting rules**: SRS §§4.2, 4.4, 4.6; Constitution `BR-02`, `BR-03`, `BR-05`, `BR-06`, `BR-10`, `VL-04`, `VL-05`, and `LA-04`.
- **Deferred SRS stories**: `BT-US-03` and `BT-US-04`, with `BT-FR-04`, `BT-FR-05`, and worker lifecycle portions of `BT-FR-07`, belong to the later queued-worker feature; this feature preserves compatible run/job provenance but does not implement distributed execution.

## Clarifications

### Session 2026-08-13

- Q: When should a Signal produced for the current Candle be executed? → A: Execute at the next Candle's opening price.
- Q: Which position model should the MVP support? → A: Spot long-only with at most one open position; `BUY` opens and `SELL` closes.
- Q: How should position size, fees, and slippage be applied? → A: Use all available cash for each entry, apply non-negative percentage fees to entry and exit notional, and apply percentage slippage adversely to each fill.
- Q: How should redundant Signals and an open position at the range end be handled? → A: Treat `BUY` while long and `SELL` while flat as documented no-ops; force-close an open position at the final Candle close with an explicit `END_OF_RANGE` reason.
- Q: What should undefined metric cases return? → A: A no-trade result has Total Return `0`, Win Rate `0`, Maximum Drawdown `0`, Number of Trades `0`, and nullable Profit Factor and Sharpe Ratio; no-loss Profit Factor and zero-variance Sharpe Ratio are null, never infinity or NaN.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run a Reproducible Historical Backtest (Priority: P1) (`BT-US-01`)

As an `ANALYST`, I want to run one exact Strategy Definition over one fixed historical dataset with an explicit execution configuration so that I can assess its past simulated behavior and reproduce the result later.

**Why this priority**: A deterministic historical simulation is the smallest useful slice and the required foundation for every trade, metric, score, and leaderboard result.

**Independent Test**: Use a fixed complete dataset, exact Strategy Definition, initial capital, fees, slippage, sizing rule, and seed; run the same request repeatedly and verify an equivalent completed result and checksum, then introduce future or incomplete data and verify rejection before simulation.

**Acceptance Scenarios**:

1. **Given** an exact available Strategy Definition, a complete immutable historical dataset, and a valid explicit execution configuration, **When** the analyst starts a Backtest Run, **Then** the system produces a completed immutable Backtest Result tied to those exact inputs.
2. **Given** the same complete canonical inputs and seed, **When** the Backtest Run is repeated, **Then** the result content and checksum are equivalent.
3. **Given** a dataset containing an open, missing, duplicated, misordered, misaligned, or future Candle, **When** the analyst requests a Backtest Run, **Then** the request is rejected without silently sorting, filling, coercing, or simulating partial data.
4. **Given** invalid capital, fees, slippage, sizing, time range, strategy version, or contract version, **When** the analyst requests a Backtest Run, **Then** all detected validation issues are returned before any result is created.

---

### User Story 2 - Inspect Simulated Trades and Equity (Priority: P2) (`BT-US-02`)

As an `ANALYST`, I want to inspect each simulated Trade and the Equity Curve so that I can explain how the strategy's Signals changed capital over time.

**Why this priority**: Aggregate performance is not trustworthy unless it reconciles to visible entry, exit, quantity, costs, and balance changes.

**Independent Test**: Use a prepared Strategy Analysis Result with known Signals and verify the exact ordered Trades, entry/exit provenance, costs, realized result, Equity Curve, and final equity without calculating evaluation metrics.

**Acceptance Scenarios**:

1. **Given** an evaluable ordered Signal sequence, **When** the simulation completes, **Then** every Trade records its entry and exit, side, quantity, prices, fees, slippage impact, profit or loss, and generating Signal references.
2. **Given** a completed Backtest Result, **When** its Trades and Equity Curve are inspected, **Then** their ordered balance changes reconcile exactly to final equity.
3. **Given** a valid run whose Signals create no executable Trade, **When** the simulation completes, **Then** it produces an explicit successful no-trade result rather than an error or fabricated Trade.
4. **Given** warm-up Signals, **When** the simulation processes them, **Then** they do not create Trades.

---

### User Story 3 - Calculate Deterministic Performance and Risk Metrics (Priority: P3) (`EV-US-01`)

As an `ANALYST`, I want a separate evaluation of a completed Backtest Result so that I can judge both performance and risk without relying on profit alone.

**Why this priority**: Required metrics make results comparable while keeping evaluation independent from Strategy behavior.

**Independent Test**: Evaluate fixed Backtest Result fixtures for profitable, losing, no-trade, no-loss, and zero-variance cases and verify documented values or explicit undefined states without reading a concrete Strategy implementation.

**Acceptance Scenarios**:

1. **Given** a completed Backtest Result, **When** it is evaluated, **Then** Total Return, Win Rate, Maximum Drawdown, and Number of Trades are calculated using documented deterministic semantics.
2. **Given** a result with sufficient applicable observations, **When** extended metrics are requested, **Then** Profit Factor and Sharpe Ratio are calculated using documented units, periods, and edge-case semantics.
3. **Given** a no-trade, no-loss, zero-variance, or otherwise undefined metric case, **When** evaluation completes, **Then** the Evaluation Result uses an explicit documented value or undefined state and never emits NaN or infinity.
4. **Given** the same immutable Backtest Result and evaluation policy version, **When** evaluation is repeated, **Then** the Evaluation Result content is equivalent and historical results are not overwritten.

---

### User Story 4 - Apply a Versioned Scoring Policy (Priority: P4) (`EV-US-02`)

As an `ANALYST`, I want to apply a published, versioned scoring policy to an Evaluation Result so that multiple metrics can produce a consistent comparison score without changing historical meaning.

**Why this priority**: TV5 requires a score and policy provenance for reproducible Top-K ranking, but raw metrics remain useful before scoring is added.

**Independent Test**: Apply one fixed policy to deterministic metric fixtures, including boundary and ineligible values, and verify stable scores, eligibility outcomes, and policy provenance without invoking leaderboard ranking.

**Acceptance Scenarios**:

1. **Given** a valid Evaluation Result and compatible scoring policy, **When** scoring is applied, **Then** the resulting score retains the exact policy identity, version, weights, normalization meaning, eligibility rules, and tie-break information.
2. **Given** the same Evaluation Result and policy version, **When** scoring is repeated, **Then** the score is equivalent.
3. **Given** a new scoring policy version, **When** an existing Backtest Result is evaluated under it, **Then** a new immutable Evaluation Result is created without rewriting the prior evaluation.
4. **Given** missing, undefined, or incompatible metric inputs, **When** scoring is attempted, **Then** the policy's documented eligibility behavior is applied and the result is not silently coerced into a superior score.

---

### User Story 5 - Compare Compatible Evaluation Results (Priority: P5) (`EV-US-03`)

As an `ANALYST`, I want to compare Evaluation Results with their complete context so that differences in metrics are meaningful rather than caused by hidden dataset or execution differences.

**Why this priority**: Comparison becomes useful after evaluations exist and prevents misleading ranking conclusions.

**Independent Test**: Compare prepared results with identical context, then vary dataset, Market Pair, Timeframe, date range, execution configuration, or policy and verify compatible comparison or an explicit contextual warning.

**Acceptance Scenarios**:

1. **Given** Evaluation Results with compatible comparison context, **When** the analyst compares them, **Then** their metrics and scores can be ordered without changing stored values.
2. **Given** Evaluation Results that differ in dataset, Market Pair, Timeframe, range, execution configuration, or policy, **When** comparison is requested, **Then** every difference is visible and the comparison is warned or rejected according to the documented compatibility rules.
3. **Given** historical Strategy, dataset, execution, or policy versions, **When** the analyst inspects a comparison, **Then** exact provenance remains available and is never reinterpreted as the current version.

### Edge Cases

- A complete dataset is empty or contains insufficient history for the Strategy; the run completes with an explicit empty/insufficient outcome and no fabricated Trades.
- Every Signal is `HOLD` or `WARMUP`; the result is valid with zero Trades and unchanged capital after applicable non-trade costs, which default to none.
- Consecutive or redundant `BUY`/`SELL` Signals arrive while the portfolio is already in the corresponding state; the configured execution policy handles them deterministically without duplicate position transitions.
- A position remains open at the requested range end; it is force-closed at the final closed Candle's close price and records `END_OF_RANGE` provenance.
- Fee or slippage consumes the available capital or makes an order non-positive; the order is rejected or skipped with an explicit reason and no negative balance.
- A Candle has a price or volume outside accepted precision/range; the run is rejected rather than silently rounded into validity.
- A Strategy Analysis Result reports `EMPTY`, `INSUFFICIENT`, an incompatible contract version, or Signals not aligned with the supplied dataset; simulation does not proceed with repaired or partial Signals.
- Total Return, Win Rate, Maximum Drawdown, Profit Factor, or Sharpe Ratio would otherwise divide by zero or become non-finite; documented undefined/null semantics are used.
- The same logical run or evaluation is submitted more than once; at most one durable result exists for the idempotency identity.
- News or sentiment data is unavailable for a purely technical Strategy; the Backtest Run remains usable. A Strategy that explicitly requires unavailable context fails or defers visibly rather than using fabricated data.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow an analyst to run one exact immutable Strategy Definition against one exact immutable historical dataset and declared UTC range and Timeframe.
- **FR-002**: A Backtest Run MUST retain the exact Strategy Definition and contract versions, canonical parameters, dataset identity/version/checksum, Market Pair, Timeframe, range, Strategy Context fingerprint, initial capital, fees, slippage, position-sizing policy, execution-policy version, and random seed used.
- **FR-003**: The system MUST reject invalid configurations before simulation, including non-positive capital, negative fees or slippage, invalid ranges, unsupported Timeframes, unavailable Strategy versions, incompatible contract versions, incomplete datasets, invalid Candles, and Signal/dataset misalignment.
- **FR-004**: Simulation MUST consume the generic Strategy contract and ordered `BUY`, `SELL`, and `HOLD` Signals without branching on concrete Strategy names.
- **FR-005**: Simulation MUST use only closed normalized Candles and contextual data available no later than each simulated decision time; no Signal, execution, Trade, or metric may use future information.
- **FR-006**: A Signal produced for a Candle MUST be eligible for execution only at the next Candle's opening price. The MVP MUST simulate spot long-only trading with at most one open position. `BUY` while flat opens a position using all available cash; `SELL` while long closes it; `BUY` while long and `SELL` while flat are deterministic no-ops with recorded reasons. Entry and exit fills MUST apply configured non-negative percentage slippage adversely to the reference price and a configured non-negative percentage fee to executed notional. A Signal on the final Candle cannot create a new execution. An open position at range end MUST be force-closed using the final closed Candle's close price as the reference price, with normal exit costs and close reason `END_OF_RANGE`.
- **FR-007**: A completed Backtest Result MUST contain immutable input provenance, ordered simulated Trades, an Equity Curve, final equity, completion status, execution version, and a deterministic result checksum.
- **FR-008**: Every Trade MUST retain stable identity, entry/exit Signal references when applicable, Strategy Definition/version, entry/exit times and prices, side, quantity, costs, realized profit or loss, return percentage, and close reason.
- **FR-009**: Trade ordering, cash/position changes, costs, realized results, the Equity Curve, and final equity MUST reconcile under one documented accounting identity.
- **FR-010**: A valid no-trade run MUST complete successfully with zero Trades, an explicit no-trade state, a valid Equity Curve, and final equity that reconciles to the execution configuration.
- **FR-011**: Evaluation MUST read an immutable Backtest Result rather than a concrete Strategy implementation and MUST calculate at least Total Return, Win Rate, Maximum Drawdown, and Number of Trades.
- **FR-012**: Evaluation MUST define deterministic formulas, units, precision, observation frequency, and edge-case semantics for every metric; Profit Factor and Sharpe Ratio MUST be included for this feature's extended evaluation scope.
- **FR-013**: A no-trade Evaluation Result MUST use Total Return `0`, Win Rate `0`, Maximum Drawdown `0`, Number of Trades `0`, and null Profit Factor and Sharpe Ratio. Profit Factor MUST be null when there is no gross loss, and Sharpe Ratio MUST be null when return variance is zero or observations are insufficient. Undefined metrics MUST never be persisted or exchanged as NaN or infinity.
- **FR-014**: A Scoring Policy MUST be immutable and versioned and MUST publish metric direction, weights, normalization, eligibility, undefined/no-trade behavior, and a deterministic tie-break sequence.
- **FR-015**: Applying a different Evaluation or Scoring Policy version MUST create a new immutable Evaluation Result and MUST NOT overwrite historical results or reinterpret their provenance.
- **FR-016**: Evaluation Result persistence MUST be idempotent for its declared Backtest Result and policy identities so duplicate processing creates no duplicate result.
- **FR-017**: Each Evaluation Result MUST expose immutable identifiers and provenance required by leaderboard consumers, including its Backtest Result, run/job correlation, Strategy version, dataset context, required metrics, optional metric availability, score, Scoring Policy version, and evaluation time.
- **FR-018**: Comparison MUST define compatibility using dataset identity, Market Pair, Timeframe, date range, execution configuration, metric semantics, and policy version; incompatible differences MUST be visible and warned or rejected rather than hidden.
- **FR-019**: Historical Backtest Results, Trades, Equity Curves, Evaluation Results, and policy provenance MUST be immutable and retrievable for audit and reproduction.
- **FR-020**: Run failures MUST expose a stable categorized reason without returning partial success as a completed Backtest Result or leaking secrets, credentials, private payloads, or internal exception traces.
- **FR-021**: The feature MUST support automated acceptance coverage for determinism, look-ahead prevention, validation, Signal/execution behavior, Trade and Equity Curve reconciliation, no-trade results, metric formulas and edge cases, scoring-policy versioning, idempotency, provenance, and compatible/incompatible comparison.
- **FR-022**: All user-facing results MUST be labelled as historical simulation for analysis only, MUST NOT imply guaranteed profit, and MUST NOT place, modify, or cancel a live exchange order.

### Key Entities

- **Backtest Run**: One requested historical simulation with exact Strategy, dataset, range, execution, correlation, and lifecycle provenance.
- **Execution Policy**: Immutable versioned rules that translate ordered Signals and Candle observations into fills, positions, costs, and end-of-range behavior.
- **Backtest Result**: Immutable simulation output containing provenance, Trades, Equity Curve, final equity, status, and checksum.
- **Trade**: One simulated position lifecycle linked to entry/exit Signals and exact execution values.
- **Equity Point / Equity Curve**: Ordered valuation history that reconciles the simulation to final equity.
- **Evaluation Policy**: Versioned definitions of metric formulas, precision, units, and undefined-value semantics.
- **Evaluation Result**: Immutable metrics and score for one Backtest Result under exact Evaluation and Scoring Policy versions.
- **Scoring Policy**: Versioned rules for metric direction, normalization, weights, eligibility, and deterministic tie-breaking.
- **Comparison Context**: The dataset, Market Pair, Timeframe, range, execution, and policy dimensions used to determine whether Evaluation Results are comparable.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Repeating the same canonical complete input and seed 100 times produces one equivalent Backtest Result content checksum and one equivalent Evaluation Result per policy version.
- **SC-002**: In look-ahead acceptance fixtures, 100% of future, open, misaligned, duplicated, unsorted, gap-marked, or incomplete inputs are rejected before they can influence a Trade or metric.
- **SC-003**: For every completed acceptance fixture, cash, positions, costs, Trades, Equity Curve, and final equity reconcile exactly within the documented decimal precision.
- **SC-004**: Required metric fixtures for profitable, losing, no-trade, no-loss, and zero-variance results match the documented formulas in 100% of cases and produce no NaN or infinite value.
- **SC-005**: Replaying the same run or evaluation request at least twice creates exactly one durable result for its idempotency identity.
- **SC-006**: For 100% of completed fixture results, an analyst can trace the result to the exact Strategy Definition/version, parameter fingerprint, dataset version/checksum, Signals, execution policy/configuration, Evaluation Policy, Scoring Policy, and result checksum.
- **SC-007**: Adding and registering a contract-compatible test Strategy requires no Backtester, Evaluator, Scoring, or comparison rule keyed to that Strategy's concrete name.
- **SC-008**: In prepared comparison fixtures, 100% of differing compatibility dimensions are either displayed with an explicit warning or rejected; none are silently treated as equivalent.
- **SC-009**: All no-trade, insufficient-history, invalid-input, failed-run, undefined-metric, and incompatible-comparison acceptance scenarios end in an explicit stable state rather than partial, fabricated, or silently coerced data.
- **SC-010**: Every user-facing backtest/evaluation result states that it is a historical simulation for analysis only and contains no claim of guaranteed future profit.

## Assumptions

- The trusted MVP demo does not introduce accounts, ownership, or new authorization roles; `ANALYST` describes a product actor rather than a security role.
- Feature 001 owns the durable Candle Dataset and historical-range contract on `origin/feat/001-market-data-spec-plan`: TV4 consumes only `COMPLETE` immutable datasets with contract/schema version `1`, one provider/Market Pair/Timeframe, UTC millisecond timestamps, `[startTime,endTime)` bounds, strictly ordered unique closed Candles, exact decimal values, stable membership, and a verified content checksum. TV4 MUST re-review this dependency after Feature 001 merges to `main`.
- Feature 003 contract version `1.0.0` is the initial Strategy boundary. TV4 supplies an exact Strategy Definition and immutable Strategy Context and consumes its deterministic ordered Signals.
- The initial execution model is spot long-only with one position, all-available-cash sizing, adverse percentage slippage, percentage fees on both fills, deterministic redundant-Signal no-ops, and forced end-of-range closure. These semantics are versioned in the Execution Policy.
- Monetary, price, quantity, return, and metric calculations use explicit decimal/rounding rules selected during planning; binary floating-point artifacts must not alter canonical results.
- Scoring belongs to evaluation in this feature because TV5 requires an immutable score and Scoring Policy version but does not calculate financial metrics or scoring formulas.
- Search generation, queue leasing, multi-worker execution, retries, dead-letter handling, realtime progress, Leaderboard projection, chart visualization, Composite Strategy resolution, and live trading are outside this feature.

## Out of Scope

- Candidate generation, Random Search, continuous loops, or choosing which Strategy Definition should run.
- Durable queue/broker selection, worker leasing/acknowledgement, horizontal worker scaling, retry budgets, and dead-letter processing.
- Leaderboard membership, Top-K projection, ranking updates, REST/WebSocket delivery, and chart rendering.
- Creating Strategy Signals, indicators, Strategy registration, or branches for MA, RSI, or any other concrete Strategy.
- Collecting, repairing, sorting, filling, deduplicating, or mutating historical Candle data.
- Composite Strategy member resolution; TV4 consumes its resulting common Strategy contract when that feature exists.
- Live order placement, exchange account management, wallet operations, investment advice, or guaranteed-profit claims.
