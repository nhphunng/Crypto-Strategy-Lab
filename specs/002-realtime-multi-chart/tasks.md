# Tasks: Realtime Multi-Chart Dashboard

**Input**: Design documents from `/specs/002-realtime-multi-chart/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`

**Tests**: Required by `NFR-007` and the Constitution. Write the listed tests first and confirm they fail before implementation.

**Organization**: Tasks are grouped by user story so each story can be implemented and demonstrated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it uses different files and has no incomplete dependency.
- **[Story]**: Maps to the numbered story in `spec.md`.
- Every task names its target file.

## Phase 1: Setup and Approval Gates

**Purpose**: Clear governance and shared-contract blockers before application code begins.

- [X] T001 Record team acceptance or replacement decisions for the baseline market architecture in `docs/ARCHITECTURE.md` and `docs/ADR/ADR-003-normalized-market-data.md`
- [X] T002 Cross-review TV1/TV2 Candle fields, decimal precision, UTC/timeframe encoding, range inclusivity, completeness, limits, versions, and errors; record the approved result in `specs/002-realtime-multi-chart/contracts/openapi.yaml` and `specs/002-realtime-multi-chart/data-model.md`
- [X] T003 [P] Create backend package/test directories and package initializers under `backend/src/crypto_lab/{domain/market_data,application/market_data,application/chart_delivery,infrastructure/market_data,api/websocket}` and `backend/tests/{unit/market_data,contract,integration}`
- [X] T004 [P] Create frontend feature/test directories under `frontend/src/features/market-chart/{api,realtime,components,hooks}` and `frontend/tests/market-chart`
- [X] T005 [P] Document provider endpoint, heartbeat, retry, history-limit, and four-slot configuration keys without secrets in `.env.example`

**Checkpoint**: Architecture/ADR and shared Candle/history contract are approved; source skeleton exists.

---

## Phase 2: Foundational Contracts and Boundaries

**Purpose**: Shared typed boundaries required by every story.

**⚠️ CRITICAL**: No user-story implementation begins until this phase passes its tests.

- [X] T006 [P] Add shared `Provider`, `Timeframe`, `MarketSelection`, `ConnectionState`, and validation rules in `backend/src/crypto_lab/domain/market_data/selection.py`
- [X] T007 [P] Implement or align the approved TV1-owned Candle value object and invariants in `backend/src/crypto_lab/domain/market_data/candle.py`
- [X] T008 Define historical repository/provider and realtime provider protocols in `backend/src/crypto_lab/application/market_data/ports.py`
- [X] T009 [P] Define versioned REST/WebSocket Pydantic boundary schemas and uppercase errors in `backend/src/crypto_lab/api/schemas/market_data.py`
- [X] T010 [P] Define matching TypeScript types and runtime schemas in `frontend/src/features/market-chart/types.ts` and `frontend/src/features/market-chart/schemas.ts`
- [X] T011 Implement connection-local slot bindings and unique-selection reference counting with a four-slot cap in `backend/src/crypto_lab/application/chart_delivery/subscription_registry.py`
- [X] T012 [P] Build a deterministic controllable realtime provider stub in `backend/tests/integration/fakes/fake_realtime_market_provider.py`
- [X] T013 [P] Add import-boundary tests preventing domain imports of FastAPI, SQLAlchemy, provider SDKs, or WebSocket clients in `backend/tests/unit/test_architecture_boundaries.py`

**Checkpoint**: Shared contracts parse consistently, domain boundaries pass, and the registry enforces slot/ref-count rules.

---

## Phase 3: User Story 1 — Receive Realtime Candles (Priority: P1) 🎯 MVP

**Goal**: One chart bootstraps bounded history and receives normalized open/closed Candle updates without polling, duplicates, or time regression.

**Independent Test**: Publish open, duplicate, out-of-order, and closed events for one selection and observe one chronological chart series update without page refresh.

### Tests for User Story 1

