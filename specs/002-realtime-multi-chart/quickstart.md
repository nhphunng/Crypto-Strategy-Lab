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

## Stop the stack

```bash
docker compose down
```
