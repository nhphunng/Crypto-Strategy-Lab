# Tasks: Historical Market Data

**Input**: Design documents in `specs/001-historical-market-data/`  
**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`  
**Tests**: Required by NFR-006, SC-008, Constitution QA/DOD rules, and the user's explicit review/risk-remediation request. Tests precede corresponding implementation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: May proceed in parallel because it touches different files and has no dependency on an incomplete task in the same phase.
- **[Story]**: Maps to local user stories US1–US4 in `spec.md`.
- Every task includes exact paths and traceability-relevant scope.

## Phase 1: Setup

**Purpose**: Establish one clean Python 3.12 backend skeleton and reproducible local environment shared by later feature branches.

- [x] T001 Create the Python 3.12 package, exact dependency/tool configuration, pytest markers, Ruff rules, and mypy rules in `backend/pyproject.toml`
- [x] T002 [P] Create package/module initializers for the planned domain, application, infrastructure, and API tree under `backend/src/crypto_lab/` and tests under `backend/tests/`
- [x] T003 [P] Add PostgreSQL/API local orchestration and non-root container build in `docker-compose.yml` and `Dockerfile`
- [x] T004 [P] Document safe environment configuration without secrets in `.env.example`
- [x] T005 Verify and extend Python, Docker, coverage, environment, IDE, and Spec Kit runtime exclusions in `.gitignore` and `.dockerignore`

**Checkpoint**: The backend imports in a Python 3.12 environment and local PostgreSQL can be started without application schema mutation.

---

## Phase 2: Foundational Boundaries

**Purpose**: Add cross-story boundary infrastructure while keeping domain/application framework-independent.

**⚠️ CRITICAL**: No user story implementation starts until this phase is complete.

- [x] T006 [P] Define typed market-data application error categories and safe metadata in `backend/src/crypto_lab/application/market_data/errors.py`
- [x] T007 [P] Define provider, repository, clock, dataset-claim, and page protocols in `backend/src/crypto_lab/application/market_data/ports.py`
- [x] T008 [P] Implement validated environment settings and provider capability registry in `backend/src/crypto_lab/infrastructure/settings.py`
- [x] T009 [P] Configure async SQLAlchemy engine/session and explicit readiness probe without `create_all` in `backend/src/crypto_lab/infrastructure/database.py`
- [x] T010 [P] Add UTC millisecond, decimal-string, response-envelope, error-envelope, and cursor helpers in `backend/src/crypto_lab/api/common.py`
- [x] T011 [P] Add request-ID middleware and sanitized structured JSON logging in `backend/src/crypto_lab/api/middleware.py` and `backend/src/crypto_lab/infrastructure/logging.py`
- [x] T012 Add FastAPI exception/status mapping for every OpenAPI error code in `backend/src/crypto_lab/api/errors.py`
- [x] T013 [P] Create deterministic clock, provider, and in-memory repository test doubles in `backend/tests/fixtures/market_data.py`

**Checkpoint**: Ports and API infrastructure compile without importing provider/ORM/framework types into domain/application contracts.

---

## Phase 3: User Story 1 — Obtain Normalized Historical Candles (Priority: P1) 🎯 MVP

**Goal**: A bounded aligned closed range is validated, served locally when complete, otherwise filled from Binance through a normalized adapter and returned honestly.

**Independent Test**: Request an absent deterministic fixture range, assert exact normalized chronological Candles and `COMPLETE`, repeat it, and assert provider call count does not increase.

### Tests for User Story 1

- [x] T014 [P] [US1] Write failing timeframe alignment, Candle identity/OHLCV/decimal/close-time, expected-open, missing-range, and checksum unit tests in `backend/tests/unit/market_data/test_domain.py`
- [x] T015 [P] [US1] Write failing Binance mapping, exact-decimal, pagination, overlap/repeat termination, range filtering, timeout, throttle, retry-hint, and invalid-payload tests in `backend/tests/contract/test_binance_provider.py`
- [x] T016 [P] [US1] Write failing cache-hit, fetch-only-gap, ordering/deduplication, partial/empty, future/limit, and conflict application tests in `backend/tests/contract/test_historical_service.py`
- [x] T017 [P] [US1] Write failing dimensions/range envelope, camelCase, error/status, request-ID, and before-provider validation API tests in `backend/tests/contract/test_market_data_api.py`
- [x] T018 [P] [US1] Write failing real-PostgreSQL NUMERIC/UTC/identity/index, identical duplicate, conflicting duplicate, and chronological range tests in `backend/tests/integration/test_market_data_repository.py`

### Implementation for User Story 1

- [x] T019 [P] [US1] Implement canonical timeframe duration/alignment/floor behavior in `backend/src/crypto_lab/domain/market_data/timeframe.py`
- [x] T020 [P] [US1] Implement UTC half-open range, expected-open, gap coalescing, and range completeness behavior in `backend/src/crypto_lab/domain/market_data/ranges.py`
- [x] T021 [US1] Implement immutable Candle validation, canonical decimal/time serialization, content hash, and identity in `backend/src/crypto_lab/domain/market_data/candle.py`
- [x] T022 [P] [US1] Implement Binance Kline DTO mapping, bounded pagination, monotonic cursor, retry, timeout, and safe failure translation in `backend/src/crypto_lab/infrastructure/binance/market_data_provider.py`
- [x] T023 [US1] Implement SQLAlchemy Candle mappings and constraints in `backend/src/crypto_lab/infrastructure/persistence/models.py`
- [x] T024 [US1] Create the immutable initial PostgreSQL schema, constraints, and range indexes in `backend/migrations/versions/0001_historical_market_data.py`, `backend/migrations/env.py`, and `backend/alembic.ini`
- [x] T025 [US1] Implement local range reads and immutable/idempotent closed-Candle inserts in `backend/src/crypto_lab/infrastructure/persistence/market_data_repository.py`
- [x] T026 [US1] Implement read-local-first/fetch-only-gap historical orchestration and completeness derivation in `backend/src/crypto_lab/application/market_data/historical_service.py`
- [x] T027 [P] [US1] Implement contract-aligned Pydantic market-data request/response schemas and explicit mappers in `backend/src/crypto_lab/api/schemas/market_data.py`
- [x] T028 [US1] Wire provider/repository/service dependencies and versioned dimensions/range routes in `backend/src/crypto_lab/api/dependencies.py`, `backend/src/crypto_lab/api/routes/market_data.py`, and `backend/src/crypto_lab/main.py`
- [x] T029 [US1] Run US1 unit, provider, application, API, and PostgreSQL tests; record the independently demonstrable checkpoint in `specs/001-historical-market-data/quickstart.md`

**Checkpoint**: US1 satisfies `MD-US-01` for backend history and can be demoed without chart/realtime code.

---

## Phase 4: User Story 2 — Reuse an Immutable Dataset (Priority: P1)

**Goal**: Complete closed coverage becomes one idempotent immutable dataset with durable ordered membership/checksum and provider-free paginated reads.

**Independent Test**: Materialize an identical range twice and concurrently, resolve/page it, and assert one ID, one provider acquisition, stable content/count/checksum, and fail-closed integrity behavior.

### Tests for User Story 2

- [x] T030 [P] [US2] Write failing request-key, dataset lifecycle, canonical ordered checksum, and terminal-complete unit tests in `backend/tests/unit/market_data/test_dataset.py`
- [x] T031 [P] [US2] Write failing build claim/reuse/concurrent-building/expired-lease/incomplete/finalization application tests in `backend/tests/contract/test_dataset_service.py`
- [x] T032 [P] [US2] Write failing real-PostgreSQL dataset uniqueness/claim/token/lease/finalization/membership/cursor/integrity tests in `backend/tests/integration/test_dataset_repository.py`
- [x] T033 [P] [US2] Extend API contract tests for materialize `200/201/202`, metadata, complete-only membership pages, cursor validation, not-found, and integrity errors in `backend/tests/contract/test_market_data_api.py`

### Implementation for User Story 2

- [x] T034 [P] [US2] Implement immutable CandleDataset, DatasetStatus, build claim/result, request key, and checksum behavior in `backend/src/crypto_lab/domain/market_data/dataset.py`
- [x] T035 [US2] Extend SQLAlchemy dataset/member mappings and repository with atomic claim lease, token-checked finalization, immutable metadata, integrity validation, and cursor pages in `backend/src/crypto_lab/infrastructure/persistence/models.py` and `backend/src/crypto_lab/infrastructure/persistence/market_data_repository.py`
- [x] T036 [US2] Implement materialize/reuse/fail/poll/resolve/page use cases in `backend/src/crypto_lab/application/market_data/dataset_service.py`
- [x] T037 [US2] Extend DTOs, dependencies, routes, and OpenAPI-conformant status behavior for dataset resources in `backend/src/crypto_lab/api/schemas/market_data.py`, `backend/src/crypto_lab/api/dependencies.py`, and `backend/src/crypto_lab/api/routes/market_data.py`
- [x] T038 [US2] Run US2 unit/application/API/PostgreSQL tests and execute the immutable dataset quickstart through provider-disabled reads in `specs/001-historical-market-data/quickstart.md`

**Checkpoint**: US2 gives TV3/TV4 a complete immutable `datasetId` contract and never refetches when resolving it.

---

## Phase 5: User Story 3 — Backfill an Explicit Closed-Candle Gap (Priority: P2)

**Goal**: TV2 can use the same range service to restore a precise missing closed interval and cannot interpret missing history as live continuity.

**Independent Test**: Remove one stored interval, request its exact range, and assert only that gap is fetched; a provider-empty fixture returns the exact `PARTIAL/EMPTY` missing range.

### Tests and Integration for User Story 3

- [x] T039 [P] [US3] Add failing explicit one-gap, adjacent-gap coalescing, covered-neighbor preservation, and provider-empty recovery tests in `backend/tests/contract/test_historical_service.py`
- [x] T040 [P] [US3] Add a shared TV1/TV2/TV3 compatibility fixture asserting Candle `openTime` identity, Signal timestamp mapping, fields, millisecond UTC, timeframe enum, `[start,end)`, 1,000 limit, completeness, and missing ranges in `backend/tests/contract/test_market_data_consumer_compatibility.py`
- [x] T041 [US3] Align the Feature 002 shared history contract references to Feature 001 as owner without changing TV2 realtime behavior in `specs/002-realtime-multi-chart/data-model.md` and `specs/002-realtime-multi-chart/contracts/openapi.yaml`
- [x] T042 [US3] Run the gap/compatibility suite and document TV2's bootstrap/reconnect plus TV3/TV4 immutable-dataset consumption and timestamp mapping in `specs/001-historical-market-data/contracts/consumer-boundaries.md`

**Checkpoint**: US3 supplies data recovery; TV2 remains owner of reconnect attempts, `STALE/RECONNECTING/LIVE`, WebSocket events, and chart merge generations.

---

## Phase 6: User Story 4 — Replace a Provider Without Changing Consumers (Priority: P3)

**Goal**: One provider protocol and fitness suite proves another adapter can replace Binance without domain/application/API consumer edits.

**Independent Test**: Run equal canonical fixtures through fake and Binance adapters, then enforce import boundaries and registry-only selection.

### Tests and Implementation for User Story 4

- [x] T043 [P] [US4] Add provider fitness tests shared by deterministic fake and Binance adapters in `backend/tests/contract/test_provider_fitness.py`
- [x] T044 [P] [US4] Add architecture/import tests forbidding FastAPI/SQLAlchemy/httpx/provider imports from domain/application and raw Binance fields outside infrastructure in `backend/tests/architecture/test_boundaries.py`
- [x] T045 [US4] Refine provider registry/composition so adding a provider is adapter plus registration only in `backend/src/crypto_lab/infrastructure/settings.py` and `backend/src/crypto_lab/api/dependencies.py`
- [x] T046 [US4] Run provider fitness and architecture gates and record the replaceability evidence in `specs/001-historical-market-data/research.md`

**Checkpoint**: US4 proves the assignment's Market Data Provider change scenario without consumer branches.

---

## Phase 7: Polish, Risk Remediation, and Delivery Gates

**Purpose**: Validate migrations, performance, security, documentation, all requirements, and clean-code quality after all stories.

- [x] T047 [P] Add migration empty-upgrade/downgrade/upgrade and schema-constraint validation in `backend/tests/integration/test_migrations.py`
- [x] T048 [P] Add documented 500-Candle local-read p95 and deterministic 10,000-Candle acquisition benchmarks in `backend/tests/performance/test_historical_market_data.py`
- [x] T049 [P] Add health readiness/liveness, redaction, arbitrary-upstream rejection, bounded cursor/range, and no-secret API tests in `backend/tests/contract/test_operational_safety.py`
- [x] T050 Add migration/version readiness, structured logs, safe shutdown of shared HTTP/database resources, and non-root container health behavior in `backend/src/crypto_lab/main.py`, `Dockerfile`, and `docker-compose.yml`
- [x] T051 Validate `contracts/openapi.yaml` syntax and exact alignment with runtime OpenAPI/DTO examples in `backend/tests/contract/test_openapi_document.py`
- [x] T052 Run Ruff, mypy, all non-performance tests, PostgreSQL integration/migration tests, performance gates, Docker build, and the complete quickstart; fix every failure in affected `backend/` files
- [x] T053 Review delivered code for timestamp, precision, partial-completeness, conflict, concurrency, retry, resource exhaustion, SSRF/log leakage, migration, and dependency-direction risks; record evidence and remediate every high/critical item in `specs/001-historical-market-data/risk-review.md`
- [x] T054 Reconcile Feature 001 artifacts and cross-feature contract references, mark all delivered tasks complete, run `$speckit-converge` until no tasks are appended, and create the final decision/trade-off report in `docs/historical-market-data-decisions.html`

**Final Checkpoint**: All tasks are `[X]`; analyze has no CRITICAL/HIGH issue; tests/lint/type/migrations/build/quickstart pass; risk review has no unresolved high/critical item; converge reports `Converged`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** starts immediately.
- **Foundational (Phase 2)** depends on Setup and blocks all stories.
- **US1 (Phase 3)** implements the historical primitive used by US2/US3 and is the backend MVP.
- **US2 (Phase 4)** depends on US1 canonical storage/range behavior.
- **US3 (Phase 5)** depends on US1 but is independent of US2 dataset materialization.
- **US4 (Phase 6)** depends on the stable US1 provider port; its tests can start once Phase 2 is complete.
- **Polish (Phase 7)** depends on every selected story.

### Story Dependency Graph

```text
Setup → Foundation → US1 Historical Range ──→ US2 Immutable Dataset ──┐
                              ├──────────────→ US3 Gap Backfill ──────┤
                              └──────────────→ US4 Provider Fitness ──┤
                                                                    v
                                                              Polish/Converge
