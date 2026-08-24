# Quickstart: Validate Realtime Multi-Chart Dashboard

## Purpose

Use these scenarios after implementation to prove `MD-US-02`, `MD-US-03`, `MTC-US-01`, and `MTC-US-02` without running strategy, backtest, leaderboard, News, or Sentiment features.

## Approval gates

- [x] TV1 and TV2 approved [openapi.yaml](contracts/openapi.yaml) and the shared Candle rules in [data-model.md](data-model.md) on 2026-08-19.
- [x] The team accepted `docs/ARCHITECTURE.md`, ADR-002, and ADR-003.
- [x] Feature 002 is approved to begin implementation without changing the accepted version 1 Candle/history semantics.

The backend/frontend skeleton described in [plan.md](plan.md) is created and validated by Phase 1 implementation tasks after these governance gates.

## Prerequisites

- Docker Desktop with Docker Compose
- A read-only Binance market-data configuration, or the deterministic provider stub for tests
- Node.js active LTS and Python 3.12 when running services outside containers
- Ports and environment variables documented in the future root `.env.example`; no secrets committed

## Start the local stack

```bash
docker compose up -d postgres api frontend
docker compose ps
```

Expected: PostgreSQL and API become healthy, the frontend is reachable, and optional News/Sentiment services are not required for chart readiness.

## Contract and focused automated checks

```bash
pytest backend/tests/unit/market_data -q
pytest backend/tests/contract/test_market_data_contracts.py -q
pytest backend/tests/integration/test_realtime_market_data.py -q
npm --prefix frontend test -- --run tests/market-chart
npx playwright test tests/e2e/realtime-multi-chart.spec.ts
```

Expected: Candle identity/merge, event validation, slot limit, subscription reference counting, historical bootstrap, reconnect/backfill, keyboard controls, responsive layout, and slot isolation pass.

## Scenario 1: Receive realtime candles (`MD-US-02`)

1. Open the Market dashboard with one `BTCUSDT` / `5m` slot.
2. Confirm a bounded historical range appears and the slot reaches `LIVE`.
3. Publish deterministic open updates, a duplicate, an out-of-order event, and the closing update through the provider stub.

Expected:

- The open Candle changes in place.
- Exactly one Candle exists for each identity.
- The series never moves backward.
- The final update marks the Candle closed.
- No page refresh or repeated polling occurs.

## Scenario 2: View one to four charts (`MTC-US-01`)

1. Add slots until four are visible.
2. Select `5m`, `15m`, `1h`, and `4h`.
3. Attempt to add a fifth slot.
4. Resize the viewport below the documented narrow-screen breakpoint.

Expected:

- All four slots retain stable identity, timeframe, status, and Candles.
- The fifth request is rejected with an actionable limit message.
- The narrow layout becomes one column without losing controls.
- Keyboard-only operation can add/remove slots and change timeframes; status meaning does not rely on color.

## Scenario 3: Change one timeframe (`MTC-US-02`)

1. With four live slots, record each slot's timeframe and viewport.
2. Change only `slot-1` from `5m` to `1h`.
3. Immediately deliver a late `5m` history response/event for the old generation.

Expected:

- Only `slot-1` loads the new range and changes subscription.
- The old `5m` work does not enter the new generation.
- The previous slot binding is released with no orphan upstream subscription.
- The other three chart instances, data, status, and viewports stay unchanged.

## Scenario 4: Recover after disconnect (`MD-US-03`)

1. Disconnect the provider stream for one active selection.
2. Generate at least two closed Candles while disconnected.
3. Restore the provider before automatic attempts are exhausted.

Expected:

- Only affected slots show `STALE` then `RECONNECTING`.
- The backend performs bounded retry and historical backfill.
- Recovery requests an initially missing gap through the accepted TV1 historical use case; the use case persists canonical closed Candles before the selection can return to `LIVE`.
- The series contains the missing closed intervals exactly once.
- The selection returns to `LIVE` only after continuity is complete.

Repeat with recovery disabled until attempts are exhausted. Expected: affected slots reach `ERROR`, expose manual retry, and healthy selections remain live.

## Scenario 5: Optional-service isolation

Stop News and Sentiment containers if present while all four charts are live.

Expected: market history, realtime updates, controls, and recovery remain usable; optional-service failure is observable but does not change market chart status.

## Realtime propagation and soak check

```bash
k6 run tests/load/realtime-market-data.js
```

Document the environment and use at least:

- 10 dashboard sessions × 4 logical slots
- 8 distinct `BTCUSDT` timeframes across sessions
- 1 accepted update per second per distinct selection
- 10-minute latency run and a separate 30-minute four-slot soak

Pass conditions:

- At least 95% of accepted updates reach the chart update boundary within one second of backend ingestion.
- No dashboard exceeds four logical slot bindings.
- No duplicate Candle identity, time regression, orphan subscription, or full-dashboard reset is observed.
- Metrics distinguish logical slots from unique upstream selections and expose reconnect/backfill failures.

