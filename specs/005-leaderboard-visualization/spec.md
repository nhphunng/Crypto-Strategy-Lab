# Feature Specification: Leaderboard and Trade Visualization

**Feature Branch**: `005-leaderboard-visualization`

**Created**: 2026-08-13

**Status**: Draft

**Input**: TV5 in `spec-plan.md`: specify and plan Top-K strategy ranking and the visualization of Buy/Sell signals and Entry/Exit trades. The assignment PDF is authoritative; `docs/REQUIREMENT.md` is its searchable export and `docs/SRS.md` supplies approved identifiers and acceptance baselines.

## Source Traceability

- **Primary assignment**: `Crypto Strategy Lab – Đồ án cuối kỳ.pdf`, especially Module 8 (Leaderboard), Top-K Strategies, Visualization Strategy, Trade Detail, the `LEADERBOARD_UPDATED` flow, MVP requirements, and demo steps 5-7.
- **Exported assignment**: `docs/REQUIREMENT.md` §§21-22, 25-26, 33-37, 40, 45-46.
- **Approved SRS feature**: `docs/SRS.md` §7.9, canonical stories `LV-US-01`, `LV-US-02`, and `LV-US-03`.
- **Approved SRS requirements**: §§3.8-3.9 (`EV-FR-03` through `EV-FR-06` and Visualization Dashboard), §4.1, §4.6, §5.1, §5.3, §5.5, and business flow §6.6.
- **Business rules**: Constitution `BR-02`, `BR-03`, `BR-05`, `BR-06`, `BR-07`, and `BR-10`; SRS `BR-03`, `BR-05`, `BR-06`, `BR-07`, `BR-08`, and `BR-10`. IDs are source-qualified because the two documents number some equivalent rules differently.

## Clarifications

### Session 2026-08-13

- No critical ambiguity required a user question. The authoritative sources define Top-K ranking, deterministic policy/ties, incremental updates, provenance, signal/trade overlays, and trade drill-down. Planning may choose storage and transport mechanisms without changing user-visible scope.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Top-K Strategies (Priority: P1) (`LV-US-01`)

As an `ANALYST`, I want to view the current Top-K strategies with their metrics, score, version, and evaluation context so that I can identify candidates worth inspecting without comparing every completed backtest manually.

**Why this priority**: Top-K is the assignment's mandatory leaderboard outcome and provides a useful, independently demonstrable result from existing Evaluation Results.

**Independent Test**: Seed more compatible Evaluation Results than the configured K, including a deterministic tie. Open the leaderboard and verify that exactly the qualifying Top-K are ordered consistently, expose their comparison context and immutable strategy version, and remain usable through sort, filter, and pagination controls.

**Acceptance Scenarios**:

1. **Given** more compatible evaluated candidates than the selected K, **When** the analyst opens the leaderboard, **Then** the K highest qualifying entries are shown according to the selected metric or versioned scoring policy and deterministic tie-breaker.
2. **Given** a displayed Leaderboard Entry, **When** the analyst inspects it, **Then** the strategy composition and immutable version, Market Pair, Timeframe, dataset/date range, Total Return, Win Rate, Maximum Drawdown, Number of Trades, score, and scoring policy version are available.
3. **Given** many Leaderboard Entries, **When** the analyst selects a ranking metric, sorts the resulting Top-K, filters by supported metric ranges or context, or changes page, **Then** membership and presentation criteria are applied consistently without changing stored metric values or historical rank meaning.
4. **Given** a no-trade or otherwise non-rankable Evaluation Result, **When** ranking is calculated, **Then** the documented metric semantics are applied and the result cannot silently corrupt ordering.

---

### User Story 2 - Receive Incremental Leaderboard Updates (Priority: P2) (`LV-US-02`)

As an `ANALYST`, I want the leaderboard to update when each candidate is evaluated so that I see new leading candidates without refreshing the page or waiting for the whole search run.

**Why this priority**: It completes the assignment's live ranking flow while remaining demonstrable with a single newly completed Evaluation Result.

**Independent Test**: Keep a leaderboard view open, publish one qualifying completed evaluation twice, and verify that the row is inserted or updated once, ranks are reconciled, and update/run state changes without a page refresh.

**Acceptance Scenarios**:

