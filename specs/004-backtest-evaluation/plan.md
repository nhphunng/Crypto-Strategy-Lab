# Implementation Plan: Deterministic Backtest and Evaluation

**Branch**: `feat/004-backtest-evaluation-spec-plan` | **Date**: 2026-08-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-backtest-evaluation/spec.md`

## Summary

Build a framework-independent Backtest and Evaluation domain that consumes Feature 001 `COMPLETE` immutable Candle Datasets and Feature 003 deterministic Strategy Analysis Results. The engine simulates one spot long-only position with next-Candle-open execution, all-available-cash sizing, adverse percentage slippage, fees on both fills, deterministic no-ops, and forced end-of-range closure. It persists immutable Signals, Trades, Equity Curve, Backtest Result, metrics, and versioned score provenance for Feature 005. A thin application/API boundary supports direct single-run execution; queues, distributed workers, retries, and frontend rendering remain deferred.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Python standard library (`dataclasses`, `decimal`, `enum`, `hashlib`, `statistics`, `typing`), Pydantic 2, FastAPI, SQLAlchemy 2, Alembic

**Storage**: PostgreSQL 16 for immutable Backtest Runs/Results, Signal snapshots, Trades, Equity Points, Evaluation Results, and versioned policies

**Testing**: pytest and pytest-asyncio; real PostgreSQL through Testcontainers or Docker Compose for persistence/API integration; Ruff and mypy

**Target Platform**: Linux containers and local Docker Compose development

**Project Type**: Backend module in the modular-monolith web application; no frontend, broker, or worker implementation in this feature

**Performance Goals**: A deterministic 10,000-Candle single-strategy benchmark completes simulation and evaluation within 5 seconds on the documented reference environment; p95 bounded result/trade/equity reads complete within 300 ms under demo load

**Constraints**: Decimal-safe accounting; no look-ahead; exact immutable dataset and Strategy versions; no concrete Strategy-name branches; append-only results and policies; no NaN/infinity; result idempotency; bounded paginated collections

**Scale/Scope**: One Strategy Definition and one Market Pair/Timeframe per run, up to 10,000 Candles in the acceptance benchmark, one long position, five core/extended metrics, one initial scoring policy, synchronous direct execution only

## Constitution Check

*GATE: Passed for design generation. Team review of the Proposed architecture and ADRs remains a pre-implementation approval gate.*

### Pre-Research Gate

| Principle | Result | Evidence |
|---|---|---|
| Spec-Driven Development | PASS | `spec.md` traces `BT-US-01/02`, `EV-US-01/02/03`, applicable FRs, flows, and NFRs. |
| Simplicity Over Premature Scale | PASS | Pure domain plus application/persistence/API boundaries; no queue, worker, cache, service split, Kafka, or Kubernetes. |
| Cross-Document Consistency | PASS | Uses canonical `CandleDataset`, `StrategyDefinition`, `Signal`, `BacktestRun`, `BacktestResult`, `Trade`, and `EvaluationResult`. |
| Architecture and ADR Governance | PASS WITH REVIEW GATE | Architecture and ADR-001 through ADR-005 were read; all remain Proposed and are not represented as Accepted. |
| Domain Owns Business Rules | PASS | Execution accounting, metrics, scoring, compatibility, and checksum rules remain framework-independent. |
| Thin Delivery Boundary | PASS | API validates/maps and delegates; it contains no simulation, metric, or scoring logic. |
| Immutable Provenance | PASS | Dataset, Strategy, execution, evaluation, and scoring versions are retained and never resolved as implicit latest. |
| Integration Testing Over Mocking | PASS | Pure calculations use fixtures; PostgreSQL behavior, migrations, and API boundaries use a real database. |
| Analysis Only | PASS | Only simulated Trades are produced; no exchange credential or live-order boundary is introduced. |

### Post-Design Gate

PASS with the same pre-implementation architecture review gate. Contracts preserve TV1/TV3/TV5 ownership, data-model writes are append-only and idempotent, the quickstart proves determinism/look-ahead/accounting, and no constitution violation requires Complexity Tracking.

### Architecture Decision References

- **Architecture baseline**: `docs/ARCHITECTURE.md` — Status: Proposed; followed as a review input for modular boundaries and Backtest → Evaluation → Leaderboard flow.
- **ADR-001** Modular Monolith with Separate Worker Processes — Proposed; this slice stays in the monolith and deliberately defers workers.
- **ADR-002** Layered Boundaries and Ports/Adapters — Proposed; used for domain/application/infrastructure/delivery separation.
- **ADR-003** Provider-Neutral Market Data Contract — Proposed; refined by Feature 001 contract version `1`, which TV4 consumes without provider fields.
- **ADR-004** Strategy Contract, Registry, and Immutable Versions — Proposed; refined by Feature 003 strategy contract `1.0.0`.
- **ADR-005** Deterministic and Reproducible Backtesting — Proposed; primary review input for provenance, look-ahead, immutable results, and metric edge cases.
- **ADR-006** Versioned Fixed-Bound Scoring Policy — Proposed; records the TV4/TV5 scoring decision. `balanced-v1` cannot be presented as the approved project default until team review changes this ADR to Accepted or approves a replacement.
- **Deviations**: None from the approved Constitution/SRS. Proposed documents are not treated as binding approval.

## Design Overview

### Runtime Flow

1. Create a Backtest Run with exact dataset, Strategy Definition, execution policy/configuration, and correlation identities.
2. Resolve Feature 001 dataset metadata/membership without provider access; require `COMPLETE` and verify count/checksum.
3. Resolve Feature 003 exact Strategy Definition and execute contract `1.0.0`; validate the returned immutable Strategy Analysis Result and ordered Signals.
4. Simulate each evaluated Signal at the next Candle open, record deterministic no-ops and fills, mark equity at each Candle close, and force-close at the final close if needed.
5. Canonicalize and persist the immutable Backtest Result, Signals, Trades, Equity Curve, execution provenance, and checksum atomically/idempotently.
6. Evaluate the Backtest Result through an exact Evaluation Policy; apply an exact Scoring Policy; persist one immutable Evaluation Result per identity.
7. Query bounded detail or compare compatible Evaluation Results. Feature 005 consumes these records and never recalculates them.

### Boundary Ownership

- Feature 001 owns Candle/Dataset acquisition and immutable membership.
- Feature 003 owns Strategy Definition validation and Signal generation.
- Feature 004 owns simulated execution, Signal snapshot retention, Trade/Equity accounting, metrics, policies, scoring, and comparison compatibility.
- Feature 005 owns ranking, Top-K projection, realtime leaderboard events, and visualization composition.

## Project Structure

### Documentation

```text
specs/004-backtest-evaluation/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── openapi.yaml
│   ├── backtest-domain-contract.md
│   └── evaluation-result-contract.md
├── checklists/
│   ├── requirements.md
│   └── backtest-evaluation.md
└── tasks.md
```

### Source Code

```text
backend/
├── src/crypto_lab/
│   ├── domain/backtest/
│   │   ├── configuration.py
│   │   ├── engine.py
│   │   ├── equity.py
│   │   ├── errors.py
│   │   ├── result.py
│   │   └── trade.py
│   ├── domain/evaluation/
│   │   ├── comparison.py
│   │   ├── metrics.py
│   │   ├── policy.py
│   │   ├── result.py
│   │   └── scoring.py
│   ├── application/backtests/
│   │   ├── create_run.py
│   │   ├── execute_run.py
│   │   ├── get_result.py
│   │   └── ports.py
│   ├── application/evaluations/
│   │   ├── compare_results.py
│   │   ├── evaluate_result.py
│   │   └── ports.py
│   ├── infrastructure/persistence/
│   │   ├── backtest_models.py
│   │   ├── evaluation_models.py
│   │   ├── repositories/backtest_repository.py
│   │   └── repositories/evaluation_repository.py
│   └── api/
│       ├── routes/backtests.py
│       ├── routes/evaluations.py
│       └── schemas/backtest_evaluation.py
├── migrations/versions/20260813_004_create_backtest_evaluation.py
└── tests/
    ├── fixtures/backtest_evaluation/
    ├── unit/backtest/
    ├── unit/evaluation/
    ├── contract/
    ├── integration/
    └── performance/
```

**Structure Decision**: Extend the existing backend modular-monolith layout. Pure simulation/evaluation rules live in `domain`; application services coordinate TV1/TV3 and repositories; persistence implements append-only storage; API routes expose direct run/evaluation workflows. No frontend or worker path is added.

## Test Strategy

- Write domain and cross-feature contract tests before implementation.
- Share TV1 dataset and TV3 Signal determinism fixtures; verify no provider access and no MA/RSI branching.
- Table-drive execution cases: warm-up/HOLD, next-open fill, repeated Signals, fee/slippage, insufficient cash, last-Candle Signal, force-close, no-trade, and losing/profitable paths.
- Assert the accounting identity and canonical checksum across 100 repeated runs.
- Table-drive metrics for profitable, losing, no-trade, no-loss, drawdown, insufficient-return, and zero-variance cases.
- Use real PostgreSQL for atomic persistence, duplicate idempotency, immutable policies/results, pagination, migrations, and concurrent create-or-resolve.
- Validate OpenAPI examples and Feature 005 consumer compatibility against the same DTO fixtures.
- Record reference hardware/data and measured p95/runtime in `quickstart.md`.

## Complexity Tracking

No constitution violation or exceptional complexity is introduced.
