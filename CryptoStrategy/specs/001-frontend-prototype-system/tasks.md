# Tasks: Crypto Strategy Lab Frontend System

**Input**: Design documents from `/specs/001-frontend-prototype-system/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Organization**: Tasks are grouped by user story and remain independently testable after the shared foundation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it changes different files with no unmet dependency.
- **[Story]**: Maps implementation work to a prioritized story from `spec.md`.

## Phase 1: Setup

**Purpose**: Align the bootstrapped project with the selected stack and preserve its Sites runtime.

- [X] T001 Update React, TypeScript, Tailwind, routing, icon, font, and test dependencies plus scripts in `package.json`
- [X] T002 [P] Configure TypeScript project references in `tsconfig.json` and `tsconfig.app.json`
- [X] T003 [P] Configure React, Tailwind, aliases, test environment, and `terminal.local` preview support in `vite.config.ts`
- [X] T004 [P] Add Node, build, coverage, environment, and editor patterns to `.gitignore`
- [X] T005 Preserve and validate Sites worker/build files in `worker/index.js`, `scripts/prepare-sites-build.mjs`, and `tests/sites-worker.test.mjs`

---

## Phase 2: Foundational

**Purpose**: Create the reusable, typed, integration-ready platform that blocks every user story.

- [X] T006 [P] Define color, type, spacing, radius, sizing, focus, reduced-motion, and responsive tokens in `src/theme/tokens.css` and `src/index.css`
- [X] T007 [P] Define shared resource, market, strategy, backtest, leaderboard, news, and operations models in `src/domain/index.ts`
- [X] T008 [P] Define navigation, timeframe, layout, metric, status, and product content configuration in `src/config/index.ts` and `src/config/strategies.ts`
- [X] T009 Define all frontend gateway interfaces and application service registry types in `src/services/ports.ts`
- [X] T010 Implement deterministic fixtures, seeded generators, and injected mock gateway adapters in `src/services/mock/createMockServices.ts` and `src/lib/mock.ts`
- [X] T011 Implement ServiceProvider, workspace state, persisted preferences, route context, timers, and toast state in `src/app/providers/AppProviders.tsx` and `src/lib/store.tsx`
- [X] T012 [P] Implement accessible shared controls, fields, segmented groups, toggles, and buttons in `src/components/ui.tsx`
- [X] T013 [P] Implement shared badges, panels, metrics, progress, key-value rows, and data display primitives in `src/components/ui.tsx`
- [X] T014 [P] Implement accessible drawer, modal, tooltip, toast, loading, empty, error, and degraded states in `src/components/ui.tsx`
- [X] T015 Implement the persistent top bar, responsive side rail, page header, and app shell in `src/components/Shell.tsx`
- [X] T016 Implement route configuration and application composition for all seven destinations in `src/App.tsx`, `src/config/index.ts`, and `src/app/providers/AppProviders.tsx`

**Checkpoint**: Routes, providers, service ports, shared components, and design tokens are ready.

---

## Phase 3: User Story 1 — Explore live market context (Priority: P1) 🎯 MVP

**Goal**: Enter the lab, choose a market, and operate one to four independent chart panes with realistic connection and watchlist states.

**Independent Test**: Open `/market`, select four panes, change only pane 2 to `30m`, toggle its overlays, search an unavailable market, and exercise live/reconnecting/stale states without losing the last candles.

- [X] T017 [P] [US1] Implement the input-driven candlestick chart and deterministic indicator utilities in `src/components/CandleChart.tsx` and `src/lib/mock.ts`
- [X] T018 [P] [US1] Implement searchable market selector and reusable watchlist controls in `src/components/MarketSelector.tsx` and `src/screens/Market.tsx`
- [X] T019 [US1] Implement independent pane state, layout cap, and gateway-backed data access in `src/screens/Market.tsx`
- [X] T020 [US1] Implement Market page composition, chart panes, watchlist, connection states, and indicator drawer in `src/screens/Market.tsx`
- [X] T021 [P] [US1] Cover pane independence, deterministic candles, search, persistence fallback, and unavailable markets in `src/test/contracts/services.test.ts` and the browser QA record

**Checkpoint**: The market workspace is usable as an independent MVP.

---

## Phase 4: User Story 2 — Compose a reusable strategy (Priority: P1)

**Goal**: Build, validate, review, save, and transfer a composite strategy to backtesting from declarative method schemas.

**Independent Test**: Select a two-method preset, trigger and repair a cross-field error, configure weighted voting, trigger and repair a weight-total error, review, and hand off to `/backtests?tab=single`.

- [X] T022 [P] [US2] Implement generic parameter and composite-rule validation in `src/config/strategies.ts`
- [X] T023 [US2] Implement strategy draft state, presets, step navigation, and backtest handoff in `src/screens/Strategies.tsx`
- [X] T024 [US2] Implement choose, configure, combine, and review step components in `src/screens/Strategies.tsx`
- [X] T025 [US2] Implement the full Strategies page, summary aside, provenance drawer, save, and run actions in `src/screens/Strategies.tsx`
- [X] T026 [P] [US2] Add validator coverage in `src/test/unit/strategy-builder.test.ts` and builder-flow browser QA in `design-qa.md`

**Checkpoint**: A valid composite strategy can be built and transferred without page-owned method conditionals.

---

## Phase 5: User Story 3 — Evaluate and compare strategies (Priority: P2)

**Goal**: Run a single simulation, control strategy search, inspect run history, and compare ranked strategy results.

**Independent Test**: Use all three Backtests tabs, stop and restart search, inspect run provenance, then sort/filter the leaderboard and inspect a selected row while preserving view state.

- [X] T027 [P] [US3] Implement shared trade table, provenance views, equity/drawdown displays, and metrics in `src/screens/Backtests.tsx` and `src/components/ui.tsx`
- [X] T028 [US3] Implement single-backtest, strategy-search, and run-history state machines behind gateway-backed data in `src/screens/Backtests.tsx` and `src/lib/store.tsx`
- [X] T029 [US3] Implement Single Backtest, Strategy Search, and Runs tab compositions in `src/screens/Backtests.tsx`
- [X] T030 [US3] Implement stable metric-aware sorting, strategy type filtering, and selected-entry state in `src/screens/Leaderboard.tsx`
- [X] T031 [US3] Implement Leaderboard table, filters, inspector tabs, and cross-feature actions in `src/screens/Leaderboard.tsx`
- [X] T032 [P] [US3] Cover search lifecycle, provenance data, sorting, filtering, and inspector behavior in `src/test/contracts/services.test.ts` and browser QA

**Checkpoint**: Evaluation and comparison flows work independently with complete risk/provenance context.

---

## Phase 6: User Story 4 — Monitor decision context and system activity (Priority: P3)

**Goal**: Review filtered sentiment context and monitor/control the continuous strategy loop and operational health.

**Independent Test**: Compose news filters, inspect healthy/degraded/empty states, stop/restart the loop, and filter operational events.

- [X] T033 [P] [US4] Implement reusable landing content and realistic gateway-backed workflow previews in `src/screens/Landing.tsx`
- [X] T034 [US4] Implement composed news filters, sentiment summaries, degraded/empty states, and detail drawer in `src/screens/News.tsx`
- [X] T035 [US4] Implement loop confirmation/start-stop state, dependency health, workers, queue, active run, and event filters in `src/screens/Operations.tsx`
- [X] T036 [P] [US4] Cover news filters/degradation and operations lifecycle through service contract tests and browser QA

**Checkpoint**: All seven destinations and their primary interactions are complete.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Close integration, accessibility, responsive, build, and visual fidelity requirements.

- [X] T037 Add adapter contract tests in `src/test/contracts/services.test.ts` and verify cross-route context in browser QA
- [X] T038 Add compact-width layouts, internal table scrolling, viewport-bounded drawers, and 1024px rail behavior across `src/index.css` and page compositions
- [X] T039 Audit and correct keyboard semantics, accessible names, focus containment/restoration, live regions, and non-color status cues across `src/components/` and `src/screens/`
- [X] T040 Run TypeScript, unit tests, production build, and Sites worker validation from `package.json`
- [X] T041 Capture deterministic 1440×900 and 1024×768 reference/implementation states and verify primary interactions plus console cleanliness in the Codex in-app browser
- [X] T042 Produce and pass the source-versus-implementation comparison history in `design-qa.md`
- [X] T043 Validate the quickstart journeys and record the completed scope and remaining backend integration dependencies in `README.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1 Setup has no dependencies.
- Phase 2 Foundational depends on Setup and blocks all user stories.
- US1 and US2 are both P1 and can begin after Foundation; the strategy-to-backtest handoff is independently verifiable before US3 is complete.
- US3 depends on Foundation and consumes the shared strategy context contract, but remains independently testable with seeded fixtures.
- US4 depends only on Foundation.
- Polish depends on all selected stories.

### Parallel Opportunities

- T002–T004 can proceed in parallel after T001.
- T006–T008 and T012–T014 change independent foundation files.
- T017 and T018 can proceed in parallel; T021 can be authored alongside T019–T020.
- T022 and T026 can proceed while the builder composition is implemented.
- T027, T030, and T032 touch separate evaluation files.
- T033 and T036 can proceed while News and Operations pages are implemented.

## Implementation Strategy

### MVP First

1. Complete Setup and Foundation.
2. Complete US1 Market workspace.
3. Validate Market independently at 1440×900 and 1024×768.
4. Add US2, then US3, then US4 without changing gateway or shared-component contracts.

### Incremental Delivery

- Foundation establishes visual fidelity and integration seams.
- Market proves multi-pane state and provider boundaries.
- Strategy Builder proves registry-driven extensibility.
- Backtests and Leaderboard prove long-running job and provenance patterns.
- Landing, News, and Operations finish the end-to-end product narrative.
- Final QA verifies that accessibility and maintainability improvements did not create visual drift.

## Format Validation

All 43 tasks use the required checkbox, sequential ID, optional `[P]`, user-story label where applicable, and exact file paths.