- [X] T014 [P] [US1] Write failing Candle identity, OHLCV, revision, open-to-closed, duplicate, conflicting-closed, and out-of-order unit tests in `backend/tests/unit/market_data/test_candle_merge.py`
- [X] T015 [P] [US1] Write failing REST and WebSocket schema/version/error contract tests in `backend/tests/contract/test_market_data_contracts.py`
- [X] T016 [P] [US1] Write failing provider-to-WebSocket integration tests with open/closed and duplicate events in `backend/tests/integration/test_realtime_market_data.py`
- [X] T017 [P] [US1] Write failing frontend event parsing, bounded merge, and late-generation rejection tests in `frontend/tests/market-chart/realtime-candles.test.ts`

### Implementation for User Story 1

- [X] T018 [US1] Implement deterministic bounded Candle merge and revision handling in `backend/src/crypto_lab/application/market_data/candle_merge.py`
- [X] T019 [P] [US1] Implement approved historical Candle query/envelope integration in `backend/src/crypto_lab/api/routes/market_data.py`
- [X] T020 [US1] Implement normalized stream orchestration and subscription acknowledgements in `backend/src/crypto_lab/application/chart_delivery/stream_candles.py`
- [X] T021 [US1] Implement provider payload validation/mapping behind the realtime port in `backend/src/crypto_lab/infrastructure/market_data/binance_realtime_provider.py`
- [X] T022 [US1] Implement `/ws/v1/market-data` command validation and typed event delivery in `backend/src/crypto_lab/api/websocket/market_data_channel.py`
- [X] T023 [P] [US1] Implement bounded historical client queries in `frontend/src/features/market-chart/api/marketDataApi.ts`
- [X] T024 [US1] Implement one validated dashboard connection, bootstrap buffering, event deduplication, and selection dispatch in `frontend/src/features/market-chart/realtime/marketDataSocket.ts`
- [X] T025 [US1] Implement incremental bounded Candle rendering and semantic latest-Candle summary in `frontend/src/features/market-chart/components/CandlestickChart.tsx`

**Checkpoint**: US1 works with one slot and satisfies `MD-US-02` independently.

---

## Phase 4: User Story 2 — View Up to Four Charts (Priority: P1)

**Goal**: Display one to four stable, responsive, accessible chart slots and reject a fifth.

**Independent Test**: Render each allowed chart count, attempt a fifth slot, and operate all controls by keyboard at wide and narrow viewports.

### Tests for User Story 2

- [X] T026 [P] [US2] Write failing component tests for one-to-four counts, fifth-slot rejection, stable IDs, non-color status, keyboard controls, and narrow layout in `frontend/tests/market-chart/chart-grid.test.tsx`
- [X] T027 [P] [US2] Write a failing one-to-four chart Playwright scenario in `tests/e2e/realtime-multi-chart.spec.ts`
- [X] T028 [P] [US2] Write failing server slot-limit and equal-selection reference-count tests in `backend/tests/unit/market_data/test_subscription_registry.py`

### Implementation for User Story 2

- [X] T029 [US2] Implement route-level stable slot order, dashboard pair, and maximum-four reducer in `frontend/src/features/market-chart/hooks/useChartSlot.ts`
- [X] T030 [P] [US2] Implement text/icon connection feedback and polite state announcements in `frontend/src/features/market-chart/components/ConnectionStatus.tsx`
- [X] T031 [US2] Implement the isolated accessible slot section and controls in `frontend/src/features/market-chart/components/ChartSlot.tsx`
- [X] T032 [US2] Implement responsive one-to-four grid, add/remove actions, and fifth-slot explanation in `frontend/src/features/market-chart/components/ChartGrid.tsx`
- [X] T033 [US2] Compose the Market dashboard route without News/Sentiment or strategy dependencies in `frontend/src/app/routes/market.tsx`

**Checkpoint**: US2 satisfies `MTC-US-01` independently on wide and narrow screens.

---

## Phase 5: User Story 3 — Change One Timeframe Independently (Priority: P2)

**Goal**: Reconfigure one slot while releasing its old binding and preserving all unaffected slot state.

**Independent Test**: Change `slot-1` from `5m` to `1h`; inject a late old-generation response and verify the other slots and the new generation remain unchanged.

### Tests for User Story 3

- [X] T034 [P] [US3] Write failing generation-token, query-cancellation, viewport-preservation, and same-selection slot tests in `frontend/tests/market-chart/timeframe-isolation.test.tsx`
- [X] T035 [P] [US3] Write failing subscribe/replace/unsubscribe idempotency and zero-reference cleanup integration tests in `backend/tests/integration/test_subscription_lifecycle.py`
- [X] T036 [US3] Extend the Playwright flow with timeframe isolation and late-old-generation delivery in `tests/e2e/realtime-multi-chart.spec.ts`

