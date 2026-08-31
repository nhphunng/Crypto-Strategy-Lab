# Quickstart: Validate Leaderboard and Trade Visualization

This guide validates the three independently demonstrable TV5 stories against the implemented feature. Measured outcomes from the 2026-08-23 verification run are recorded at the end of each section.

## Prerequisites

- Docker Desktop with Compose (PostgreSQL 16)
- Python 3.12 for the backend, Node.js active LTS for the frontend
- The deterministic TV5 fixture in `backend/tests/fixtures/leaderboard.py`, which contains:
  - 13 compatible Evaluation Results for K=10 (10 qualify, 2 fall outside Top-K, 1 is upstream-ineligible);
  - one scoring tie (`80.0`) resolved by the policy tie-breaker;
  - one no-trade result inside Top-K;
  - one result whose Sharpe Ratio is undefined;
  - Candles, Buy/Sell/Hold Signals and 1–4 Trades per result;
  - one deliberately unaligned Signal timestamp.

Contracts: [REST OpenAPI](contracts/openapi.yaml), [leaderboard events](contracts/leaderboard-events.md), and [chart overlays](contracts/chart-overlays.md).

## 1. Start the Integrated Environment

```bash
docker compose up -d postgres
docker compose run --rm migrate                      # alembic upgrade head
python backend/scripts/seed_leaderboard_demo.py      # deterministic fixture only
docker compose up -d api                             # or: uvicorn crypto_lab.main:app --port 8000
npm --prefix frontend run dev                        # http://localhost:5173
```

The frontend calls the API on its own origin and relies on the Vite dev proxy
(and the nginx container in Compose) to forward `/api` and `/ws`. Set
`VITE_API_BASE_URL` only when the API is reached directly on another origin.

With `CSL_AUTO_EVALUATION_ENABLED=true` (the default in `docker-compose.yml`) the
API populates the leaderboard by itself: it materializes the configured dataset,
backtests every registered Strategy, evaluates each result, and ranks it. The
seed script below stays useful for the deterministic acceptance fixture.

The seed script writes only immutable upstream records. The leaderboard projection is always derived by the feature itself; it is never seeded directly.

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
npm run test

cd ..
npm run test:e2e:leaderboard                         # or npm run test:e2e for every suite
k6 run tests/load/leaderboard.js                     # add -e EVENTS=1 for the event target
```

`playwright.config.ts` starts the dev server itself and uses the `chrome`
channel, so install it once with `npx playwright install chrome`. The API must
already be running and seeded.

**Measured 2026-08-23**, on the merge with `main` that includes feature 002: **272 backend tests**, **124 frontend tests**, and **11/11 Playwright scenarios** (6 leaderboard + 5 realtime multi-chart) pass. `npm run typecheck` is clean and `ruff check` is clean for every file this feature owns.

## 3. Validate `LV-US-01`: View Top-K Strategies

1. Open the Leaderboard route with K=10, `rankBy=OVERALL_SCORE`, and the fixture's scoring policy.
2. Confirm exactly 10 of the 13 compatible results are shown with contiguous ranks.
3. Repeat the request and confirm the tied Evaluation Result IDs remain in the same order.
4. Confirm each row exposes Strategy Definition/version, Market Pair, Timeframe, dataset/range, Return, Win Rate, MDD, Number of Trades, score, and policy version.
5. Filter by required metric ranges, presentation-sort and page the resulting Top-K without changing membership or stored metrics.
6. Inspect the no-trade fixture and confirm its documented eligibility/state is explicit.
7. Request the same scope with a different K or ranking metric and confirm it resolves a separate projection identity/version.
8. Confirm the view is labelled as simulated analysis and displays a visible non-investment-advice disclaimer with no guaranteed-profit claim.

**Measured**: ranks `#1..#10` are contiguous and stable across repeated requests; the tie resolves as `sr-breakout` before `ma-rsi` (higher Total Return); the upstream-ineligible candidate with score `99.0` never enters Top-K; `minScore=80` narrows the view to 5 rows while ranks and `k` stay unchanged; `k=3` and `rankBy=MAX_DRAWDOWN` each return a different `leaderboardId`.

## 4. Validate `LV-US-02`: Receive Incremental Updates

1. Keep the leaderboard open and record its `projectionVersion` and latest update time.
2. Complete one more qualifying evaluation:

   ```bash
   python backend/scripts/seed_leaderboard_demo.py --complete
   ```

3. Confirm the table updates without a page refresh, ranks remain contiguous, and the version increments once.
4. Replay the same evaluation/event twice; confirm one entry and no second visible transition.
5. Deliver an older projection event; confirm it does not regress the view.
6. Disconnect the realtime channel, publish another qualifying update, and reconnect.

