---

description: "Dependency-ordered implementation tasks for Strategy Foundation"
---

# Tasks: Strategy Foundation

**Input**: Design documents from `/specs/003-strategy-foundation/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Required. The specification mandates deterministic acceptance fixtures, and the constitution requires domain/contract tests before implementation.

**Organization**: Tasks are grouped by the seven independently testable user stories in `spec.md`. US5–US7 map to canonical SRS `SP-US-04`–`SP-US-06`; FR-039–FR-060 map to `SP-FR-06`–`SP-FR-20`. Requirement IDs in each task provide direct traceability.

**Implementation Gate**: PASS as of 2026-08-23. SRS 0.2, Accepted ADR-006, updated Architecture and Approved `docs/GENERATED_STRATEGY_SECURITY_POLICY.md` are binding inputs for T048 and later.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: May run in parallel because it targets a different file and has no dependency on another incomplete task in the same phase.
- **[Story]**: Maps to `US1` through `US7` in `spec.md`.
- Every task names an exact repository path.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the approved Python backend package and quality gates without implementing strategy behavior.

- [X] T001 Create the Python 3.12 backend package, dependency groups, and locked tool configuration in `backend/pyproject.toml`
- [X] T002 [P] Create the `crypto_lab` package roots and strategy module exports in `backend/src/crypto_lab/__init__.py` and `backend/src/crypto_lab/domain/strategy/__init__.py`
- [X] T003 [P] Configure shared pytest markers, Decimal comparison policy, and deterministic-test defaults in `backend/tests/conftest.py`
- [X] T004 [P] Add backend Ruff, mypy, migration, and pytest quality gates in `.github/workflows/backend.yml`

**Checkpoint**: Backend imports, static checks, and an empty pytest suite run from a clean environment.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement the contract-neutral immutable values required by every user story.

**⚠️ CRITICAL**: No user-story implementation begins until this phase passes its tests.

- [X] T005 [P] Write contract-version compatibility tests for FR-025, FR-027, and FR-035 in `backend/tests/unit/strategy/test_contract_version.py`
- [X] T006 [P] Write parameter-definition/default/canonicalization tests for FR-004, FR-017, FR-031, and SC-003 in `backend/tests/unit/strategy/test_parameters.py`
- [X] T007 [P] Write immutable Signal identity, action, phase, and ordering tests for FR-018, FR-019, FR-020, and FR-021 in `backend/tests/unit/strategy/test_signal.py`
- [X] T008 [P] Write categorized all-or-nothing error tests for FR-037 and FR-038 in `backend/tests/unit/strategy/test_errors.py`
- [X] T009 Implement semantic version parsing and supported-major/minor-range rules for FR-025, FR-027, and FR-035 in `backend/src/crypto_lab/domain/strategy/version.py`
- [X] T010 Implement immutable parameter definitions, relationship validation, defaults, canonical values, and fingerprints for FR-004, FR-017, and FR-031 in `backend/src/crypto_lab/domain/strategy/parameters.py`
- [X] T011 [P] Implement categorized Strategy errors and structured issues for FR-037 and FR-038 in `backend/src/crypto_lab/domain/strategy/errors.py`
- [X] T012 Implement immutable Strategy Definition values and deterministic content fingerprints for FR-031, FR-032, and FR-033 in `backend/src/crypto_lab/domain/strategy/definition.py`
- [X] T013 Implement immutable Signal and Strategy Analysis Result values with deterministic identity and ordering for FR-018, FR-019, FR-020, FR-021, FR-022, and FR-023 in `backend/src/crypto_lab/domain/strategy/signal.py`
- [X] T014 Define the common Strategy protocol and capability metadata for FR-001, FR-005, FR-024, and FR-030 in `backend/src/crypto_lab/domain/strategy/protocol.py`

**Checkpoint**: Version, parameter, definition, error, and Signal values are immutable, deterministic, and framework-independent.

---

## Phase 3: User Story 1 - Run MA and RSI Strategies (Priority: P1) 🎯 MVP

**Goal**: Run deterministic MA and RSI calculations against validated normalized contexts with explicit parameter, boundary, look-ahead, and warm-up behavior.

**Independent Test**: Execute fixed MA/RSI fixtures for normal, strict crossing, equality, warm-up, empty, invalid parameter/context, and insufficient-history cases; repeat each fixture and compare the entire ordered result.

### Tests for User Story 1

> Write these tests first and observe the intended failures before implementation.

- [X] T015 [P] [US1] Create immutable normalized Candle, dataset, MA, and RSI fixture builders for FR-002, FR-003, and FR-007 in `backend/tests/fixtures/strategy/factories.py`
- [X] T016 [P] [US1] Add Strategy Context validation tests for empty, unsorted, duplicate, incomplete, invalid-OHLCV, open, future, and misaligned input covering FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, and SC-004 in `backend/tests/unit/strategy/test_context.py`
- [X] T017 [P] [US1] Add MA default/range, arithmetic-mean, crossing, equality, warm-up, empty, insufficient-history, and repeatability fixtures covering FR-009, FR-010, FR-011, SC-003, and SC-005 in `backend/tests/unit/strategy/test_moving_average.py`
- [X] T018 [P] [US1] Add RSI default/range/relationship, Wilder, threshold-exit, equality, constant, one-directional, warm-up, and repeatability fixtures covering FR-012, FR-013, FR-014, FR-015, FR-016, SC-003, and SC-005 in `backend/tests/unit/strategy/test_rsi.py`
- [X] T019 [P] [US1] Add no-look-ahead and ten-run byte-equivalent canonical result tests for FR-006, FR-007, and SC-001 in `backend/tests/contract/test_strategy_contract.py`

### Implementation for User Story 1

- [X] T020 [US1] Implement immutable Strategy Context construction, strict validation, and deterministic fingerprinting for FR-002 through FR-008 in `backend/src/crypto_lab/domain/strategy/context.py`
- [X] T021 [US1] Implement MA metadata, parameter validation, Decimal rolling mean, crossing actions, and warm-up reasons for FR-009 through FR-011 and FR-017 in `backend/src/crypto_lab/domain/strategy/implementations/moving_average.py`
- [X] T022 [US1] Implement RSI metadata, Wilder Decimal calculation, threshold-exit actions, zero-gain/loss semantics, and warm-up reasons for FR-012 through FR-017 in `backend/src/crypto_lab/domain/strategy/implementations/rsi.py`
- [X] T023 [US1] Define normalized-dataset and immutable-definition application ports for FR-001 through FR-005 in `backend/src/crypto_lab/application/strategies/ports.py`
- [X] T024 [US1] Implement the common analyze-strategy use case with pre-validation, exact version selection, and zero partial output for FR-001, FR-004, FR-007, FR-008, and FR-022 through FR-024 in `backend/src/crypto_lab/application/strategies/analyze_strategy.py`

**Checkpoint**: US1 passes independently with MA and RSI deterministic fixture output and no persistence/API dependency inside calculation.

---

## Phase 4: User Story 2 - Inspect Strategy Signals (Priority: P2)

**Goal**: Expose provenance-rich ordered BUY/SELL/HOLD signals to analysts and TV4 through one strategy-neutral result contract.

**Independent Test**: Serialize fixture Signals, combine equal-timestamp results, call bounded analysis, and verify exact provenance, ordering, phase, optional fields, and categorized invalid-context responses.

### Tests for User Story 2

- [X] T025 [P] [US2] Add TV4 domain-contract tests for result provenance, equal-timestamp ordering, warm-up state, and generic consumption covering FR-018, FR-019, FR-020, FR-021, FR-022, FR-023, FR-024, SC-002, and SC-010 in `backend/tests/contract/test_tv4_strategy_contract.py`
- [X] T026 [P] [US2] Add OpenAPI/Pydantic schema parity and error-envelope tests for FR-018, FR-019, FR-022, FR-037, FR-038, and SC-002 in `backend/tests/contract/test_strategy_api.py`
- [X] T027 [P] [US2] Add bounded analysis integration tests with normalized-dataset fixtures and all invalid-context categories for FR-002 through FR-008 in `backend/tests/integration/test_strategy_analysis_api.py`

### Implementation for User Story 2

- [X] T028 [P] [US2] Implement request, strategy metadata, provenance, Signal, result, and error boundary schemas from `contracts/openapi.yaml` in `backend/src/crypto_lab/api/schemas/strategy.py`
- [X] T029 [US2] Implement the strategy-analysis route and domain-error mapping for FR-004, FR-018 through FR-024, FR-037, and FR-038 in `backend/src/crypto_lab/api/routes/strategies.py`
- [X] T030 [US2] Wire dataset and definition repositories into the analysis use case without leaking I/O into Strategy for FR-001 and FR-005 in `backend/src/crypto_lab/api/dependencies.py`
- [X] T031 [US2] Add structured analysis logs with request ID, strategy ID/version, definition ID, dataset ID/version, and outcome while excluding Candle/parameter payloads in `backend/src/crypto_lab/application/strategies/analyze_strategy.py`

**Checkpoint**: US2 passes independently against constructed Signal fixtures and, when combined with US1, exposes MA/RSI results through the same contract.

---

## Phase 5: User Story 3 - Register and Discover Strategies (Priority: P3)

**Goal**: Register trusted compatible strategy versions atomically and discover MA, RSI, and a generic compliant strategy without hard-coded downstream lists.

**Independent Test**: Register valid and invalid entries, inspect deterministic discovery metadata, and prove a generic strategy works without edits to Backtester, Evaluator, or Leaderboard.

### Tests for User Story 3

- [X] T032 [P] [US3] Add registry tests for valid, duplicate, invalid-metadata, invalid-schema, incompatible, and atomic-failure cases covering FR-025, FR-026, FR-027, FR-028, FR-029, and SC-007 in `backend/tests/unit/strategy/test_registry.py`
- [X] T033 [P] [US3] Add discovery API contract tests for MA/RSI metadata, filters, deterministic order, and exact-version resolution covering FR-025 and FR-026 in `backend/tests/contract/test_strategy_discovery_api.py`
- [X] T034 [P] [US3] Add a generic compliant test strategy and downstream no-concrete-name fitness test covering FR-024, FR-030, SC-006, and SC-010 in `backend/tests/contract/test_strategy_extensibility.py`

### Implementation for User Story 3

- [X] T035 [US3] Implement atomic compatibility-aware Strategy Registry registration and exact resolution for FR-025 through FR-029 in `backend/src/crypto_lab/domain/strategy/registry.py`
- [X] T036 [US3] Register trusted MA and RSI entries deterministically during application composition for FR-026 and FR-030 in `backend/src/crypto_lab/bootstrap/strategies.py`
- [X] T037 [US3] Implement strategy discovery, lifecycle filtering, and exact-version metadata resolution for FR-025 and FR-026 in `backend/src/crypto_lab/application/strategies/discover_strategies.py`
- [X] T038 [US3] Add discovery and exact-version route handlers from `contracts/openapi.yaml` for FR-025 and FR-026 in `backend/src/crypto_lab/api/routes/strategies.py`
- [X] T039 [US3] Add application-composition registration/discovery logs with strategy ID/version, contract version, status, and categorized failure while preserving the pure registry domain in `backend/src/crypto_lab/bootstrap/strategies.py`

**Checkpoint**: US3 passes independently with constructed compliant strategies; MA/RSI become discoverable when US1 registration is present.

---

## Phase 6: User Story 4 - Preserve Immutable Strategy Versions (Priority: P4)

**Goal**: Persist and resolve exact immutable definitions while distinguishing unknown, unavailable, deprecated, and incompatible versions without fallback.

**Independent Test**: Create identical and changed definitions concurrently, resolve historical content after a new version exists, and request every lifecycle/error state.

### Tests for User Story 4

- [X] T040 [P] [US4] Add empty-database upgrade/downgrade and unique/immutable constraint tests for FR-031 through FR-034 in `backend/tests/integration/test_strategy_definition_migration.py`
- [X] T041 [P] [US4] Add real-PostgreSQL repository tests for idempotent identical content, concurrent duplicates, changed parameters, and exact historical lookup covering FR-031, FR-032, FR-033, FR-034, and SC-008 in `backend/tests/integration/test_strategy_definition_repository.py`
- [X] T042 [P] [US4] Add unknown, unavailable, deprecated-metadata, deprecated-execution, incompatible, and no-fallback contract tests covering FR-034, FR-035, FR-036, and SC-009 in `backend/tests/contract/test_strategy_version_resolution.py`

### Implementation for User Story 4

- [X] T043 [US4] Add the append-only `strategy_definitions` table, unique content fingerprint, and exact-version index for FR-031 through FR-034 in `backend/migrations/versions/20260813_003_create_strategy_definitions.py`
- [X] T044 [US4] Implement the immutable SQLAlchemy Strategy Definition persistence mapping for FR-031 through FR-034 in `backend/src/crypto_lab/infrastructure/persistence/strategy_models.py`
- [X] T045 [US4] Implement create-or-resolve, exact lookup, and conflict-safe repository operations for FR-031 through FR-034 in `backend/src/crypto_lab/infrastructure/persistence/repositories/strategy_definition_repository.py`
- [X] T046 [US4] Enforce deprecated/unavailable/incompatible execution states and historical metadata resolution for FR-034 through FR-036 in `backend/src/crypto_lab/application/strategies/analyze_strategy.py`
- [X] T047 [US4] Map exact version-state failures to 404/409 categorized API responses from `contracts/openapi.yaml` for FR-035 through FR-038 in `backend/src/crypto_lab/api/routes/strategies.py`

**Checkpoint**: US4 passes independently using registry/definition fixtures and real PostgreSQL; historical content never changes or falls back.

---

## Phase 7: User Story 5 - Generate a Strategy from an Existing Name (Priority: P2)

**Goal**: Turn a specific existing strategy name into a structured, validated, user-confirmed, reusable Strategy Version without trusting model output implicitly.

**Independent Test**: Exercise known, unknown, misspelled, ambiguous, invalid, equivalent, and valid strategy-name fixtures; only the confirmed passing draft may become available.

### Tests for User Story 5

- [X] T048 [P] [US5] Add deterministic model-response fixtures for known, unknown, misspelled, ambiguous, equivalent, and valid strategy names covering FR-039 through FR-047 and SC-013 in `backend/tests/fixtures/strategy_generation/names.py`
- [X] T049 [P] [US5] Add structured draft, rule evidence, assumption, parameter, and generation-provenance tests covering FR-041 through FR-044 and FR-052 through FR-054 in `backend/tests/unit/strategy/test_generation_draft.py`
- [X] T050 [P] [US5] Add generated artifact schema, syntax, import/capability, contract, determinism, no-look-ahead, resource, sandbox-containment, and fixture validation tests covering FR-044 through FR-046 and SC-015 in `backend/tests/contract/test_generated_strategy_validation.py` and `backend/tests/contract/test_generated_strategy_sandbox.py`
- [X] T051 [P] [US5] Add confirmation, duplicate-content, atomic activation, and analyst review UI tests covering FR-047, FR-048, FR-052, SC-016, and SC-019 in `backend/tests/contract/test_generated_strategy_activation.py` and `frontend/src/test/unit/generated-strategy-review.test.tsx`

### Implementation for User Story 5

- [X] T052 [US5] Implement immutable generation request, draft, artifact, validation report, and provenance domain values for FR-040, FR-043, FR-046, FR-052, and FR-053 in `backend/src/crypto_lab/domain/strategy/generation.py`
- [X] T053 [US5] Define model generation, artifact storage, validation runtime, and generation repository ports for FR-040 through FR-046 in `backend/src/crypto_lab/application/strategies/ports.py`
- [X] T054 [US5] Implement strategy-name intent resolution and zero-to-one draft orchestration with explicit ambiguity handling for FR-039 through FR-043 in `backend/src/crypto_lab/application/strategies/generate_strategies.py`
- [X] T055 [US5] Implement ADR-006 isolated validation/execution, the bounded one-shot runner, hardened image and deployment profiles for FR-044 through FR-046 in `backend/src/crypto_lab/infrastructure/sandbox/generated_strategy_runtime.py`, `backend/sandbox/runner.py`, `backend/sandbox/Dockerfile`, `infra/security/strategy-sandbox-seccomp.json`, `infra/security/strategy-sandbox.apparmor`, and `infra/compose.yaml`
- [X] T056 [US5] Implement review/confirmation preconditions, content-addressed duplicate resolution, and atomic activation for FR-047, FR-048, FR-052, and FR-055 in `backend/src/crypto_lab/application/strategies/activate_generated_strategy.py`
- [X] T057 [US5] Implement generation request/draft/activation API boundaries and the analyst review-confirmation UI showing exact rules, evidence, assumptions, fingerprints and Validation Report in `backend/src/crypto_lab/api/routes/strategy_generation.py`, `backend/src/crypto_lab/api/schemas/strategy_generation.py`, `frontend/src/features/strategies/types.ts`, `frontend/src/features/strategies/components/StrategyGenerationForm.tsx`, `frontend/src/features/strategies/components/GeneratedStrategyReview.tsx`, `frontend/src/services/strategyGeneration.ts`, and `frontend/src/screens/Strategies.tsx`

**Checkpoint**: US5 passes with deterministic fake-model fixtures; no live model or invalid artifact is required to prove activation safety.

---

## Phase 8: User Story 6 - Extract Strategies from Source Content (Priority: P2)

**Goal**: Convert direct text or policy-compliant webpage content into zero-to-many evidence-backed drafts that can be handled independently.

**Independent Test**: Run one-, multi-, zero-, contradictory-, inaccessible-, hostile-, and unsupported-source fixtures and verify evidence, provenance, access controls, prompt-injection resistance, and sibling isolation.

### Tests for User Story 6

- [X] T058 [P] [US6] Add immutable direct-text and webpage snapshots containing zero, one, multiple, contradictory, incomplete, irrelevant, and injected strategy content for FR-039, FR-042, FR-049, and FR-051 in `backend/tests/fixtures/strategy_generation/sources.py`
- [X] T059 [P] [US6] Add source-access and retention-policy tests for scheme, DNS/IP class, redirects, size, media type, timeout, attribution, private/local destinations, encrypted raw payloads, 30-day deletion, and permanent minimal provenance covering FR-050, FR-051, and FR-054 in `backend/tests/contract/test_strategy_source_access.py` and `backend/tests/integration/test_strategy_source_retention.py`
- [X] T060 [P] [US6] Add zero-to-many extraction, rule-evidence, assumption, contradiction, and sibling-failure isolation tests covering FR-042, FR-043, FR-046, FR-049, SC-014, and SC-016 in `backend/tests/contract/test_strategy_source_extraction.py`
- [X] T061 [P] [US6] Add malformed/refused/timeout/provider-failure and retry-idempotency tests covering FR-040, FR-046, and the generation error contract in `backend/tests/integration/test_strategy_generation_failures.py`

### Implementation for User Story 6

- [X] T062 [US6] Implement immutable source snapshot/provenance values and access-policy decisions for FR-050, FR-051, FR-053, and FR-054 in `backend/src/crypto_lab/domain/strategy/provenance.py`
- [X] T063 [US6] Implement the approved safe webpage source adapter with destination revalidation on redirects and bounded inert-content extraction for FR-050 and FR-051 in `backend/src/crypto_lab/infrastructure/sources/web_source_adapter.py`
- [X] T064 [US6] Implement the LLM provider adapter with structured output validation, prompt/template versioning, request correlation, and redacted failures for FR-042 through FR-046 and FR-053 in `backend/src/crypto_lab/infrastructure/llm/strategy_generation_adapter.py`
- [X] T065 [US6] Extend generation orchestration for zero-to-many drafts, evidence mapping, explicit assumptions, and independent sibling lifecycle handling for FR-042, FR-043, FR-046, and FR-049 in `backend/src/crypto_lab/application/strategies/generate_strategies.py`
- [X] T066 [US6] Implement durable idempotent generation persistence, envelope-encrypted raw source payloads, configured key-provider boundary, 30-day purge, and permanent minimal provenance for FR-040, FR-046, FR-052 through FR-054 in `backend/src/crypto_lab/infrastructure/persistence/repositories/strategy_generation_repository.py`, `backend/src/crypto_lab/infrastructure/security/source_content_protector.py`, and `backend/src/crypto_lab/application/strategies/purge_expired_source_content.py`
- [X] T067 [US6] Add generation lifecycle progress and source-safe error responses without exposing raw protected content in `backend/src/crypto_lab/api/routes/strategy_generation.py`

**Checkpoint**: US6 independently produces safe evidence-backed drafts; URL or model failure never creates an executable strategy or blocks valid sibling drafts.

---

## Phase 9: User Story 7 - Reuse Generated Strategies in Later Workflows (Priority: P1)

**Goal**: Persist activated generated versions and make them discoverable and executable through the exact same downstream contract as built-ins without regeneration.

**Independent Test**: Activate a valid generated draft, restart with model/source adapters disabled, discover and execute the exact version, consume it through TV4, revise it, and verify historical immutability.

### Tests for User Story 7

- [X] T068 [P] [US7] Add migration and real-PostgreSQL tests for generation requests, source metadata, drafts, artifacts, reports, provenance, and atomic activation covering FR-052 through FR-060 in `backend/tests/integration/test_strategy_generation_repository.py`
- [X] T069 [P] [US7] Add restart-safe discovery and exact artifact resolution tests with model/source adapters disabled covering FR-055, FR-057, FR-060, SC-017, and SC-018 in `backend/tests/integration/test_generated_strategy_reuse.py`
- [X] T070 [P] [US7] Add TV4 and later-workflow fitness tests proving no built-in/generated origin branch and no regeneration covering FR-056, SC-017, and `contracts/strategy-domain-contract.md` in `backend/tests/contract/test_generated_strategy_downstream.py`
- [X] T071 [P] [US7] Add immutable revision and historical provenance tests for source, rule, artifact, prompt/model, and policy changes covering FR-052, FR-053, FR-058, FR-060, and SC-018 in `backend/tests/contract/test_generated_strategy_versioning.py`

### Implementation for User Story 7

- [X] T072 [US7] Add immutable generation and artifact provenance tables/constraints using a new migration in `backend/migrations/versions/`
- [X] T073 [US7] Add persistence mappings for generation requests, source snapshots, drafts, artifacts, reports, provenance, and activation links in `backend/src/crypto_lab/infrastructure/persistence/strategy_generation_models.py`
- [X] T074 [US7] Extend Strategy Registry entries and Strategy Definitions with origin and immutable generated provenance references for FR-055 through FR-058 in `backend/src/crypto_lab/domain/strategy/registry.py` and `backend/src/crypto_lab/domain/strategy/definition.py`
- [X] T075 [US7] Implement restart-safe generated artifact loading through the approved isolation adapter without model/source calls for FR-056 and FR-060 in `backend/src/crypto_lab/infrastructure/sandbox/generated_strategy_runtime.py`
- [X] T076 [US7] Publish activated generated versions through existing discovery and analysis use cases while filtering all non-active draft states for FR-055 through FR-060 in `backend/src/crypto_lab/application/strategies/discover_strategies.py` and `backend/src/crypto_lab/application/strategies/analyze_strategy.py`
- [X] T077 [US7] Expose safe origin and generation/validation provenance summaries in discovery without protected source/prompt leakage for FR-057 in `backend/src/crypto_lab/api/schemas/strategy.py`
- [X] T078 [US7] Add the generated-version shared fixture to TV4 and document exact artifact/provenance resolution in `backend/tests/fixtures/strategy/tv4_generated_contract.json`

**Checkpoint**: US7 proves durable reuse and immutable revision semantics with no model/source dependency during later execution.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Close contract sync, performance, security, architecture, and acceptance gates across all stories.

- [X] T079 [P] Add canonical JSON snapshots proving `contracts/openapi.yaml` matches boundary schemas in `backend/tests/contract/test_strategy_openapi_sync.py`
- [X] T080 [P] Add TV3↔TV4 shared fixtures for MA, RSI, generic, and activated generated strategies in `backend/tests/fixtures/strategy/tv4_contract.json`
- [X] T081 [P] Add the 10,000-Candle execution benchmark plus generation acknowledgement/completion and strategy-discovery p95 benchmarks in `backend/tests/performance/test_strategy_benchmark.py`
- [X] T082 [P] Add architecture fitness tests that forbid ambient database, HTTP, queue, provider, clock, randomness, filesystem, process, and environment access from all strategy calculation modules in `backend/tests/contract/test_strategy_architecture.py`
- [X] T083 Add generated-code threat-model fixtures, source/prompt redaction, disclaimer, resource limits, and analytical-only security assertions in `backend/tests/contract/test_strategy_security_boundary.py`
- [ ] T084 Execute every scenario in `specs/003-strategy-foundation/quickstart.md` and record commands/results in the feature pull-request evidence
- [ ] T085 Conduct SC-011/SC-012/SC-020 provenance, metadata, and generation-review comprehension assessments and record outcomes in `specs/003-strategy-foundation/evidence/usability-validation.md`
- [ ] T086 Run Ruff, mypy, migration tests, unit/contract/integration/security suites, benchmarks, `$speckit-analyze`, and `$speckit-converge`; resolve every CRITICAL/HIGH finding before the feature is considered complete

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 — Setup**: no dependencies.
- **Phase 2 — Foundational**: depends on Phase 1 and blocks all user stories.
- **Phase 3 — US1**: depends on Phase 2; delivers the MVP calculations.
- **Phase 4 — US2**: depends on Phase 2 for Signal/result values; its contract tests can use constructed fixtures before US1 completes, while integrated MA/RSI analysis also uses US1.
- **Phase 5 — US3**: depends on Phase 2; registry behavior is independently testable with constructed strategies, while built-in discovery uses US1 implementations.
- **Phase 6 — US4**: depends on Phase 2 and registry lifecycle semantics from US3 for full execution-state integration; persistence tests are independently runnable.
- **Phase 7 — US5**: depends on Phase 2 and the approved SRS/ADR-006/security-policy baseline; activation integrates with US3/US4 registry and version semantics.
- **Phase 8 — US6**: depends on the same approved governance baseline and US5 generation values/ports; direct source-policy/extraction tests can run independently with fixtures.
- **Phase 9 — US7**: depends on US5 activation plus US3/US4 registry/version behavior; it consumes US6 provenance structures for text/URL-derived strategies.
- **Phase 10 — Polish**: depends on every story selected for delivery.

### User Story Dependency Graph

```text
Setup -> Foundational
Foundational -> US1
Foundational -> US2
Foundational -> US3 -> US4
Approved SRS + ADR-006 + security policy -> US5 -> US7
Approved SRS + ADR-006 + security policy -> US5 -> US6 -> US7
US1 -> integrated US2 analysis
US1 -> MA/RSI registration in US3
US1 + US2 + US3 + US4 + US5 + US6 + US7 -> Polish
```

### Within Each User Story

- Fixture and contract tests precede behavior implementation.
- Domain values precede application use cases; application use cases precede API routes.
- Migration precedes persistence model/repository integration.
- T050 precedes T055; T055 must produce and verify the hardened sandbox artifacts before T075 enables stored generated-version execution.
- T059 precedes the encryption/retention behavior in T066, and T051 precedes the review-confirmation UI/API implementation in T057.
- A story reaches its checkpoint only after its independent test passes.

### Parallel Opportunities

- T002–T004 can run in parallel after T001 establishes the package decision.
- T005–T008 target separate foundational test files and can run in parallel.
- T015–T019, T025–T027, T032–T034, and T040–T042 are parallel test-authoring groups within their stories.
- T048–T051, T058–T061, and T068–T071 are parallel test-authoring groups within the amendment stories after their governance gate passes.
- US1, contract-only US2 work, and registry-core US3 work can begin in parallel after Phase 2.
- T079–T082 can run in parallel after the relevant story implementations stabilize.

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

### User Story 5

```text
T048: strategy-name/model fixtures
T049: structured draft/provenance tests
T050: isolated generated-artifact validation
T051: confirmation/activation contract
```

### User Story 6

```text
T058: source fixtures
T059: URL/source-access policy
T060: zero-to-many extraction and sibling isolation
T061: provider failure and retry idempotency
```

### User Story 7

```text
T068: durable generation persistence
T069: restart-safe exact reuse
T070: downstream origin-neutral contract
T071: immutable generated revisions
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
5. **US5**: name-to-draft generation, independent validation, and confirmed activation.
6. **US6**: safe text/URL ingestion and zero-to-many evidence-backed extraction.
7. **US7**: durable catalog reuse, restart safety, immutable generated revisions, and downstream compatibility.
8. **Polish**: sync contracts, prove isolation/boundaries, benchmark, and run all quality gates.

