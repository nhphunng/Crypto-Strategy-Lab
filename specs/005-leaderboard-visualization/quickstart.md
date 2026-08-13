# Quickstart: Validate Leaderboard and Trade Visualization

This guide validates the three independently demonstrable TV5 stories. It assumes the implementation tasks have been completed; it does not provide implementation code.

## Prerequisites

- Docker Desktop with Compose
- Backend dependencies locked for Python 3.12 and frontend dependencies installed for Node.js active LTS
- Deterministic TV5 fixture containing:
  - at least 12 compatible Evaluation Results for K=10;
  - one scoring tie resolved by the policy tie-breaker;
  - one no-trade result;
  - duplicate and out-of-order update messages;
  - one ranked result with Candles, MA/Support overlays, Buy/Sell Signals, and at least three Trades;
  - one unaligned/partial marker case.

Contracts: [REST OpenAPI](contracts/openapi.yaml), [leaderboard events](contracts/leaderboard-events.md), and [chart overlays](contracts/chart-overlays.md).

## 1. Start the Integrated Environment

```bash
docker compose -f infra/compose.yaml up -d postgres redis
docker compose -f infra/compose.yaml up -d api frontend
```

Apply migrations and load the deterministic TV5 fixture using the repository commands established during implementation. Do not use production/provider data for acceptance assertions.

## 2. Run Automated Quality Gates

```bash
cd backend
pytest tests/unit/leaderboard \
  tests/contract/test_leaderboard_api.py \
  tests/contract/test_leaderboard_events.py \
  tests/contract/test_ranked_result_api.py \
  tests/contract/test_leaderboard_extensibility.py \
  tests/contract/test_leaderboard_contract_sync.py \
  tests/integration/test_leaderboard_projection.py \
  tests/integration/test_ranked_result_detail.py \
  tests/integration/test_leaderboard_observability.py

cd ../frontend
npm run typecheck
npm run test -- leaderboard

cd ..
npx playwright test tests/e2e/leaderboard-visualization.spec.ts
k6 run tests/load/leaderboard.js
```

Expected: all ranking, transaction/idempotency, contract, frontend, E2E, and p95 checks pass. The load report states fixture size, concurrency, hardware, and observed p95 values.

## 3. Validate `LV-US-01`: View Top-K Strategies

1. Open the Leaderboard route with K=10, `rankBy=OVERALL_SCORE`, and the fixture's scoring policy.
2. Confirm exactly 10 of the 12 compatible results are shown with contiguous ranks.
3. Repeat the request and confirm the tied Evaluation Result IDs remain in the same order.
4. Confirm each row exposes Strategy Definition/version, Market Pair, Timeframe, dataset/range, Return, Win Rate, MDD, Number of Trades, score, and policy version.
5. Filter by required metric ranges, Market Pair, and Timeframe; presentation-sort and page the resulting Top-K without changing membership or stored metrics.
6. Inspect the no-trade fixture and confirm its documented eligibility/state is explicit.
7. Request the same scope with a different K or ranking metric and confirm it resolves a separate projection identity/version.
8. Confirm the view is labelled as simulated analysis and displays a visible non-investment-advice disclaimer with no guaranteed-profit claim.

Expected: deterministic Top-K, complete provenance summary, bounded controls, and no misleading missing/non-finite values.

## 4. Validate `LV-US-02`: Receive Incremental Updates

1. Keep the leaderboard open and record its `projectionVersion` and latest update time.
2. Complete/publish the fixture evaluation that enters Top-K.
3. Confirm the table updates without page refresh, ranks remain contiguous, and the version increments once.
4. Replay the same evaluation/event twice; confirm one entry and no second visible transition.
5. Deliver an older projection event; confirm it does not regress the view.
6. Disconnect the realtime channel, publish another qualifying update, and reconnect.

Expected: visible stale/reconnecting feedback followed by authoritative snapshot recovery to the newest projection; last valid rows remain usable throughout.

## 5. Validate `LV-US-03`: Visualize Signals and Trades

1. Open the prepared Top-1 entry.
2. Confirm its Market Pair, Timeframe, range, Candles, generic overlays, Buy/Sell, and Entry/Exit markers match the source fixture.
3. Enable Hold markers, then view the chart in grayscale or with a color-vision simulation; confirm Buy, Sell, Hold, Entry, and Exit remain distinguishable by label/shape.
4. Navigate the Trade table by keyboard and select Trade #3.
5. Confirm its Entry and Exit are both highlighted and detail shows times/prices, side, quantity, result, signal links, exact Strategy version, Backtest Run, dataset, execution configuration, Evaluation Result, and policy version.
6. Open the no-trade fixture and confirm Candles/available Signals remain visible with an explicit no-trade state.
7. Open the partial marker fixture and confirm the unaligned marker is reported rather than moved to a guessed Candle.
8. Confirm the detail view repeats the simulated-analysis label and visible non-investment-advice disclaimer.

Expected: explainable, timestamp-aligned results; complete drill-down provenance; non-color-only and keyboard-equivalent interaction.

## 6. Architecture Fitness Check

Register the implementation's test-only generic strategy/overlay fixture through the existing Strategy contract. Run leaderboard and visualization tests without modifying ranking or renderer branches.

Expected: the new Strategy Definition ranks through `EvaluationResult` and renders its supported generic overlay descriptor; Backtester, Evaluator, Leaderboard ranking, and visualization contain no strategy-name-specific change.

## Acceptance Summary

| Story | Pass signal |
|-------|-------------|
| `LV-US-01` | Fixed inputs produce the same Top-K and expose complete metrics/version context. |
| `LV-US-02` | Qualifying evaluations appear within target latency; duplicates/out-of-order events are harmless; reconnect recovers the snapshot. |
| `LV-US-03` | Buy/Sell and Entry/Exit align and remain accessible; Trade selection explains metrics through immutable provenance. |
