# Tasks: Deterministic Backtest and Evaluation

**Input**: Design documents from `/specs/004-backtest-evaluation/`

**Tests**: Required by FR-021, Constitution DOD-06, and the plan's test-first strategy. Contract/domain tests precede boundary implementation.

## Phase 1: Setup

**Purpose**: Establish feature-owned modules and deterministic fixtures without implementing behavior.

- [X] T001 Create Backtest/Evaluation package initializers in `backend/src/crypto_lab/domain/backtest/__init__.py`, `backend/src/crypto_lab/domain/evaluation/__init__.py`, `backend/src/crypto_lab/application/backtests/__init__.py`, and `backend/src/crypto_lab/application/evaluations/__init__.py`
- [ ] T002 [P] Add canonical profitable, losing, no-trade, no-loss, zero-variance, redundant-Signal, and forced-close fixtures in `backend/tests/fixtures/backtest_evaluation/scenarios.py`
- [ ] T003 [P] Add the shared TV1 Dataset/TV3 Strategy Analysis determinism fixture in `backend/tests/fixtures/backtest_evaluation/cross_feature.py`
- [ ] T004 Reconcile Feature 001 after merge and update TV1/TV3/TV5 compatibility references if its merged contract differs in `specs/004-backtest-evaluation/contracts/backtest-domain-contract.md`

---

## Phase 2: Foundational Domain and Persistence

**Purpose**: Define shared types, ports, storage, and migration required by every story.

**CRITICAL**: No user-story implementation begins until this phase is complete.

- [ ] T005 Define Decimal precision, canonical serialization, hashing, UTC, and version value objects in `backend/src/crypto_lab/domain/backtest/configuration.py`
- [ ] T006 [P] Define categorized Backtest errors and stable issue/no-op codes in `backend/src/crypto_lab/domain/backtest/errors.py`
- [ ] T007 [P] Define immutable Execution Policy, Backtest Run configuration, validation, and lifecycle types in `backend/src/crypto_lab/domain/backtest/configuration.py`
- [ ] T008 [P] Define immutable Trade and fill value objects with reconciliation invariants in `backend/src/crypto_lab/domain/backtest/trade.py`
- [ ] T009 [P] Define Equity Point/Curve values and accounting invariants in `backend/src/crypto_lab/domain/backtest/equity.py`
- [ ] T010 [P] Define Backtest Result, Signal snapshot, provenance, and checksum value objects in `backend/src/crypto_lab/domain/backtest/result.py`
- [ ] T011 [P] Define Evaluation/Scoring Policy, metric descriptor, eligibility, and version types in `backend/src/crypto_lab/domain/evaluation/policy.py`
- [ ] T012 [P] Define immutable Evaluation Result and comparison-context values in `backend/src/crypto_lab/domain/evaluation/result.py`
- [ ] T013 Define typed Dataset reader, Strategy analyzer, Backtest repository, and clock ports in `backend/src/crypto_lab/application/backtests/ports.py`
- [ ] T014 [P] Define typed Backtest reader, Evaluation repository, and policy reader ports in `backend/src/crypto_lab/application/evaluations/ports.py`
- [ ] T015 [P] Add SQLAlchemy mappings/constraints for policies, runs, results, Signal snapshots, Trades, and Equity Points in `backend/src/crypto_lab/infrastructure/persistence/backtest_models.py`
- [ ] T016 [P] Add SQLAlchemy mappings/constraints for Evaluation Results and policies in `backend/src/crypto_lab/infrastructure/persistence/evaluation_models.py`
- [ ] T017 Create immutable Alembic upgrade/downgrade for all Feature 004 tables, constraints, and indexes in `backend/migrations/versions/20260813_004_create_backtest_evaluation.py`
- [ ] T018 Implement atomic append-only Backtest repository primitives and paginated reads in `backend/src/crypto_lab/infrastructure/persistence/repositories/backtest_repository.py`
- [ ] T019 [P] Implement immutable Evaluation repository and policy lookup primitives in `backend/src/crypto_lab/infrastructure/persistence/repositories/evaluation_repository.py`
- [ ] T020 [P] Add Pydantic request/response/error DTOs aligned to OpenAPI in `backend/src/crypto_lab/api/schemas/backtest_evaluation.py`
- [ ] T021 Wire repositories, TV1 Dataset reader, TV3 Strategy analyzer, policies, and use cases in `backend/src/crypto_lab/api/dependencies.py`