### Implementation for User Story 3

- [X] T037 [US3] Add slot generation, old-query cancellation, selection release/acquire, and viewport preservation to `frontend/src/features/market-chart/hooks/useChartSlot.ts`
- [X] T038 [US3] Add idempotent slot replacement and zero-reference upstream release to `backend/src/crypto_lab/application/chart_delivery/subscription_registry.py`
- [X] T039 [US3] Connect per-slot timeframe changes to historical/bootstrap/live lifecycle in `frontend/src/features/market-chart/components/ChartSlot.tsx`

**Checkpoint**: US3 satisfies `MTC-US-02`; no old subscription or late response changes the new slot generation.

---

## Phase 6: User Story 4 — Recover a Market Data Connection (Priority: P2)

**Goal**: Mark data stale, retry within bounds, backfill missing closed Candles, restore live truthfully, and isolate terminal failure.

**Independent Test**: Disconnect one selection, create missed closed intervals, reconnect, and prove exact gap recovery before `LIVE`; repeat until `ERROR`, then use manual retry.

### Tests for User Story 4

- [X] T040 [P] [US4] Write failing backoff, jitter-bound, attempt-limit, offline-pause, and state-transition unit tests in `backend/tests/unit/market_data/test_stream_recovery.py`
- [X] T041 [P] [US4] Write failing disconnect, heartbeat timeout, backfill completeness, duplicate recovery, exhaustion, and healthy-selection isolation tests in `backend/tests/integration/test_realtime_recovery.py`
- [X] T042 [P] [US4] Write failing stale/reconnecting/error/manual-retry frontend tests in `frontend/tests/market-chart/connection-recovery.test.tsx`
- [X] T043 [US4] Extend the Playwright flow with successful gap recovery and exhausted/manual-retry scenarios in `tests/e2e/realtime-multi-chart.spec.ts`

### Implementation for User Story 4

- [X] T044 [US4] Implement capped exponential backoff, jitter, attempt budget, offline pause, and continuity gate in `backend/src/crypto_lab/application/market_data/recover_stream.py`
- [X] T045 [US4] Add provider heartbeat detection, reconnect, and last-closed checkpoint reporting in `backend/src/crypto_lab/infrastructure/market_data/binance_realtime_provider.py`
- [X] T046 [US4] Integrate historical closed-Candle gap backfill before `LIVE` in `backend/src/crypto_lab/application/chart_delivery/stream_candles.py`
- [X] T047 [US4] Add reconnect state dispatch, retry command, and unaffected-selection behavior in `frontend/src/features/market-chart/hooks/useMarketDataConnection.ts`
- [X] T048 [US4] Add stale/reconnecting/error presentation and manual retry wiring in `frontend/src/features/market-chart/components/ChartSlot.tsx`

**Checkpoint**: US4 satisfies `MD-US-03`; a connected socket alone cannot falsely mark a gapped selection live.

---

## Phase 7: Polish and Cross-Cutting Validation

**Purpose**: Prove performance, observability, isolation, compatibility, and documentation across all stories.

- [X] T049 [P] Add sanitized stream lifecycle logs and metrics for clients, logical slots, unique selections, reconnects, gaps, invalid events, and latency in `backend/src/crypto_lab/api/websocket/market_data_channel.py`
- [X] T050 [P] Add the documented 10-session/four-slot propagation and 30-minute soak scenarios in `tests/load/realtime-market-data.js`
- [X] T051 [P] Add automated accessibility assertions for focus, names, state announcements, non-color status, and latest-Candle summary in `frontend/tests/market-chart/accessibility.test.tsx`
- [X] T052 Cross-check the TV5 generic extension seam without importing leaderboard behavior in `frontend/src/features/market-chart/components/CandlestickChart.tsx` and `specs/005-leaderboard-visualization/contracts/chart-overlays.md`
- [X] T053 Run every command and acceptance scenario in `specs/002-realtime-multi-chart/quickstart.md` and record measured environment/results in that file
- [X] T054 Re-run `$speckit-analyze`, resolve all CRITICAL/HIGH findings in `specs/002-realtime-multi-chart/`, and keep implementation blocked if Architecture/ADR-003 are not Accepted