### Review Gates

- TV1 confirms normalized Candle/dataset identity before T020/T023 integration.
- TV4 signs off `contracts/strategy-domain-contract.md` and shared fixtures before T080 is complete.
- SRS 0.2 canonical `SP-US-04..06`/`SP-FR-06..20`, Accepted ADR-006, updated Architecture and Approved security/source policy are reviewed as binding inputs before T048.
- The implementation uses the approved global trusted-workspace catalog, requester confirmation, provider-neutral LLM port and documented source/sandbox operational limits.
- Do not run `$speckit-implement` as part of this documentation workflow.

## Notes

- `[P]` means different files and no incomplete same-phase dependency.
- Tests are intentionally present because deterministic fixtures and contract fitness are normative requirements.
- Tasks never implement Bollinger Bands, Support/Resistance, full MACD, Composite Strategy, Backtest, Evaluation, Leaderboard, arbitrary user code upload, or live trading.
- Commit after each task or small logical group; do not commit `.specify/feature.json`.

---

## Phase 11: Convergence

**Purpose**: Close implementation gaps found by `$speckit-converge` before the feature can pass T086.

- [X] T087 Isolate generation candidate lifecycles so one failed validation or persistence operation does not determine sibling outcomes, persist a structured per-draft failure, and add mixed-success tests covering FR-046 and FR-049 in `backend/src/crypto_lab/application/strategies/generate_strategies.py` and `backend/tests/integration/test_strategy_generation_failures.py`
- [X] T088 Make request processing retry-idempotent by resolving existing request/candidate/artifact/report records instead of creating duplicate drafts or surfacing uniqueness errors, with retry tests covering FR-040, FR-046, and SC-019 in `backend/src/crypto_lab/application/strategies/generate_strategies.py`, `backend/src/crypto_lab/infrastructure/persistence/repositories/strategy_generation_repository.py`, and `backend/tests/integration/test_strategy_generation_repository.py`
- [X] T089 Create or resolve an immutable default Strategy Definition during generated-strategy activation and prove exact analysis/downstream execution after restart with model/source adapters disabled, covering FR-055, FR-056, FR-060, and SC-017 in `backend/src/crypto_lab/application/strategies/activate_generated_strategy.py` and `backend/tests/integration/test_generated_strategy_reuse.py`
- [X] T090 Enforce full canonical OpenAPI-to-boundary schema parity, including the common error envelope and all generated-strategy endpoints, with snapshot assertions covering FR-037, FR-038, and T079 in `backend/tests/contract/test_strategy_openapi_sync.py`, `backend/src/crypto_lab/api/errors.py`, and `specs/003-strategy-foundation/contracts/openapi.yaml`
- [X] T091 Stream webpage retrieval with hard transfer and decoded-content byte limits and bind the connection to the already-approved public destination to prevent DNS rebinding, with redirect/oversize/rebinding fixtures covering FR-050 and FR-051 in `backend/src/crypto_lab/infrastructure/sources/web_source_adapter.py` and `backend/tests/contract/test_strategy_source_access.py`
- [X] T092 Validate exact generated signal timestamps, sequence positions, provenance, deterministic repetitions, prefix no-look-ahead behavior, and actual-versus-declared imports before executability, with structured findings covering FR-043 through FR-046 and FR-059 in `backend/src/crypto_lab/infrastructure/sandbox/generated_strategy_runtime.py` and `backend/tests/contract/test_generated_strategy_validation.py`
- [X] T093 Preserve every duplicate request/draft activation link to the existing immutable artifact/version/provenance while preventing duplicate active versions, with traceability tests covering FR-052 through FR-054 and SC-019 in `backend/src/crypto_lab/application/strategies/activate_generated_strategy.py` and `backend/tests/contract/test_generated_strategy_activation.py`
- [X] T094 Return `STRATEGY_INTENT_UNRESOLVED` when strategy-name generation yields zero or multiple materially plausible candidates, while natural-language/source zero-candidate extraction completes explicitly, with tests covering FR-039 through FR-043 and SC-013 in `backend/src/crypto_lab/application/strategies/generate_strategies.py` and `backend/tests/integration/test_strategy_generation_failures.py`
- [ ] T095 Make the approved generated-code isolation profile operationally installable/configurable and run an actual image containment smoke test for non-root, networkless, read-only, capability-free, time/memory/process-limited execution, covering ADR-006, FR-044, FR-045, and SC-015 in `backend/sandbox/`, `infra/compose.yaml`, `infra/security/`, and `backend/tests/contract/test_generated_strategy_sandbox.py`