1. **Given** an open leaderboard and a newly completed candidate, **When** its Evaluation Result qualifies for Top-K, **Then** the affected entry and ranks update without a full-page refresh or waiting for other candidates.
2. **Given** the same evaluation notification is delivered more than once, **When** updates are processed, **Then** there is at most one Leaderboard Entry for the evaluation and policy version.
3. **Given** an update arrives after another newer update, **When** the client reconciles state, **Then** stale data does not replace the newer leaderboard projection.
4. **Given** live update delivery is interrupted, **When** the analyst continues viewing the page, **Then** the UI identifies the data as stale/reconnecting and can recover the current snapshot without losing access to existing entries.

---

### User Story 3 - Visualize Signals and Simulated Trades (Priority: P3) (`LV-US-03`)

As an `ANALYST`, I want to select a ranked result and view its strategy overlays, signals, and simulated trades on Candles so that I can explain how its aggregate metrics arose.

**Why this priority**: Visualization makes ranking explainable and fulfills the MVP requirement for Buy/Sell and Entry/Exit chart markers, but it depends on a result being available to inspect.

**Independent Test**: Open a prepared Leaderboard Entry with Candles, signals, overlays, and trades. Verify timestamp/price alignment, non-color-only marker distinctions, trade-table reconciliation, selection highlighting, and complete provenance without running a new backtest.

**Acceptance Scenarios**:

1. **Given** a Leaderboard Entry with strategy output and trades, **When** the analyst opens its detail, **Then** the matching Market Pair, Timeframe, range, Candles, supported strategy overlays, Buy/Sell signals, and Entry/Exit markers are displayed.
2. **Given** multiple marker types at nearby times or prices, **When** they are displayed, **Then** Buy, Sell, Entry, and Exit remain distinguishable by text and/or shape rather than color alone.
3. **Given** a trade table row, **When** the analyst selects it, **Then** the corresponding Entry and Exit are highlighted on the chart and entry/exit time and price, side, quantity, result, generating signal, strategy version, Backtest Run, dataset, and execution context are inspectable.
4. **Given** an entry with zero trades, **When** the analyst opens visualization, **Then** Candles and available signals/overlays remain inspectable and a clear no-trade state replaces an empty or misleading trade table.
5. **Given** any leaderboard or ranked-result analysis view, **When** it is displayed, **Then** it is clearly labelled as simulated historical analysis, includes a visible non-investment-advice disclaimer, and makes no claim of guaranteed profit.

### Edge Cases