**Checkpoint**: Domain types compile; migration round-trips; repositories and cross-feature ports construct without API business rules.

---

## Phase 3: User Story 1 — Run a Reproducible Historical Backtest (Priority: P1)

**Goal**: Create and execute one exact deterministic, look-ahead-safe Backtest Run.

**Independent Test**: Repeat one complete canonical input 100 times for the same checksum; reject open/future/incomplete/misaligned inputs before persistence.

### Tests for User Story 1

- [ ] T022 [P] [US1] Write failing unit tests for configuration validation, next-open timing, last-Candle exclusion, canonical fingerprints, and 100-run determinism in `backend/tests/unit/backtest/test_engine.py`
- [ ] T023 [P] [US1] Write failing TV1 Dataset contract tests for COMPLETE status, version/checksum/membership verification, no provider access, and fail-closed integrity in `backend/tests/contract/test_backtest_market_data_contract.py`
- [ ] T024 [P] [US1] Write failing TV3 contract tests for exact definition/version, ordered Signals, warm-up, alignment, compatibility errors, and no MA/RSI branches in `backend/tests/contract/test_backtest_strategy_contract.py`
- [ ] T025 [P] [US1] Write failing REST contract tests for create/start/get envelopes, lifecycle, validation codes, and analysis-only fields in `backend/tests/contract/test_backtest_api.py`
- [ ] T026 [P] [US1] Write failing PostgreSQL integration tests for atomic result persistence, duplicate `jobId` idempotency/conflict, terminal states, and migration round-trip in `backend/tests/integration/test_backtest_persistence.py`

### Implementation for User Story 1

- [ ] T027 [US1] Implement create-or-resolve Backtest Run validation and persistence orchestration in `backend/src/crypto_lab/application/backtests/create_run.py`
- [ ] T028 [US1] Implement pure next-Candle-open long-only simulation, no-op recording, slippage/fees, force-close, Equity Points, and checksum in `backend/src/crypto_lab/domain/backtest/engine.py`
- [ ] T029 [US1] Implement TV1 Dataset verification, TV3 analysis invocation, state transitions, atomic result write, and safe failure mapping in `backend/src/crypto_lab/application/backtests/execute_run.py`
- [ ] T030 [US1] Implement create/start/get Backtest Run and get Backtest Result routes in `backend/src/crypto_lab/api/routes/backtests.py`
- [ ] T031 [US1] Register Backtest routes and default Execution Policy composition in `backend/src/crypto_lab/main.py` and `backend/src/crypto_lab/api/dependencies.py`

**Checkpoint**: `BT-US-01` passes independently without Trade-page UI, metrics, scoring, comparison, queue, or worker.

---

## Phase 4: User Story 2 — Inspect Simulated Trades and Equity (Priority: P2)

**Goal**: Explain final equity through ordered Trade and Equity Curve detail.

**Independent Test**: Retrieve a prepared completed result and reconcile every fill/cost/balance, redundant Signal, forced close, and final equity.

### Tests for User Story 2

- [ ] T032 [P] [US2] Write failing unit tests for quantity rounding, entry/exit costs, redundant Signal no-ops, forced close, P/L, Trade return, and accounting identity in `backend/tests/unit/backtest/test_accounting.py`
- [ ] T033 [P] [US2] Write failing REST contract tests for bounded Trade/Equity pagination, decimal/UTC encoding, close reasons, and provenance in `backend/tests/contract/test_backtest_detail_api.py`
- [ ] T034 [P] [US2] Write failing PostgreSQL integration tests for ordered child persistence, exact counts, pagination, and immutable retrieval in `backend/tests/integration/test_backtest_detail_persistence.py`

### Implementation for User Story 2

- [ ] T035 [US2] Complete Trade lifecycle calculations and stable Signal linkage in `backend/src/crypto_lab/domain/backtest/trade.py`
- [ ] T036 [US2] Complete Equity Curve marking and reconciliation helpers in `backend/src/crypto_lab/domain/backtest/equity.py`
- [ ] T037 [US2] Implement bounded result, Trade, and Equity Curve query orchestration in `backend/src/crypto_lab/application/backtests/get_result.py`
- [ ] T038 [US2] Implement paginated Trade and Equity Curve endpoints in `backend/src/crypto_lab/api/routes/backtests.py`

**Checkpoint**: `BT-US-02` passes independently using a prepared Backtest Result without Evaluation or Leaderboard.

---

## Phase 5: User Story 3 — Calculate Performance and Risk Metrics (Priority: P3)

