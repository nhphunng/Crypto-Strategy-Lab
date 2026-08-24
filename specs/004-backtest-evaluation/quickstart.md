# Quickstart: Validate Deterministic Backtest and Evaluation

## Prerequisites

- Feature 001 contract fixture with one `COMPLETE` immutable dataset and verified checksum.
- Feature 003 contract fixture with exact Strategy Definition and ordered deterministic Signals.
- PostgreSQL available through the project Docker Compose or Testcontainers.
- Python 3.12 environment with backend development dependencies.

## Validation Sequence

1. Run format, lint, and type checks.
2. Run backtest/evaluation unit tests.
3. Run TV1/TV3/TV5 contract compatibility tests.
4. Run PostgreSQL migration, repository, idempotency, and API integration tests.
5. Run the 10,000-Candle benchmark and record reference environment/runtime.

Suggested commands after implementation:

```powershell
cd backend
ruff check src tests
mypy src
pytest tests/unit/backtest tests/unit/evaluation
pytest tests/contract/test_backtest_market_data_contract.py tests/contract/test_backtest_strategy_contract.py tests/contract/test_backtest_api.py tests/contract/test_evaluation_result_contract.py
pytest tests/integration/test_backtest_persistence.py tests/integration/test_evaluation_persistence.py
pytest tests/performance/test_backtest_evaluation.py -m performance
```

## Scenario A — Determinism and look-ahead

- Execute the same exact dataset/Strategy/configuration/seed 100 times.
- Expect one input fingerprint, byte-equivalent canonical result content, and one result checksum.
- Mutate a future/open/duplicate/out-of-order Candle or misalign one Signal.
- Expect rejection before any completed result is persisted.

## Scenario B — Execution accounting

- Use Signals containing warm-up, HOLD, BUY, redundant BUY, SELL, redundant SELL, and a final-Candle BUY.
- Expect BUY/SELL fills at next opens, adverse slippage, fees on both fills, stable no-op reasons, and no final-Candle entry.
- Run a second fixture ending while long.
- Expect force-close at final close with `END_OF_RANGE`.
- Reconcile cash, position, every Trade, every Equity Point, and final equity.

## Scenario C — Metrics and scoring

- Evaluate profitable, losing, no-trade, no-loss, drawdown, insufficient-return, and zero-variance fixtures.
- Expect exact documented metric values; no-trade and undefined cases use the specified null/zero semantics.
- Apply `balanced-v1` twice and expect one equivalent score/result identity.
- Apply a new policy version and expect a new Evaluation Result without changing the old one.

## Scenario D — Comparison and TV5 handoff

- Compare two results with identical context and expect compatible ordering.
- Change each compatibility dimension one at a time and expect a complete warning/rejection list.
- Validate the Evaluation Result and Trade fixtures against Feature 005 consumer fields.

## Expected Evidence

Record test counts, checksums, policy versions, measured benchmark runtime/p95 reads, reference hardware, and any architecture/ADR approval status before implementation sign-off.

## Implementation Evidence (2026-08-24)

- Scenarios A-D are executable across the Feature 004 unit, REST contract, PostgreSQL integration, architecture, and performance suites. The final complete backend run passed `396` tests with one unrelated generated-strategy sandbox test skipped because its optional prebuilt Docker image was unavailable.
- Canonical two-Trade fixture evidence: input fingerprint `47858cbc826d7bd27ca3cb1fba8fba491a9b8348917d4cc8ed6b632dff8d8f03`, result checksum `69af199087fd5bcbc913d2a1f7d556cf1665dcd32251c83e5b9905851671f2a5`, Evaluation fingerprint `06994387766851ef98c9d50ee03d816f6c388c66f4fd6d1e68073295a54bd4a4`, `5` Signals, `2` Trades, `5` Equity Points, score `92.300000000000000000`, eligible `true`.
- PostgreSQL tests at `localhost:55432` prove atomic child persistence/rollback, concurrent duplicate submission, immutable policy versions, idempotent evaluation, exact pagination/counts, checksum-conflict detection, terminal safe failure, and both Feature 004 and full migration upgrade/downgrade round-trips.
- Ruff passed over all `src` and `tests` with cache disabled; mypy passed all `133` source files; checked-in/generated OpenAPI validation passed; `pip check` reported no broken requirements; the tracked-source secret scan found no populated credential assignment and no populated `.env` file is committed (`.env.example` only).
- 10,000-Candle benchmark: `1.20s`; bounded PostgreSQL Result/Trade/Equity read p95: `12.249ms`, below the `300ms` interactive gate. Reference environment: Python `3.12.7`, Windows NT `10.0.26200` AMD64, Intel64 Family 6 Model 154, local PostgreSQL.
- Bootstrapped policies: execution `next-open-long-only/1.0.0`, evaluation `standard-metrics/1.0.0`, and scoring `balanced/1.0.0` (`balanced-v1` semantics).
- ADR-006 remains Proposed; the policy is versioned and historical evaluations are not reinterpreted.

## Single Backtest Frontend Integration Evidence (2026-08-24)

- The Single Backtest screen now loads exact registered Strategy versions and the bootstrapped Execution/Evaluation/Scoring Policy identities from same-origin REST APIs; it no longer renders calculated mock results after Run.
- The typed browser workflow materializes Feature 001 Dataset data, creates or resolves an immutable built-in Feature 003 Strategy Definition, creates/starts Feature 004 Backtest Run, evaluates the result, and retrieves every paginated Candle, Trade, and Equity Point. Runtime parsers reject malformed response contracts.
- Docker-backed smoke through the frontend nginx proxy (`localhost:5173`) completed with a real Binance `BTCUSDT` 15m Dataset for `[2026-08-01,2026-08-02)`: 96 Candles, 6 Trades, 96 Equity Points, Total Return `-0.766270874215122758`, score `46.33010409664556441`, eligible `true`.
- The smoke exposed and fixed a one-unit-at-18-decimal reconciliation defect: Trade invariants now apply the same published-notional rounding used by entry/exit accounting. A realistic BTC-price regression test preserves the exact accounting gate rather than adding a tolerance.
- Validation after the fix: Feature 004 focused suites `21 passed`; real PostgreSQL integration `60 passed`; changed backend source mypy `0 issues`; Ruff passed; frontend Vitest `127 passed`; TypeScript typecheck, production Vite build, Docker frontend build, and Sites packaging tests passed.
- In-app visual inspection was unavailable because no browser session was connected in the validation environment. Docker HTTP proxy, production build, UI compilation, and the full workflow contract remain validated; final manual viewport/interaction acceptance is still recommended.