- Fewer than K compatible results exist: show every qualifying result and state the actual count rather than padding the list.
- K is outside `1..200`, a metric range is malformed, or filters are unsupported: reject the request with the standardized semantic-validation response. A page beyond the result set returns an empty page with the requested page metadata and unchanged authoritative ranks.
- Scores or selected metrics are tied: apply the scoring policy's documented deterministic tie-breaker so repeated ranking yields the same order.
- An Evaluation Result has missing, non-finite, or no-trade metric values: apply the upstream metric semantics and expose exclusion/availability clearly; never treat missing data as silently superior.
- An evaluated candidate no longer belongs in Top-K after another result arrives: remove or reposition it and reconcile contiguous ranks atomically.
- Duplicate or out-of-order update delivery occurs: deduplicate by immutable evaluation and policy identity and reject stale projection versions.
- A historical Strategy Definition or scoring policy has a newer version: retain and display the exact versions used by the selected historical result.
- Candle, signal, or trade timestamps do not align or referenced data is unavailable: show a partial-data/error state, preserve provenance, and do not place a marker on a guessed Candle.
- Several signals or trade endpoints overlap: aggregate or offset their visual presentation while retaining access to every underlying detail.
- The selected range is large: retrieve and display a bounded range and allow further navigation rather than loading unbounded history.
- Live update connectivity fails: existing snapshot browsing and detail visualization remain available with an explicit stale/reconnecting indicator.
- News/Sentiment is unavailable: technical-strategy Leaderboard Entries and visualizations remain available; no fabricated sentiment overlay is shown.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST maintain and return a configurable Top-K set of Leaderboard Entries derived only from compatible persisted Evaluation Results. Projection identity MUST include the comparison scope, selected ranking metric, K, and versioned scoring policy so concurrent requests for different ranking definitions cannot overwrite or subscribe to one another. (`EV-FR-03`, `EV-FR-04`)
- **FR-002**: Ranking MUST use the scoring policy's documented direction, normalization, and deterministic tie-breaker so the same eligible inputs produce the same ordered result. (Constitution `BR-06`; SRS `BR-07`)
- **FR-003**: Each Leaderboard Entry MUST identify its rank, Evaluation Result, immutable Strategy Definition/version and composition, dataset/date range, Market Pair, Timeframe, required metrics, score, scoring policy version, and last update/projection version. (`LV-US-01`)
- **FR-004**: The leaderboard MUST expose at least Total Return, Win Rate, Maximum Drawdown, and Number of Trades, and MUST label metric direction and units clearly; supported extended metrics such as Sharpe Ratio MAY also be shown. (`EV-FR-01`, `EV-FR-02`, UXR §5.1)
- **FR-005**: Analysts MUST be able to select the ranking metric; sort the resulting Top-K by rank, supported metric, or score; filter by supported metric ranges, Market Pair, and Timeframe; and page through bounded result sets. Presentation sorting MUST NOT change Top-K membership, persisted values, or historical policy meaning. (`EV-FR-05`, UXR §5.5)
- **FR-006**: Each Scoring Policy MUST define explicit eligibility and ordering behavior for fewer-than-K, ties, no-trade, missing/non-finite metrics, and incompatible evaluation contexts. Inputs without valid policy semantics MUST be excluded with a visible reason rather than silently coerced. (`LV-US-01`, §6.6 negative flow)
- **FR-007**: A completed candidate MUST be eligible for ranking immediately after evaluation without waiting for the enclosing search/backtest run to finish. (`EV-FR-06`)
- **FR-008**: A qualifying leaderboard change MUST be published to connected clients and applied without a full-page refresh. The view MUST expose latest update time/projection version and related run state. (`LV-US-02`)
- **FR-009**: Processing the same Evaluation Result/update more than once MUST NOT create duplicate Leaderboard Entries, projection changes, update records, or visible update effects. This feature MUST consume, not duplicate or rewrite, the upstream Evaluation Result and score. (Constitution `BR-07`; SRS Reliability §4.6)
- **FR-010**: Out-of-order, missed, or interrupted live updates MUST NOT regress the displayed projection; clients MUST identify stale/reconnecting state and recover from a current snapshot. (`LV-US-02`, UXR §§5.1, 5.3)
- **FR-011**: Analysts MUST be able to open a Leaderboard Entry and view a detail context that exactly matches its Market Pair, Timeframe, dataset/date range, Strategy Definition/version, Backtest Run, Evaluation Result, and scoring policy. (`LV-US-03`)
- **FR-012**: The detail view MUST show Candles together with supported strategy-provided overlays and timestamped Buy/Sell signals; timestamped Hold signals MUST be available through an explicit visibility control and MAY be hidden by default to reduce chart clutter. The view MUST NOT infer strategy-specific overlays from concrete strategy names. (`LV-US-03`, Visualization Dashboard)
- **FR-013**: The detail view MUST show simulated Entry and Exit markers aligned to the recorded trade timestamps and prices. Buy, Sell, Entry, and Exit MUST remain distinguishable without relying on color alone. (`LV-US-03`, UXR §5.1)
- **FR-014**: The detail view MUST provide a sortable, pageable trade list with entry/exit times and prices, side, quantity, and result; selecting a trade MUST highlight both endpoints on the chart. (PDF §26, `LV-US-03`)
- **FR-015**: Signal and trade detail MUST preserve traceability to the generating signal, Strategy Definition/version, Backtest Run, dataset, execution configuration, Evaluation Result, and scoring policy; historical provenance MUST NOT be overwritten. (Constitution `BR-02`/`BR-03`; SRS `BR-03`, `LV-US-03`)
- **FR-016**: The feature MUST represent empty, loading, partial-data, no-trade, failed-result, stale-update, and unavailable-overlay states explicitly and retain usable data where possible. (UXR §§5.3, 5.5)
- **FR-017**: Leaderboard ranking and visualization MUST remain generic across registered strategies; adding MACD, another compliant Strategy, or Sentiment Strategy MUST NOT require strategy-name branches in ranking or visualization. (Architecture extensibility scenario)
- **FR-018**: The feature MUST present simulated historical results for analysis only, display a visible non-investment-advice disclaimer on leaderboard and ranked-result views, make no guaranteed-profit claim, and MUST NOT place, modify, or imply execution of live exchange orders. (`BR-10`, Constitution Security Requirements)
- **FR-019**: The feature MUST support automated acceptance coverage for ranking/ties, query controls, duplicate/out-of-order updates, snapshot recovery, marker alignment/accessibility, trade drill-down, provenance, simulated-analysis/disclaimer text, and empty/error states. (Constitution Definition of Done)

### Key Entities

