# Current Chat Context

Updated: 2026-08-20 (Asia/Bangkok)

## Repository

- Workspace: `F:\D\Uni\YEAR_3\SEM_3\KTPM\Crypto-Strategy-Lab`
- Branch: `feat/002-realtime-multi-chart`
- Feature: `specs/002-realtime-multi-chart`
- Accepted baseline commit: `387a62b docs: accept market data architecture and contracts`
- Feature 002 implementation remains uncommitted in a dirty worktree. Preserve it; do not reset, clean, or discard changes.

## Final Feature State

Feature 002 is complete at `58/58` tasks. Architecture, ADR-002, ADR-003, and the TV1/TV2 version 1 Candle/history boundary are `Accepted`.

The first Phase 7 analysis found two blocking gaps:

1. Constitution DOD-06 required `$speckit-converge`; it was incorrectly described as optional.
2. Production recovery read only the repository, so an uncached disconnect gap could not be acquired through TV1 historical data.
3. README still described Feature 002 as unimplemented and mock-only.

`$speckit-converge` appended Phase 8 tasks `T055` and `T056`. T055 now routes recovery through a TV2 adapter over the accepted `HistoricalMarketDataService.get_range` use case. No TV1 Candle/history contract was changed. T056 synchronized README, quickstart, context, and handoff. A later real-Compose browser check found that the frontend origin returned the SPA document for `/api/` and `/ws/`; Phase 9 task `T057` added tested Vite/Nginx REST and WebSocket reverse proxies plus an opt-in non-mock Compose Playwright smoke test. That smoke exposed a second runtime gap: equal selections across dashboard connections competed for the singleton Binance adapter. `T058` added a process-wide selection hub with connection-scoped clients so one upstream stream fans out safely until the last client releases it.

Closure completed:

1. `T055` and `T056` are `[X]`.
2. The second `$speckit-converge` run reported `Converged` without appending tasks.
3. The final strict read-only `$speckit-analyze` reported zero CRITICAL/HIGH findings and 100% FR/NFR task coverage.
4. `T054`, `T057`, and `T058` are `[X]`; the ledger is `58/58`.
5. The worktree remains uncommitted; commit only if the user explicitly requests it.

## Phase and Task Status

- Phases 1–7: implemented and validated.
- Phase 8: complete.
- Phase 9: complete.
- Tasks `T001–T058`: `[X]`.
- Final convergence: `Converged`.
- Final analysis: zero CRITICAL/HIGH findings.

## Phase 8 Implementation

New TV2-owned adapter:

- `backend/src/crypto_lab/application/chart_delivery/historical_backfill.py`
- `HistoricalGapBackfillAdapter` exposes the accepted TV1 historical use case as the narrow `read_candles` recovery seam.
- `market_data_channel.py` composes the adapter with `container.historical` instead of injecting `container.repository` directly.
- `stream_candles.py` remains independent of the concrete provider and TV1 implementation.

Test-first evidence:

- RED: recovery integration test failed collection because `historical_backfill` did not exist.
- GREEN: recovery suite `9 passed`.
- The new test begins with an empty repository, obtains three missing closed Candles through the historical provider, confirms `[10:15, 10:30)` acquisition, persistence, and `LIVE` only after continuity.

## Latest Validation Checkpoint

Environment:

- Windows build `10.0.26200`
- Python `3.12.13`, pytest `8.4.0`, Ruff `0.11.13`, mypy `1.16.0`
- Node.js `v22.16.0`, npm `10.9.2`, Vitest `4.1.10`, Vite `8.2.1`
- Docker Compose PostgreSQL 16 healthy on `localhost:55432`
- Playwright with installed Google Chrome
- k6 `v2.0.0`

Results:

- Backend full suite: `149 passed in 16.63s`.
- Ruff check: PASS.
- Ruff format check: `132 files already formatted`.
- mypy: `Success: no issues found in 84 source files`.
- Frontend: `14 files, 78 tests passed`.
- TypeScript typecheck: PASS.
- Production build: PASS; non-fatal Vite chunk-size warning.
- Playwright: `5 passed in 17.6s`.
- Real Compose Playwright smoke through `http://127.0.0.1:5173`: `1 passed in 4.4s`; observed REST JSON, the frontend WebSocket, `Live`, and a non-empty Candle series without mocked routes.
- Multi-session checkpoint: backend `150 passed`; fan-out test proves one upstream acquisition and last-reference release; the two-tab Compose smoke passed in `4.9s` and kept tab 2 `Live` after tab 1 closed.
- k6 smoke: `16/16` checks and `320/320` samples for every threshold, all 100%.
- `git diff --check`: PASS with existing LF/CRLF working-copy warnings only.

Detailed real commands and results are recorded in `specs/002-realtime-multi-chart/quickstart.md`.

## Architecture Decisions to Preserve

- One app-level TanStack Query client; never one per slot.
- TanStack `AbortSignal` cancels obsolete history queries.
- TradingView Lightweight Charts v5 remains the renderer with public attribution.
- One dashboard WebSocket, connection-local slot identities, and reference-counted equal selections.
- Route updates by selection; guard slot mutations by slot ID, generation, and selection.
- Closed Candle is terminal; revision resets to 1 only for a new bucket.
- Recovery must acquire uncached gaps through the accepted TV1 historical use case before `LIVE`.
- Do not alter the TV1-owned Candle/history contract without cross-review.

## Important Files

- `specs/002-realtime-multi-chart/{spec.md,plan.md,tasks.md,quickstart.md,data-model.md}`
- `specs/002-realtime-multi-chart/contracts/`
- `backend/src/crypto_lab/application/chart_delivery/historical_backfill.py`
- `backend/src/crypto_lab/application/chart_delivery/stream_candles.py`
- `backend/src/crypto_lab/api/websocket/market_data_channel.py`
- `backend/tests/integration/test_realtime_recovery.py`
- `frontend/src/features/market-chart/`
- `tests/e2e/realtime-multi-chart.spec.ts`
- `tests/load/realtime-market-data.js`

Crypto Strategy Lab is for research and education. It is not investment advice and does not guarantee profit.