**Goal**: Produce deterministic required/extended metrics from an immutable Backtest Result.

**Independent Test**: Evaluate profitable, losing, no-trade, no-loss, drawdown, insufficient-return, and zero-variance fixtures with exact expected/null values.

### Tests for User Story 3

- [ ] T039 [P] [US3] Write failing table-driven tests for Total Return, Win Rate, Maximum Drawdown, Number of Trades, Profit Factor, Sharpe annualization, precision, and null semantics in `backend/tests/unit/evaluation/test_metrics.py`
- [ ] T040 [P] [US3] Write failing contract tests proving Evaluation consumes Backtest Result only and never concrete Strategy behavior in `backend/tests/contract/test_evaluation_domain_contract.py`
- [ ] T041 [P] [US3] Write failing persistence/API tests for policy identity, idempotent Evaluation Result creation, immutable historical metrics, and no NaN/infinity in `backend/tests/integration/test_evaluation_persistence.py`

### Implementation for User Story 3

- [ ] T042 [US3] Implement documented metric formulas, annualization, Decimal precision, and undefined-value semantics in `backend/src/crypto_lab/domain/evaluation/metrics.py`
- [ ] T043 [US3] Implement evaluation orchestration from immutable Backtest Result and exact Evaluation Policy in `backend/src/crypto_lab/application/evaluations/evaluate_result.py`
- [ ] T044 [US3] Implement create/get Evaluation Result routes and error mapping in `backend/src/crypto_lab/api/routes/evaluations.py`
- [ ] T045 [US3] Register Evaluation routes and initial Evaluation Policy composition in `backend/src/crypto_lab/main.py` and `backend/src/crypto_lab/api/dependencies.py`

**Checkpoint**: `EV-US-01` passes independently with raw metrics before overall score behavior is enabled.

---

## Phase 6: User Story 4 — Apply a Versioned Scoring Policy (Priority: P4)

**Goal**: Produce a deterministic score/eligibility result with immutable policy provenance.

**Independent Test**: Apply `balanced-v1` repeatedly to boundary/null fixtures and verify fixed-bound score, eligibility, exclusion reasons, and new-result behavior for a new policy version.

### Tests for User Story 4

- [ ] T046 [P] [US4] Write failing unit tests for fixed-bound normalization, directions, weights, score bounds, null eligibility, and total tie-break order in `backend/tests/unit/evaluation/test_scoring.py`
- [ ] T047 [P] [US4] Write failing TV5 consumer contract tests for required score, eligibility, policy versions, metric nulls, provenance, and idempotency in `backend/tests/contract/test_evaluation_result_contract.py`
- [ ] T048 [P] [US4] Write failing PostgreSQL tests for immutable policy versions and historical re-evaluation without overwrite in `backend/tests/integration/test_scoring_policy_persistence.py`

### Implementation for User Story 4

- [ ] T049 [US4] Implement generic fixed-bound normalization, eligibility, score, and tie-break keys in `backend/src/crypto_lab/domain/evaluation/scoring.py`
- [ ] T050 [US4] Add versioned `balanced-v1` policy bootstrap data and validation in `backend/src/crypto_lab/api/dependencies.py`
- [ ] T051 [US4] Extend evaluation orchestration and DTO mapping with score, eligibility, exclusion reasons, and policy fingerprints in `backend/src/crypto_lab/application/evaluations/evaluate_result.py` and `backend/src/crypto_lab/api/schemas/backtest_evaluation.py`

**Checkpoint**: `EV-US-02` passes; Feature 005 can consume complete immutable Evaluation Results.

---

## Phase 7: User Story 5 — Compare Evaluation Results (Priority: P5)

**Goal**: Compare only with complete visible context and never silently equate incompatible experiments.

**Independent Test**: Compare compatible fixtures, then vary every context dimension and verify strict rejection or contextual warnings without changing stored values.

### Tests for User Story 5

- [ ] T052 [P] [US5] Write failing unit tests for complete comparison-dimension detection, strict/contextual modes, and stable metric ordering in `backend/tests/unit/evaluation/test_comparison.py`
- [ ] T053 [P] [US5] Write failing REST contract tests for bounded ID count, difference payloads, ordering, validation, and immutable values in `backend/tests/contract/test_evaluation_comparison_api.py`

### Implementation for User Story 5

