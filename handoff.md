# Feature 002 Handoff

Updated: 2026-08-20 (Asia/Bangkok)

Read [`context.md`](context.md) for the detailed implementation and validation record.

## Repository State

- Branch: `feat/002-realtime-multi-chart`
- Feature directory: `specs/002-realtime-multi-chart`
- Accepted baseline: `387a62b docs: accept market data architecture and contracts`
- Architecture and ADR-003: `Accepted`
- TV1/TV2 Candle/history contract version 1: accepted and unchanged
- Working tree: intentionally dirty with uncommitted Feature 002 work

Do not reset, clean, checkout, or discard the worktree. Commit only on an explicit user request.

## Final Stop Point

Feature 002 is complete at `58/58` tasks. The convergence remediation is implemented and validated:

- `T055`: recovery now acquires uncached closed-Candle gaps through a TV2 adapter over TV1 `HistoricalMarketDataService` before `LIVE`.
- `T056`: README, quickstart, context, and handoff are synchronized with the real Market dashboard and validation state.
- `T057`: Vite and production Nginx proxy same-origin `/api/` and WebSocket `/ws/` traffic to the backend; a non-mock Compose browser smoke test guards the deployed path.
- `T058`: `RealtimeSelectionHub` fans one provider stream out to equal selections across dashboard connections and releases it only after the final client leaves.
- No TV1-owned Candle/history contract was modified.

Mandatory closure completed:

1. `T055` and `T056` are `[X]`.
2. The second `$speckit-converge` run reported `Converged` with no new task.
3. Final strict read-only `$speckit-analyze` reported zero CRITICAL/HIGH findings.
4. `T054`, `T057`, and `T058` are `[X]`; all Feature 002 tasks are complete.
5. The post-T058 `$speckit-converge` audit reported `Converged` without another task.

## Phase 8 Validation

- TDD RED: focused recovery test failed because the adapter module was absent.
- Focused GREEN: `backend/tests/integration/test_realtime_recovery.py` — `9 passed`.
- Backend full suite with healthy Compose PostgreSQL: `149 passed in 16.63s`.
- Ruff check PASS; Ruff format check `132 files`; mypy PASS across `84 source files`.
- Frontend unit: `14 files`, `78 tests` PASS.
- Typecheck and production build PASS; build has only the known non-fatal chunk-size warning.
- Playwright Chrome: `5/5` PASS.
- Real Compose Playwright smoke on port `5173`: `1/1` PASS without REST/WebSocket mocks.
- Two-tab equal-selection smoke: PASS; both tabs reached `Live`, and the remaining tab stayed `Live` after the first closed.
- Backend full suite after the hub fix: `150 passed`; Ruff, format check, and mypy PASS.
- k6 smoke: `16/16` checks, `320/320` samples for all three custom thresholds, all 100%.

Exact commands, environment, and results are in `specs/002-realtime-multi-chart/quickstart.md`.

## Key Recovery Files

- `backend/src/crypto_lab/application/chart_delivery/historical_backfill.py`
- `backend/src/crypto_lab/application/chart_delivery/stream_candles.py`
- `backend/src/crypto_lab/api/websocket/market_data_channel.py`
- `backend/tests/integration/test_realtime_recovery.py`

The production WebSocket composition uses `HistoricalGapBackfillAdapter(container.historical)`. The adapter exposes only a narrow recovery reader and delegates acquisition, validation, persistence, and completeness derivation to the accepted TV1 historical use case.

## Decisions to Preserve

- TanStack Query and its cancellation/generation boundaries.
- TradingView Lightweight Charts v5 and public attribution.
- Stable 1–4 slot identities and one dashboard WebSocket.
- Reference-counted equal selections with per-slot state and viewport.
- Provider-neutral versioned REST/WebSocket contracts.
- Bounded recovery with truthful stale/reconnecting/error states.
- TV1 owns Candle/history semantics; TV2 consumes through approved boundaries.

Crypto Strategy Lab is for research and education. It is not investment advice and does not guarantee profit.
