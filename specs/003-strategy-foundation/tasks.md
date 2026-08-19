---

description: "Dependency-ordered implementation tasks for Strategy Foundation"
---

# Tasks: Strategy Foundation

**Input**: Design documents from `/specs/003-strategy-foundation/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Required. The specification mandates deterministic acceptance fixtures, and the constitution requires domain/contract tests before implementation.

**Organization**: Tasks are grouped by the four independently testable user stories in `spec.md`. Requirement IDs in each task provide direct traceability.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: May run in parallel because it targets a different file and has no dependency on another incomplete task in the same phase.
- **[Story]**: Maps to `US1` through `US4` in `spec.md`.
- Every task names an exact repository path.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the approved Python backend package and quality gates without implementing strategy behavior.

- [ ] T001 Create the Python 3.12 backend package, dependency groups, and locked tool configuration in `backend/pyproject.toml`
- [ ] T002 [P] Create the `crypto_lab` package roots and strategy module exports in `backend/src/crypto_lab/__init__.py` and `backend/src/crypto_lab/domain/strategy/__init__.py`
- [ ] T003 [P] Configure shared pytest markers, Decimal comparison policy, and deterministic-test defaults in `backend/tests/conftest.py`
- [ ] T004 [P] Add backend Ruff, mypy, migration, and pytest quality gates in `.github/workflows/backend.yml`

**Checkpoint**: Backend imports, static checks, and an empty pytest suite run from a clean environment.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement the contract-neutral immutable values required by every user story.

**⚠️ CRITICAL**: No user-story implementation begins until this phase passes its tests.

- [ ] T005 [P] Write contract-version compatibility tests for FR-025, FR-027, and FR-035 in `backend/tests/unit/strategy/test_contract_version.py`
- [ ] T006 [P] Write parameter-definition/default/canonicalization tests for FR-004, FR-017, FR-031, and SC-003 in `backend/tests/unit/strategy/test_parameters.py`
- [ ] T007 [P] Write immutable Signal identity, action, phase, and ordering tests for FR-018, FR-019, FR-020, and FR-021 in `backend/tests/unit/strategy/test_signal.py`
- [ ] T008 [P] Write categorized all-or-nothing error tests for FR-037 and FR-038 in `backend/tests/unit/strategy/test_errors.py`
- [ ] T009 Implement semantic version parsing and supported-major/minor-range rules for FR-025, FR-027, and FR-035 in `backend/src/crypto_lab/domain/strategy/version.py`
- [ ] T010 Implement immutable parameter definitions, relationship validation, defaults, canonical values, and fingerprints for FR-004, FR-017, and FR-031 in `backend/src/crypto_lab/domain/strategy/parameters.py`
- [ ] T011 [P] Implement categorized Strategy errors and structured issues for FR-037 and FR-038 in `backend/src/crypto_lab/domain/strategy/errors.py`
- [ ] T012 Implement immutable Strategy Definition values and deterministic content fingerprints for FR-031, FR-032, and FR-033 in `backend/src/crypto_lab/domain/strategy/definition.py`
- [ ] T013 Implement immutable Signal and Strategy Analysis Result values with deterministic identity and ordering for FR-018, FR-019, FR-020, FR-021, FR-022, and FR-023 in `backend/src/crypto_lab/domain/strategy/signal.py`
- [ ] T014 Define the common Strategy protocol and capability metadata for FR-001, FR-005, FR-024, and FR-030 in `backend/src/crypto_lab/domain/strategy/protocol.py`

**Checkpoint**: Version, parameter, definition, error, and Signal values are immutable, deterministic, and framework-independent.

---

## Phase 3: User Story 1 - Run MA and RSI Strategies (Priority: P1) 🎯 MVP

**Goal**: Run deterministic MA and RSI calculations against validated normalized contexts with explicit parameter, boundary, look-ahead, and warm-up behavior.

**Independent Test**: Execute fixed MA/RSI fixtures for normal, strict crossing, equality, warm-up, empty, invalid parameter/context, and insufficient-history cases; repeat each fixture and compare the entire ordered result.

### Tests for User Story 1

> Write these tests first and observe the intended failures before implementation.

- [ ] T015 [P] [US1] Create immutable normalized Candle, dataset, MA, and RSI fixture builders for FR-002, FR-003, and FR-007 in `backend/tests/fixtures/strategy/factories.py`
- [ ] T016 [P] [US1] Add Strategy Context validation tests for empty, unsorted, duplicate, incomplete, invalid-OHLCV, open, future, and misaligned input covering FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, and SC-004 in `backend/tests/unit/strategy/test_context.py`
- [ ] T017 [P] [US1] Add MA default/range, arithmetic-mean, crossing, equality, warm-up, empty, insufficient-history, and repeatability fixtures covering FR-009, FR-010, FR-011, SC-003, and SC-005 in `backend/tests/unit/strategy/test_moving_average.py`
- [ ] T018 [P] [US1] Add RSI default/range/relationship, Wilder, threshold-exit, equality, constant, one-directional, warm-up, and repeatability fixtures covering FR-012, FR-013, FR-014, FR-015, FR-016, SC-003, and SC-005 in `backend/tests/unit/strategy/test_rsi.py`
- [ ] T019 [P] [US1] Add no-look-ahead and ten-run byte-equivalent canonical result tests for FR-006, FR-007, and SC-001 in `backend/tests/contract/test_strategy_contract.py`

### Implementation for User Story 1

- [ ] T020 [US1] Implement immutable Strategy Context construction, strict validation, and deterministic fingerprinting for FR-002 through FR-008 in `backend/src/crypto_lab/domain/strategy/context.py`
- [ ] T021 [US1] Implement MA metadata, parameter validation, Decimal rolling mean, crossing actions, and warm-up reasons for FR-009 through FR-011 and FR-017 in `backend/src/crypto_lab/domain/strategy/implementations/moving_average.py`
- [ ] T022 [US1] Implement RSI metadata, Wilder Decimal calculation, threshold-exit actions, zero-gain/loss semantics, and warm-up reasons for FR-012 through FR-017 in `backend/src/crypto_lab/domain/strategy/implementations/rsi.py`
- [ ] T023 [US1] Define normalized-dataset and immutable-definition application ports for FR-001 through FR-005 in `backend/src/crypto_lab/application/strategies/ports.py`
- [ ] T024 [US1] Implement the common analyze-strategy use case with pre-validation, exact version selection, and zero partial output for FR-001, FR-004, FR-007, FR-008, and FR-022 through FR-024 in `backend/src/crypto_lab/application/strategies/analyze_strategy.py`

**Checkpoint**: US1 passes independently with MA and RSI deterministic fixture output and no persistence/API dependency inside calculation.

---

## Phase 4: User Story 2 - Inspect Strategy Signals (Priority: P2)

**Goal**: Expose provenance-rich ordered BUY/SELL/HOLD signals to analysts and TV4 through one strategy-neutral result contract.

**Independent Test**: Serialize fixture Signals, combine equal-timestamp results, call bounded analysis, and verify exact provenance, ordering, phase, optional fields, and categorized invalid-context responses.

### Tests for User Story 2

- [ ] T025 [P] [US2] Add TV4 domain-contract tests for result provenance, equal-timestamp ordering, warm-up state, and generic consumption covering FR-018, FR-019, FR-020, FR-021, FR-022, FR-023, FR-024, SC-002, and SC-010 in `backend/tests/contract/test_tv4_strategy_contract.py`
- [ ] T026 [P] [US2] Add OpenAPI/Pydantic schema parity and error-envelope tests for FR-018, FR-019, FR-022, FR-037, FR-038, and SC-002 in `backend/tests/contract/test_strategy_api.py`
- [ ] T027 [P] [US2] Add bounded analysis integration tests with normalized-dataset fixtures and all invalid-context categories for FR-002 through FR-008 in `backend/tests/integration/test_strategy_analysis_api.py`

### Implementation for User Story 2

- [ ] T028 [P] [US2] Implement request, strategy metadata, provenance, Signal, result, and error boundary schemas from `contracts/openapi.yaml` in `backend/src/crypto_lab/api/schemas/strategy.py`
- [ ] T029 [US2] Implement the strategy-analysis route and domain-error mapping for FR-004, FR-018 through FR-024, FR-037, and FR-038 in `backend/src/crypto_lab/api/routes/strategies.py`
- [ ] T030 [US2] Wire dataset and definition repositories into the analysis use case without leaking I/O into Strategy for FR-001 and FR-005 in `backend/src/crypto_lab/api/dependencies.py`
- [ ] T031 [US2] Add structured analysis logs with request ID, strategy ID/version, definition ID, dataset ID/version, and outcome while excluding Candle/parameter payloads in `backend/src/crypto_lab/application/strategies/analyze_strategy.py`

**Checkpoint**: US2 passes independently against constructed Signal fixtures and, when combined with US1, exposes MA/RSI results through the same contract.

---

## Phase 5: User Story 3 - Register and Discover Strategies (Priority: P3)

**Goal**: Register trusted compatible strategy versions atomically and discover MA, RSI, and a generic compliant strategy without hard-coded downstream lists.

**Independent Test**: Register valid and invalid entries, inspect deterministic discovery metadata, and prove a generic strategy works without edits to Backtester, Evaluator, or Leaderboard.

### Tests for User Story 3

- [ ] T032 [P] [US3] Add registry tests for valid, duplicate, invalid-metadata, invalid-schema, incompatible, and atomic-failure cases covering FR-025, FR-026, FR-027, FR-028, FR-029, and SC-007 in `backend/tests/unit/strategy/test_registry.py`
- [ ] T033 [P] [US3] Add discovery API contract tests for MA/RSI metadata, filters, deterministic order, and exact-version resolution covering FR-025 and FR-026 in `backend/tests/contract/test_strategy_discovery_api.py`
- [ ] T034 [P] [US3] Add a generic compliant test strategy and downstream no-concrete-name fitness test covering FR-024, FR-030, SC-006, and SC-010 in `backend/tests/contract/test_strategy_extensibility.py`

### Implementation for User Story 3

- [ ] T035 [US3] Implement atomic compatibility-aware Strategy Registry registration and exact resolution for FR-025 through FR-029 in `backend/src/crypto_lab/domain/strategy/registry.py`
- [ ] T036 [US3] Register trusted MA and RSI entries deterministically during application composition for FR-026 and FR-030 in `backend/src/crypto_lab/bootstrap/strategies.py`
- [ ] T037 [US3] Implement strategy discovery, lifecycle filtering, and exact-version metadata resolution for FR-025 and FR-026 in `backend/src/crypto_lab/application/strategies/discover_strategies.py`
- [ ] T038 [US3] Add discovery and exact-version route handlers from `contracts/openapi.yaml` for FR-025 and FR-026 in `backend/src/crypto_lab/api/routes/strategies.py`
- [ ] T039 [US3] Add application-composition registration/discovery logs with strategy ID/version, contract version, status, and categorized failure while preserving the pure registry domain in `backend/src/crypto_lab/bootstrap/strategies.py`

**Checkpoint**: US3 passes independently with constructed compliant strategies; MA/RSI become discoverable when US1 registration is present.

---

## Phase 6: User Story 4 - Preserve Immutable Strategy Versions (Priority: P4)

**Goal**: Persist and resolve exact immutable definitions while distinguishing unknown, unavailable, deprecated, and incompatible versions without fallback.

**Independent Test**: Create identical and changed definitions concurrently, resolve historical content after a new version exists, and request every lifecycle/error state.

### Tests for User Story 4

- [ ] T040 [P] [US4] Add empty-database upgrade/downgrade and unique/immutable constraint tests for FR-031 through FR-034 in `backend/tests/integration/test_strategy_definition_migration.py`
- [ ] T041 [P] [US4] Add real-PostgreSQL repository tests for idempotent identical content, concurrent duplicates, changed parameters, and exact historical lookup covering FR-031, FR-032, FR-033, FR-034, and SC-008 in `backend/tests/integration/test_strategy_definition_repository.py`
- [ ] T042 [P] [US4] Add unknown, unavailable, deprecated-metadata, deprecated-execution, incompatible, and no-fallback contract tests covering FR-034, FR-035, FR-036, and SC-009 in `backend/tests/contract/test_strategy_version_resolution.py`

### Implementation for User Story 4

- [X] T043 [US4] Add the append-only `strategy_definitions` table, unique content fingerprint, and exact-version index for FR-031 through FR-034 in `backend/migrations/versions/20260813_003_create_strategy_definitions.py`
- [X] T044 [US4] Implement the immutable SQLAlchemy Strategy Definition persistence mapping for FR-031 through FR-034 in `backend/src/crypto_lab/infrastructure/persistence/strategy_models.py`
- [ ] T045 [US4] Implement create-or-resolve, exact lookup, and conflict-safe repository operations for FR-031 through FR-034 in `backend/src/crypto_lab/infrastructure/persistence/repositories/strategy_definition_repository.py`
- [ ] T046 [US4] Enforce deprecated/unavailable/incompatible execution states and historical metadata resolution for FR-034 through FR-036 in `backend/src/crypto_lab/application/strategies/analyze_strategy.py`
- [ ] T047 [US4] Map exact version-state failures to 404/409 categorized API responses from `contracts/openapi.yaml` for FR-035 through FR-038 in `backend/src/crypto_lab/api/routes/strategies.py`

**Checkpoint**: US4 passes independently using registry/definition fixtures and real PostgreSQL; historical content never changes or falls back.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Close contract sync, performance, security, architecture, and acceptance gates across all stories.

- [ ] T048 [P] Add canonical JSON snapshots proving `contracts/openapi.yaml` matches boundary schemas in `backend/tests/contract/test_strategy_openapi_sync.py`
- [ ] T049 [P] Add TV3↔TV4 shared fixture for MA, RSI, and the generic strategy in `backend/tests/fixtures/strategy/tv4_contract.json`
- [ ] T050 [P] Add the 10,000-Candle linear-time deterministic benchmark and strategy-discovery p95 benchmark with documented environment fields in `backend/tests/performance/test_strategy_benchmark.py`
- [ ] T051 [P] Add architecture fitness tests that forbid database, HTTP, queue, provider, clock, and randomness imports from strategy calculation modules in `backend/tests/contract/test_strategy_architecture.py`
- [ ] T052 Review API/resource bounds, log redaction, no-code-upload behavior, and analytical-only wording in `backend/tests/contract/test_strategy_security_boundary.py`
- [ ] T053 Execute every scenario in `specs/003-strategy-foundation/quickstart.md` and record commands/results in the feature pull-request evidence
- [ ] T054 Conduct the SC-011/SC-012 provenance and metadata comprehension assessment with representative analysts/developers and record participant count, tasks, outcomes, and pass rate in `specs/003-strategy-foundation/evidence/usability-validation.md`
- [ ] T055 Run Ruff, mypy, migration tests, unit/contract/integration suites, benchmark, and `$speckit-analyze` against `backend/` and `specs/003-strategy-foundation/`; resolve every CRITICAL/HIGH finding before implementation is considered ready

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 — Setup**: no dependencies.
- **Phase 2 — Foundational**: depends on Phase 1 and blocks all user stories.
- **Phase 3 — US1**: depends on Phase 2; delivers the MVP calculations.
- **Phase 4 — US2**: depends on Phase 2 for Signal/result values; its contract tests can use constructed fixtures before US1 completes, while integrated MA/RSI analysis also uses US1.
- **Phase 5 — US3**: depends on Phase 2; registry behavior is independently testable with constructed strategies, while built-in discovery uses US1 implementations.
- **Phase 6 — US4**: depends on Phase 2 and registry lifecycle semantics from US3 for full execution-state integration; persistence tests are independently runnable.
- **Phase 7 — Polish**: depends on every story selected for delivery.

### User Story Dependency Graph

```text
Setup -> Foundational
Foundational -> US1
Foundational -> US2
Foundational -> US3 -> US4
US1 -> integrated US2 analysis
US1 -> MA/RSI registration in US3
US1 + US2 + US3 + US4 -> Polish
```

### Within Each User Story

- Fixture and contract tests precede behavior implementation.
- Domain values precede application use cases; application use cases precede API routes.
- Migration precedes persistence model/repository integration.
- A story reaches its checkpoint only after its independent test passes.

### Parallel Opportunities

- T002–T004 can run in parallel after T001 establishes the package decision.
- T005–T008 target separate foundational test files and can run in parallel.
- T015–T019, T025–T027, T032–T034, and T040–T042 are parallel test-authoring groups within their stories.
- US1, contract-only US2 work, and registry-core US3 work can begin in parallel after Phase 2.
- T048–T051 can run in parallel after the relevant story implementations stabilize.

## Parallel Examples

### User Story 1

```text
T016: Strategy Context invalid/edge fixtures
T017: MA acceptance fixtures
T018: RSI acceptance fixtures
T019: deterministic/no-look-ahead contract fixtures
```

### User Story 3

```text
T032: registry atomicity tests
T033: discovery API contract tests
T034: generic-strategy extensibility fitness test
```

### User Story 4

```text
T040: migration constraints
T041: real-PostgreSQL repository behavior
T042: version lifecycle/error contract
```

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational phases.
2. Complete US1 only.
3. Run MA/RSI fixture suites and demonstrate deterministic ordered Signals without API or persistence.
4. Stop for TV3 review before adding delivery and registry/version integration.

### Incremental Delivery

1. **US1**: deterministic MA/RSI Strategy behavior.
2. **US2**: provenance-rich common output consumable by TV4 and analysts.
3. **US3**: atomic trusted registration and metadata-driven discovery.
4. **US4**: durable immutable definitions and lifecycle-safe exact resolution.
5. **Polish**: sync contracts, prove boundaries, benchmark, and run all quality gates.

### Review Gates

- TV1 confirms normalized Candle/dataset identity before T020/T023 integration.
- TV4 signs off `contracts/strategy-domain-contract.md` and shared fixture before T049 is complete.
- The team reviews the Proposed architecture and ADRs before implementation approval.
- Do not run `$speckit-implement` as part of this documentation workflow.

## Notes

- `[P]` means different files and no incomplete same-phase dependency.
- Tests are intentionally present because deterministic fixtures and contract fitness are normative requirements.
- Tasks never implement Bollinger Bands, Support/Resistance, full MACD, Composite Strategy, Backtest, Evaluation, Leaderboard, or live trading.
- Commit after each task or small logical group; do not commit `.specify/feature.json`.