## Validation evidence (2026-08-20)

Environment used for the recorded runs:

- Windows 10/11 build `10.0.26200`
- Node.js `v22.16.0`, npm `10.9.2`
- Python `3.12.13` (`backend/.venv`), pytest `8.4.0`, Ruff `0.11.13`, mypy `1.16.0`
- Docker Desktop + Compose (`postgres:16-alpine`, `api`, `frontend` images)
- Playwright test runner with installed Google Chrome (no downloaded Chromium required)
- k6 `v2.0.0` at `C:\Program Files\k6\k6.exe`; the load script uses the legacy `k6/ws` module because k6 v2.0.0's `k6/websockets` never dispatches `open` against this server
- Deterministic provider stub `backend/scripts/realtime_stub_server.py` (run with `backend/.venv/Scripts/python.exe` from `backend/`) when k6 targets the local API on `ws://127.0.0.1:8000/ws/v1/market-data`

Commands run and results:

```bash
docker compose up -d postgres api frontend   # api healthy :8000, frontend :5173, postgres healthy :55432, migrate exited 0
docker compose ps                            # all services Up (healthy)
pytest backend/tests/unit/market_data -q                       # 87 passed
pytest backend/tests/contract/test_market_data_contracts.py -q # 5 passed
pytest backend/tests/integration/test_realtime_market_data.py -q # 2 passed
pytest -q                                      # full backend suite: 148 passed (against compose Postgres)
npm --prefix frontend test -- --run tests/market-chart  # 10 files, 66 tests passed
npm test -- --run                              # full frontend unit suite: 13 files, 76 tests passed
npm run typecheck                              # passed with no diagnostics
npm run build                                  # passed (non-fatal Vite 500 kB warning on main JS chunk)
node node_modules/@playwright/test/cli.js test tests/e2e/realtime-multi-chart.spec.ts --project=chromium
# 5 passed (slot limit, responsive layout, timeframe isolation, disconnect/backfill recovery, exhausted recovery + manual retry)
```

Backend static analysis (run during the same validation window):

```bash
.\.venv\Scripts\python.exe -m ruff check src tests migrations   # passed
.\.venv\Scripts\python.exe -m ruff format --check src tests migrations  # passed (126 files already formatted)
.\.venv\Scripts\python.exe -m mypy                                # no issues in 81 source files
```

k6 results against the deterministic stub (documented load profile per the section above):

```bash
k6 run --env SCENARIO=smoke   --env WS_URL=ws://127.0.0.1:8000/ws/v1/market-data tests/load/realtime-market-data.js
# 2 VUs x 4 slots x 40s session: 16/16 checks, 598/598 samples, all thresholds 100%, 0 samples beyond 1s
k6 run --env SCENARIO=latency --env WS_URL=ws://127.0.0.1:8000/ws/v1/market-data tests/load/realtime-market-data.js
# 10 sessions x 4 slots x 600s: 80/80 checks, 23,884/23,884 samples, all thresholds 100%, 0 samples beyond 1s
k6 run --env SCENARIO=soak    --env WS_URL=ws://127.0.0.1:8000/ws/v1/market-data tests/load/realtime-market-data.js
# 1 session x 4 slots x 1800s: 8/8 checks, 7,166 candles, 0 beyond 1s, 0 recovery events, limitRejected=true, all thresholds 100%
```

Scenario coverage note: Scenarios 1-5 are exercised by the contract, focused, integration, unit, and Playwright tests listed above; the Playwright suite runs Scenarios 2-4 in a real browser against the local stack (including the late-old-generation isolation case and both recovery outcomes).

### Convergence revalidation (2026-08-20, Asia/Bangkok)

The Phase 8 recovery fix was validated on the same Windows/Python/Node environment above. PostgreSQL was started with Docker Compose and reported healthy on `localhost:55432`.

```powershell
# TDD RED: adapter intentionally absent
backend\.venv\Scripts\python.exe -m pytest backend/tests/integration/test_realtime_recovery.py -q
# collection error: ModuleNotFoundError for historical_backfill (expected RED)

# GREEN after routing gap acquisition through the accepted TV1 historical service
backend\.venv\Scripts\python.exe -m pytest backend/tests/integration/test_realtime_recovery.py -q
# 9 passed in 0.43s

cd backend
.\.venv\Scripts\python.exe -m pytest -q
# 149 passed in 16.63s against Compose PostgreSQL
.\.venv\Scripts\python.exe -m ruff check src tests migrations
# All checks passed
.\.venv\Scripts\python.exe -m ruff format --check src tests migrations
# 132 files already formatted
.\.venv\Scripts\python.exe -m mypy
# Success: no issues found in 84 source files

cd ..\frontend
F:\nodejs\npm.cmd test -- --run
# 13 files, 76 tests passed
F:\nodejs\npm.cmd run typecheck
# passed with no diagnostics
F:\nodejs\npm.cmd run build
# passed; Vite 8.2.1 built 1,884 modules (non-fatal >500 kB chunk warning)

cd ..
F:\nodejs\node.exe node_modules/@playwright/test/cli.js test tests/e2e/realtime-multi-chart.spec.ts --project=chromium
# 5 passed in 17.6s

& 'C:\Program Files\k6\k6.exe' run --env SCENARIO=smoke --env WS_URL=ws://127.0.0.1:8000/ws/v1/market-data tests/load/realtime-market-data.js
# 16/16 checks; 320/320 latency, duplicate-identity, and time-regression samples; all thresholds 100%
```

