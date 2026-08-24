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

- Feature 004 focused suites: 21 passed, including 100-run checksum determinism, TV1/TV3/TV5 contracts, execution/accounting, metrics, scoring, comparison, architecture, contract sync, and performance.
- Full repository suite excluding the unavailable migration round-trip: 234 passed and 8 skipped. PostgreSQL at `localhost:55432` was not running, and the Docker Desktop daemon was unavailable in the validation environment.
- Ruff: all `src` and `tests` checks passed.
- mypy: 118 source files passed with no issues.
- 10,000-Candle benchmark: 1.01 seconds test call on the current Windows development machine, below the 5-second gate.
- Bootstrapped policies: execution `next-open-long-only/1.0.0`, evaluation `standard-metrics/1.0.0`, and scoring `balanced/1.0.0` (`balanced-v1` semantics).
- ADR-006 remains Proposed; the policy is versioned and historical evaluations are not reinterpreted.

## Single Backtest Frontend Integration Evidence (2026-08-24)

- The Single Backtest screen now loads exact registered Strategy versions and the bootstrapped Execution/Evaluation/Scoring Policy identities from same-origin REST APIs; it no longer renders calculated mock results after Run.
- The typed browser workflow materializes Feature 001 Dataset data, creates or resolves an immutable built-in Feature 003 Strategy Definition, creates/starts Feature 004 Backtest Run, evaluates the result, and retrieves every paginated Candle, Trade, and Equity Point. Runtime parsers reject malformed response contracts.
- Docker-backed smoke through the frontend nginx proxy (`localhost:5173`) completed with a real Binance `BTCUSDT` 15m Dataset for `[2026-08-01,2026-08-02)`: 96 Candles, 6 Trades, 96 Equity Points, Total Return `-0.766270874215122758`, score `46.33010409664556441`, eligible `true`.
- The smoke exposed and fixed a one-unit-at-18-decimal reconciliation defect: Trade invariants now apply the same published-notional rounding used by entry/exit accounting. A realistic BTC-price regression test preserves the exact accounting gate rather than adding a tolerance.
- Validation after the fix: Feature 004 focused suites `21 passed`; real PostgreSQL integration `60 passed`; changed backend source mypy `0 issues`; Ruff passed; frontend Vitest `127 passed`; TypeScript typecheck, production Vite build, Docker frontend build, and Sites packaging tests passed.
- In-app visual inspection was unavailable because no browser session was connected in the validation environment. Docker HTTP proxy, production build, UI compilation, and the full workflow contract remain validated; final manual viewport/interaction acceptance is still recommended.