---

## Dependencies and Execution Order

### Phase dependencies

- Phase 1 approval and contract tasks block all source implementation.
- Phase 2 depends on Phase 1 and blocks all user stories.
- US1 establishes the live Candle path used by US2–US4.
- US2 depends on US1 for a visible slot but can develop its UI tests/components in parallel with late US1 backend tasks.
- US3 depends on the US1 transport and US2 stable slots.
- US4 depends on the US1 stream and historical port; its unit recovery work can begin after Phase 2.
- Phase 7 follows the stories selected for delivery.

### User story completion order

```text
Setup/Approval → Foundation → US1 Realtime Candle → US2 Four-Chart Grid → US3 Independent Timeframe
                                      └──────────────────────────────→ US4 Recovery
US1 + US2 + US3 + US4 → Polish/Analyze
```

### Parallel opportunities

- T003–T005 can run in parallel after T001–T002 are approved.
- T006, T007, T009, T010, T012, and T013 use separate files and can run in parallel.
- Tests marked `[P]` within each story can be written together before that story's implementation.
- US4 recovery unit/integration fixtures can progress beside US2/US3 frontend work after US1 boundaries exist.
- T049–T051 can run in parallel before final quickstart validation.

## Parallel Example: User Story 1

```text
T014 backend Candle merge tests
T015 REST/WebSocket contract tests
T016 provider-to-WebSocket integration tests
T017 frontend parsing/merge tests
```

## Parallel Example: User Story 4

```text
T040 recovery policy unit tests
T041 disconnect/backfill integration tests
T042 frontend recovery-state tests
```

## Implementation Strategy

### MVP first

1. Complete Phase 1 and Phase 2.
2. Complete US1 with one chart.
3. Stop and validate `MD-US-02` independently.
4. Add US2 to reach the project-visible four-chart MVP.

### Incremental delivery

1. US1: one reliable realtime chart.
2. US2: one-to-four responsive charts.
3. US3: independent timeframe lifecycle.
4. US4: automatic recovery and gap continuity.
5. Phase 7: performance, accessibility, observability, and full analysis gate.

## Task Summary

- Total tasks: 58
- Setup and foundation: 13
- US1: 12
- US2: 8
- US3: 6
- US4: 9
- Polish and cross-cutting: 6
- Convergence: 4
- Suggested MVP: Phase 1 + Phase 2 + US1; project-visible TV2 slice adds US2.

## Phase 8: Convergence

**Purpose**: Close the remaining runtime-recovery and documentation gaps found after the completed implementation pass.

- [X] T055 [US4] Add a failing initially-missing-gap recovery test, then route recovery backfill through an adapter over the accepted TV1 historical use case before `LIVE` without changing the TV1 Candle/history contract, per FR-011, SC-005, and the plan recovery flow (partial)
- [X] T056 Update `README.md`, `context.md`, and `handoff.md` to match the implemented Feature 002 runtime, validation results, remaining gates, and non-mock market dashboard path, per the Phase 7 documentation purpose and completion-sync requirement (contradicts)

**Checkpoint**: Re-run `$speckit-converge`; it must report `Converged` without appending another task before Feature 002 can be declared complete.

## Phase 9: Convergence

**Purpose**: Restore the deployed browser-to-backend REST/WebSocket path that was hidden by mocked Playwright routes.

- [X] T057 **CRITICAL** Add failing frontend proxy configuration coverage, then proxy `/api/` and WebSocket `/ws/` from the Vite/Nginx frontend origin to the backend and validate JSON plus `101 Switching Protocols` through port `5173`, per US1/AC1, FR-004, and the plan deployment flow (contradicts)
- [X] T058 **CRITICAL** Add a failing concurrent-client fan-out test, then share one provider stream per Market Selection across dashboard connections without one client's release interrupting another, per the accepted shared-upstream identity in `data-model.md`, the plan selection-hub flow, NFR-001, and the documented 10-session load (partial)

**Checkpoint**: The real Compose Market dashboard receives historical and realtime Candles through its own origin; mocked Playwright routes are not the only passing browser path.