The recovery integration test starts with an empty repository, serves the missing `10:15`, `10:20`, and `10:25` closed Candles from the historical provider, verifies the provider was called for `[10:15, 10:30)`, and confirms the canonical values were persisted before the second `LIVE` state.

Final Spec Kit closure on the same date: the second `$speckit-converge` run reported `Converged` without appending tasks; the final strict read-only `$speckit-analyze` reported zero CRITICAL/HIGH findings and 100% FR/NFR task coverage. The later Phase 9 deployment-path and multi-session remediations brought the task ledger to `58/58`.

### Phase 9 frontend-origin proxy validation (2026-08-20, Asia/Bangkok)

The failure was reproduced before implementation: port `5173` returned `index.html` instead of JSON for `/api/...`, and `/ws/...` was not upgraded. The focused configuration test was written first and failed both Vite and Nginx assertions. After adding the reverse proxies, the following commands were run on Windows build `10.0.26200`, Node.js `v22.16.0`, npm `10.9.2`, Docker Compose, Playwright `1.55.0`, and installed Google Chrome:

```powershell
cd frontend
F:\nodejs\node.exe node_modules/vitest/vitest.mjs run tests/market-chart/proxy-config.test.ts
# 1 file, 2 tests passed
F:\nodejs\npm.cmd test -- --run
# 14 files, 78 tests passed
F:\nodejs\npm.cmd run typecheck
# passed with no diagnostics
F:\nodejs\npm.cmd run build
# passed; 1,884 modules, known non-fatal >500 kB chunk warning only

cd ..
docker compose build frontend
docker compose up -d frontend
# postgres healthy, migrate exited 0, api healthy, rebuilt frontend running on :5173

curl.exe -sS -D - http://localhost:5173/api/v1/market-data/dimensions -o NUL
# HTTP/1.1 200 OK; Server: nginx; Content-Type: application/json; x-request-id present

curl.exe --http1.1 --max-time 3 -i -N `
  -H "Connection: Upgrade" -H "Upgrade: websocket" `
  -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: SGVsbG9Xb3JsZDEyMzQ1Ng==" `
  http://localhost:5173/ws/v1/market-data
# HTTP/1.1 101 Switching Protocols; curl then timed out as expected while the socket remained open

$env:COMPOSE_E2E='1'
F:\nodejs\node.exe node_modules/@playwright/test/cli.js test tests/e2e/realtime-multi-chart-compose.spec.ts --config=playwright.compose.config.ts --project=chromium
# 1 passed in 4.9s; no mocked route, two equal-selection tabs reached Live, and tab 2 stayed Live after tab 1 closed

F:\nodejs\node.exe node_modules/@playwright/test/cli.js test tests/e2e/realtime-multi-chart.spec.ts --project=chromium
# 5 passed in 12.1s
```

An additional interactive run in the Codex in-app browser opened `http://localhost:5173/market` and displayed a real `BTCUSDT 5m` Lightweight Chart in `Live` state with Binance OHLCV values. The Compose services were intentionally left running for manual inspection.

The first two-client run honestly failed: an already-active `BTCUSDT/5m` selection caused the second connection to remain `Loading`. The backend TDD RED was `ModuleNotFoundError` for the intentionally absent `realtime_selection_hub`. After adding the hub and rebuilding the API image, validation was:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/integration/test_realtime_selection_hub.py -q
# 1 passed; two clients received the same heartbeat through one upstream stream; first release did not close it; final release did

cd backend
.\.venv\Scripts\python.exe -m pytest -q
# 150 passed in 14.96s against Compose PostgreSQL (one non-code pytest cache permission warning)
.\.venv\Scripts\python.exe -m ruff check src tests migrations
# All checks passed
.\.venv\Scripts\python.exe -m ruff format --check src tests migrations
# 134 files already formatted
.\.venv\Scripts\python.exe -m mypy
# Success: no issues found in 85 source files
```

The final `$speckit-converge` audit after T058 reported `Converged`: the deployed REST/WebSocket path and process-wide equal-selection fan-out now match the accepted plan and data model, so no further convergence task was appended.

## Stop the stack

```bash
docker compose down
```