**Measured**: the browser moved from `projection v1` to the newly published version with no refresh, the new candidate appeared at rank 1, and the status strip stayed `LIVE`. Repeating `on_evaluation_completed` for the same evaluation produced zero additional entries, zero additional update records, and no new event. `--complete` commits only the projection change; the running API process claims the durable record and publishes it, which is the cross-process proof that publication is retry-safe.

## 5. Validate `LV-US-03`: Visualize Signals and Trades

1. Open the prepared Top-1 entry.
2. Confirm its Market Pair, Timeframe, range, Candles, overlays, Buy/Sell, and Entry/Exit markers match the source fixture.
3. Enable Hold markers, then view the chart in grayscale; confirm Buy, Sell, Hold, Entry, and Exit remain distinguishable by label/shape.
4. Navigate the Trade table by keyboard and select Trade #3.
5. Confirm its Entry and Exit are both highlighted and detail shows times/prices, side, quantity, result, signal links, exact Strategy version, Backtest Run, dataset, execution configuration, Evaluation Result, and policy version.
6. Open the no-trade fixture and confirm Candles/available Signals remain visible with an explicit no-trade state.
7. Open the partial marker fixture and confirm the unaligned marker is reported rather than moved to a guessed Candle.
8. Confirm the detail view repeats the simulated-analysis label and visible non-investment-advice disclaimer.

**Measured**: the Top-1 detail rendered 192 Candles and 17 markers for `BTCUSDT 15m 2026-07-01 → 2026-07-03`; keyboard selection of a Trade highlighted exactly one `ENTRY` and one `EXIT` plus the range band; the unaligned `BUY` at `2026-07-01T07:37:00Z` was listed with its reason and never placed on a Candle; the no-trade entry kept Candles and Hold Signals visible with `trades: EMPTY`; overlays report `UNAVAILABLE` with the documented reason because the current upstream Backtest Result publishes no overlay descriptors.

## 6. Architecture Fitness Check

`backend/tests/contract/test_leaderboard_extensibility.py` registers a test-only `future-unknown-strategy` Strategy Definition and asserts that it ranks and visualizes through the same contracts. The suite also fails if any ranking or mapping module mentions a concrete strategy term or compares `strategy_id` against a string literal. `frontend/tests/leaderboard/RankedResultDetail.test.tsx` renders `LINE`, `BAND`, and `ZONE` overlays emitted by an unknown strategy.

**Measured**: the unknown strategy entered at rank 1 with its recorded metrics and rendered generic markers, with no renderer or ranking change.

## 7. Performance Targets

```bash
k6 run -e DURATION=20s -e VUS=10 tests/load/leaderboard.js
k6 run -e DURATION=20s -e VUS=4 -e EVENTS=1 tests/load/leaderboard.js
```

**Measured 2026-08-23** (Windows 11 host, API in a Python 3.12 container, PostgreSQL 16 in Compose, 13-candidate fixture):

| Target | Threshold | Observed |
|---|---|---|
| SC-003 snapshot/filter/sort/page p95 | <= 300 ms | 187.97 ms at 10 VUs (1952 requests, 0 failures); 72.41 ms at 4 VUs |
| SC-004 update visible to a connected client p95 | <= 1000 ms | 231.6 ms (max 236 ms) over three published updates |

## Acceptance Summary

| Story | Pass signal | Status |
|---|---|---|
| `LV-US-01` | Fixed inputs produce the same Top-K and expose complete metrics/version context. | Verified |
| `LV-US-02` | Qualifying evaluations appear within target latency; duplicates/out-of-order events are harmless; reconnect recovers the snapshot. | Verified |
| `LV-US-03` | Buy/Sell and Entry/Exit align and remain accessible; Trade selection explains metrics through immutable provenance. | Verified |

## Known Deviations

- Overlay descriptors are reported as `UNAVAILABLE` until an upstream Strategy/Backtest feature publishes them. The contract, renderer, and tests already support `LINE`, `BAND`, and `ZONE`.
- The demo database is shared with the integration suite, which truncates leaderboard and upstream tables. Re-run `python backend/scripts/seed_leaderboard_demo.py` after running the backend tests.
- The ranked-result chart is `features/leaderboard/components/RankedResultChart.tsx`, not the feature 002 `market-chart` component. The realtime chart is built on lightweight-charts and exposes no scale for shape-based markers or selection rings, so the leaderboard keeps its own dependency-free SVG surface until a second feature needs it.
- Error responses use the repository-wide `error` payload from feature 001 rather than the `data` payload originally drafted in `contracts/openapi.yaml`; the contract file now documents the shared shape and a contract-sync test enforces it.