- [ ] T054 [US5] Implement compatibility keys, complete difference reporting, strict rejection, and contextual comparison in `backend/src/crypto_lab/domain/evaluation/comparison.py`
- [ ] T055 [US5] Implement bounded Evaluation Result loading and comparison orchestration in `backend/src/crypto_lab/application/evaluations/compare_results.py`
- [ ] T056 [US5] Implement the evaluation-comparison route and response mapping in `backend/src/crypto_lab/api/routes/evaluations.py`

**Checkpoint**: All five included canonical SRS stories pass independently and together.

---

## Phase 8: Polish and Cross-Cutting Gates

- [ ] T057 [P] Add structured run/evaluation logs, correlation propagation, duration/failure metrics, and sensitive-data guards in `backend/src/crypto_lab/infrastructure/observability/backtest_evaluation.py`
- [ ] T058 [P] Add architecture fitness tests preventing framework imports and concrete Strategy-name branches in `backend/tests/architecture/test_backtest_evaluation_boundaries.py`
- [ ] T059 [P] Add executable OpenAPI/domain/TV1/TV3/TV5 contract-sync coverage in `backend/tests/contract/test_backtest_evaluation_contract_sync.py`
- [ ] T060 [P] Add the documented 10,000-Candle runtime and bounded-read benchmark in `backend/tests/performance/test_backtest_evaluation.py`
- [ ] T061 Add transaction-failure, duplicate/concurrent submission, checksum corruption, and safe-error recovery tests in `backend/tests/integration/test_backtest_evaluation_reliability.py`
- [ ] T062 Execute every quickstart scenario and record checksums, policy versions, counts, p95/runtime, environment, and Proposed-ADR review status in `specs/004-backtest-evaluation/quickstart.md`
- [ ] T063 [P] Add feature test markers and benchmark configuration in `backend/pyproject.toml`
- [ ] T064 Run Ruff, mypy, complete pytest suites, migration upgrade/downgrade, OpenAPI validation, and secret/dependency checks from `backend/pyproject.toml`

## Dependencies

- Phase 1 → Phase 2 blocks all stories; T004 is an external merge/re-review gate.
- US1 is the MVP and establishes Backtest Result persistence.
- US2 depends on US1's simulation/result but is independently testable from a prepared result.
- US3 depends on the Backtest Result contract, not concrete Strategy code.
- US4 depends on US3 metrics; a prepared metric fixture permits independent scoring tests.
- US5 depends on persisted Evaluation Results; prepared results permit independent comparison tests.
- Polish follows all stories.

## Parallel Opportunities

- T002–T003 can run in parallel; T004 depends on Feature 001 merge.
- T006–T012, T014–T016, and T019–T020 are parallel after shared conventions T005.
- Each story's test tasks marked `[P]` can be written in parallel before its implementation.
- US2 detail queries and US3 metric work can proceed in parallel after US1 stabilizes the Backtest Result contract.
- T057–T060 can proceed in parallel after all public contracts stabilize.

## Requirements Coverage

| Requirement area | Tasks |
|---|---|
| Exact inputs, validation, dataset/strategy contracts, no look-ahead (FR-001–FR-005) | T005–T007, T013, T022–T031 |
| Execution policy, Trades, Equity Curve, accounting, no-trade (FR-006–FR-010) | T008–T010, T028, T032–T038 |
| Metrics and undefined semantics (FR-011–FR-013) | T011–T012, T039–T045 |
| Scoring, versioning, idempotent Evaluation Result (FR-014–FR-017) | T014, T016, T019, T041, T046–T051 |
| Comparison and audit retrieval (FR-018–FR-019) | T037–T038, T052–T056 |
| Safe failures, automated coverage, analysis-only boundary (FR-020–FR-022) | T006, T020, T025–T026, T057–T064 |
| Determinism/performance/provenance success criteria | T022–T026, T032–T034, T039–T041, T046–T048, T052–T053, T057–T064 |

## Implementation Strategy

### MVP First

Implement Phases 1–3 to deliver one deterministic direct Backtest Run with immutable provenance and checksum. This proves the central architectural boundary before detail queries, metrics, scoring, or comparison.

### Incremental Delivery

1. US1: deterministic run and result.
2. US2: explainable Trades and Equity Curve.
3. US3: required/extended metrics.
4. US4: versioned score for TV5.
5. US5: context-safe comparison.
6. Polish: observability, contract sync, performance, reliability, and cross-feature re-review.

## Format Validation

All 64 tasks use the required checkbox, sequential ID, optional `[P]`, required story label within user-story phases, actionable description, and concrete file path.