- **Evaluation Result**: Immutable metrics and score for one completed Backtest Result under an exact scoring policy version; authoritative input to ranking.
- **Scoring Policy**: Versioned rules for metric direction, weights/normalization, eligibility, and deterministic tie-breaking.
- **Leaderboard Entry**: A Top-K projection item linking rank and projection metadata to one Evaluation Result and its provenance.
- **Strategy Definition**: Immutable strategy identity, version, parameters, and composition referenced by the ranked result.
- **Backtest Run**: The historical simulation context that produced signals, trades, and the Evaluation Result.
- **Candle Dataset**: Immutable Market Pair, Timeframe, provider, range, and Candle set used by the Backtest Run.
- **Signal**: Timestamped Buy/Sell/Hold strategy output, optionally carrying strength, reason, and overlay references.
- **Trade**: Simulated position lifecycle with Entry and Exit time/price, side, quantity, result, and generating Signal reference.
- **Visualization Overlay**: Provider-neutral chart description emitted or referenced by a strategy result, such as MA, Bollinger, Support, or Resistance.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a fixed eligible set, K, and scoring policy version, 100% of repeated ranking runs return the same ordered Evaluation Result identifiers, including tie fixtures.
- **SC-002**: The displayed leaderboard contains no more than K entries, uses contiguous ranks, and 100% of entries expose the required metrics and immutable provenance fields.
- **SC-003**: Under the documented demo load, at least 95% of leaderboard snapshot/filter/sort/page requests complete within 300 ms.
- **SC-004**: Under the documented demo load, at least 95% of qualifying completed evaluations become visible to a connected analyst within 1 second of backend ingestion, without page refresh.
- **SC-005**: Replaying any evaluation update at least twice produces exactly one Leaderboard Entry and one visible state transition for the evaluation/policy identity.
- **SC-006**: In acceptance fixtures, 100% of Buy, Sell, Entry, and Exit markers resolve to the recorded Candle/trade timestamp and price or are explicitly reported as unaligned; none are silently guessed.
- **SC-007**: In keyboard and non-color accessibility checks, analysts can distinguish Buy, Sell, Hold (when enabled), Entry, and Exit marker categories and open every displayed trade's detail without color being the sole cue.
- **SC-008**: For every displayed Leaderboard Entry and Trade fixture, analysts can reach the exact Strategy Definition/version, Backtest Run, dataset, Evaluation Result, execution context, and scoring policy version within one drill-down flow.
- **SC-009**: Duplicate/out-of-order event, reconnect, fewer-than-K, tie, no-trade, partial-data, and unavailable-overlay acceptance scenarios all complete without duplicate rows, rank regression, fabricated markers, or loss of the last valid snapshot.
- **SC-010**: Every leaderboard and ranked-result acceptance view displays the simulated-analysis label and non-investment-advice disclaimer, and automated text checks find no guaranteed-profit claim.

## Assumptions

- TV4/backtest-evaluation (or the equivalent upstream feature) supplies immutable Backtest Results, Signals, Trades, Evaluation Results, required metric semantics, and versioned scoring policies. TV5 consumes these contracts and does not recalculate financial metrics or simulate trades.
- Historical Candle data and the single-chart capability are supplied by the market/chart features. TV5 adds a ranked-result detail composition and overlays rather than owning market ingestion or the four-chart realtime dashboard.
- The assignment permits either persisting Leaderboard Entries or deriving them from Evaluation Results. The choice and consistency mechanism belong in `plan.md` as long as user-visible behavior is unchanged.
- `K` is configurable and defaults to 10 for the assignment demo; validation bounds are a contract/design concern.
- Actors describe product responsibilities rather than security roles. The trusted MVP demo does not add user accounts or a new authorization system.
- Timestamps are normalized to UTC for exchange and comparison; presentation may localize them while retaining the original instant.
- Hold signals are available through an explicit chart visibility control but may be hidden by default to reduce clutter.

## Out of Scope

- Calculating strategy indicators, generating Signals, simulating Trades, computing Evaluation metrics, or defining a new scoring formula; those belong to Strategy/Backtest/Evaluation features.
- Starting, stopping, pausing, or generating a continuous/random search run; TV5 only shows related run/update context.
- Market data collection, realtime Candle streaming, or the general four-timeframe dashboard.
- Strategy-specific conditional rendering keyed to concrete names; strategies may provide generic overlay data through a stable contract.
- Live trading, order placement, wallet/key management, investment advice, or claims of future profitability.
- News collection and sentiment analysis, except displaying already-versioned strategy/provenance data supplied through common contracts.