```

### Within Each Story

1. Write the listed tests and observe the relevant failure.
2. Implement domain models before services.
3. Implement infrastructure adapters/repositories before composition.
4. Implement application orchestration before API routes.
5. Run the independent story checkpoint before moving on.

### Parallel Opportunities

- T002–T004 can run after T001 establishes package decisions.
- T006–T011 and T013 touch separate foundation files.
- T014–T018 are independent failing test files.
- T019–T020 and T022/T027 touch independent implementation files after their tests exist.
- T030–T033 are independent US2 failing test surfaces.
- T039–T040 and T043–T044 are independent compatibility/fitness tests.
- T047–T049 can be developed in parallel after stories complete.

## Parallel Example: User Story 1

```text
T014 domain invariants/tests
T015 Binance provider contract tests
T016 historical application contract tests
T017 public API contract tests
T018 PostgreSQL repository integration tests
```

After those tests are reviewed, T019/T020/T022/T027 can proceed in separate files before T021/T023–T028 integrate them.

## Implementation Strategy

### MVP First

1. Complete Setup and Foundation.
2. Complete US1 with all five test layers.
3. Demonstrate normalized first fetch plus provider-free repeat.
4. Add immutable dataset US2 before downstream strategy/backtest integration.

### Incremental Delivery

1. **US1**: trusted bounded history and local reuse.
2. **US2**: reproducible immutable dataset identity.
3. **US3**: explicit TV2 closed-gap compatibility.
4. **US4**: provider replaceability proof.
5. **Polish**: migrations, performance, security, risk remediation, convergence, HTML decision record.

## Task Coverage Summary

| Story/phase | Task count | Independent criterion |
|---|---:|---|
| Setup | 5 | Backend imports and PostgreSQL starts cleanly |
| Foundation | 8 | Stable ports/config/error/API infrastructure compiles |
| US1 | 16 | First normalized range then provider-free repeat |
| US2 | 9 | Stable complete dataset ID/checksum/pages under repeat/concurrency |
| US3 | 4 | Exact gap-only fetch and honest missing range |
| US4 | 4 | Fake/Binance provider fitness plus import isolation |
| Polish | 8 | All gates, risk remediation, convergence, and report |
| **Total** | **54** | All Feature 001 requirements and user-requested final review |

All 54 tasks follow the required checkbox/ID/story/path format. Suggested MVP scope is Setup + Foundation + US1; the user's requested “complete TV1” scope requires every phase.