---

## Phase 12: Convergence

**Purpose**: Connect the frontend strategy builder to the canonical backend catalog and make activated generated strategies immediately reusable across later frontend sessions.

- [X] T096 Add strict frontend discovery DTOs, runtime boundary validation, mapping tests, and an asynchronous strategy catalog client for `GET /api/v1/strategies`, replacing runtime dependence on the mock strategy gateway while preserving test-only fixtures, per FR-025, FR-026, FR-055, FR-057, FE-01, and FE-08 (partial)
- [X] T097 Render built-in and generated catalog entries from backend-owned identities and parameter schemas with loading, retry, empty, and safe presentation-fallback states; remove runtime assumptions about `ma-cross-v3`, `rsi-reversal-v2`, and unsupported mock-only strategies, per FR-017, FR-025, FR-026, FE-01, and FE-06 (contradicts)
- [X] T098 Invalidate and refetch strategy discovery after successful generated-draft activation, automatically expose/select the exact activated ID and version for parameter configuration, and prove a later mount/reload rediscovers it without local-only persistence, per US7/AC1-2, FR-055, FR-056, and FR-060 (partial)
- [X] T099 Synchronize generated draft `failureIssues` and validation findings with the backend contract and add frontend integration coverage for discovery, activation-to-selection, failure feedback, and remount reuse using API fixtures, per FR-046, FR-047, DOD-05, and DOD-06 (partial)
