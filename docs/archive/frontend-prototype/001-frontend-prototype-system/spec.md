# Feature Specification: Crypto Strategy Lab Frontend System

**Feature Branch**: `001-frontend-prototype-system`

**Created**: 2026-08-17

**Status**: Draft

**Input**: User description: "Implement the supplied Crypto Strategy Lab mock UI as a reusable, non-hard-coded, integration-ready system."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Explore live market context (Priority: P1)

As a trader or strategy researcher, I can move from the product overview into a market workspace, select a supported market, compare up to four independently configured timeframes, and inspect visible price and indicator context.

**Why this priority**: Market context is the entry point for every strategy decision and proves the application shell, navigation, shared state, and chart workspace operate as one coherent product.

**Independent Test**: Start on the overview, enter the workspace, switch market and timeframe controls, change the chart layout, and verify that only the intended panes and shared market context update.

**Acceptance Scenarios**:

1. **Given** the overview is open, **When** the user selects the primary workspace action, **Then** the market workspace opens with a visible selected market, connection status, chart area, and watchlist.
2. **Given** multiple chart panes are visible, **When** the user changes one pane's timeframe, **Then** that pane updates without resetting the other panes.
3. **Given** a market is unavailable or no matching market is found, **When** the user searches or selects it, **Then** the interface communicates the unavailable or empty state without breaking the current workspace.

---

### User Story 2 - Compose a reusable strategy (Priority: P1)

As a strategy researcher, I can choose analysis methods, configure their parameters, select a combination rule, review the resulting composite, and save or send it to backtesting.

**Why this priority**: Strategy composition is the product's central value proposition and establishes extensible contracts for adding future analysis methods.

**Independent Test**: Complete the four-step strategy builder with at least two methods, adjust parameters, choose a weighted combination, and verify that the review summary and next actions reflect the selections.

**Acceptance Scenarios**:

1. **Given** the strategy catalog is open, **When** the user selects supported analysis methods, **Then** the selected methods appear in a shared strategy summary.
2. **Given** a selected method has configurable parameters, **When** the user enters an invalid combination, **Then** a clear validation message prevents progression until the values are valid.
3. **Given** the strategy review is complete, **When** the user starts a backtest, **Then** the backtest workspace opens with the composed strategy selected.

---

### User Story 3 - Evaluate and compare strategies (Priority: P2)

As a strategy researcher, I can configure and inspect a single backtest, observe a simulated strategy search, browse prior runs, and compare ranked results with risk and provenance details.

**Why this priority**: Evaluation turns strategy definitions into decisions and connects the backtest, search, run history, and leaderboard experiences.

**Independent Test**: Run the single-backtest flow, start and stop a search, inspect a run record, sort the leaderboard, and open a strategy detail panel.

**Acceptance Scenarios**:

1. **Given** a configured backtest, **When** the user runs it, **Then** the interface exposes return, win rate, drawdown, trades, risk metrics, and reproducibility context.
2. **Given** a strategy search is running, **When** the user stops or restarts it, **Then** its status and progress controls update consistently.
3. **Given** ranked strategies are visible, **When** the user sorts or selects a result, **Then** the ordering and selected strategy details update without losing the active filter context.

---

### User Story 4 - Monitor decision context and system activity (Priority: P3)

As an operator or researcher, I can review coin-related news sentiment and observe the health of the continuous strategy loop, its dependencies, workers, queue, and active run.

**Why this priority**: These screens make the prototype ready for later sentiment and operational integrations while remaining independently demonstrable today.

**Independent Test**: Filter the news list, inspect one item's classification, pause and resume the continuous loop, and verify the operational status panels remain coherent.

**Acceptance Scenarios**:

1. **Given** news items are available, **When** the user filters by coin or sentiment, **Then** only matching items remain and an explicit empty state appears when no items match.
2. **Given** an operations view is open, **When** the user pauses or resumes the continuous loop, **Then** the loop status and available actions update immediately.

### Edge Cases

- A search or filter returns no strategies, markets, runs, or news items.
- A chart layout request exceeds the four-pane product limit.
- A previously selected strategy method becomes unavailable before review.
- An invalid numeric parameter, zero weight total, or contradictory threshold is entered.
- Connection state changes from live to reconnecting or stale while the user remains on another screen.
- A search or continuous loop completes while its screen is not active.
- The viewport is narrower than the preferred desktop canvas and must retain access to all primary controls.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a consistent application shell with overview, market, strategies, backtests, leaderboard, news sentiment, and operations destinations.
- **FR-002**: The system MUST preserve shared user context, including selected market, watchlist, explanation preference, active strategy, and current run intent, when navigating between destinations.
- **FR-003**: Users MUST be able to select from supported markets and receive searchable available, unavailable, and empty states.
- **FR-004**: Users MUST be able to display one to four chart panes and configure each pane's timeframe independently.
- **FR-005**: The market workspace MUST expose visible loading, live, reconnecting, stale, and empty/error-friendly states that can later map to real provider data.
- **FR-006**: The system MUST expose analysis methods through a catalog whose labels, descriptions, parameter definitions, defaults, and availability are supplied as data rather than duplicated within page markup.
- **FR-007**: Users MUST be able to select multiple analysis methods and configure valid method-specific parameters.
- **FR-008**: Users MUST be able to choose a composite decision method, including majority and weighted modes, and see a plain-language explanation of the resulting behavior.
- **FR-009**: The system MUST validate strategy parameters and combination rules before allowing review or backtest actions.
- **FR-010**: Users MUST be able to review a complete strategy summary and transfer that strategy context into a backtest flow.
- **FR-011**: The backtest experience MUST provide single-run, strategy-search, and run-history views with interactive status controls and realistic result states.
- **FR-012**: The system MUST present return, win rate, maximum drawdown, trade count, Sharpe ratio, profit factor, and provenance for evaluated strategies.
- **FR-013**: Users MUST be able to sort and inspect leaderboard strategies without losing the current evaluation context.
- **FR-014**: Users MUST be able to filter news by relevant market context and sentiment and inspect classification details.
- **FR-015**: Users MUST be able to pause and resume the continuous strategy loop and inspect dependency, worker, queue, and active-run status.
- **FR-016**: Repeated visual and interaction patterns MUST behave consistently across destinations, including headers, panels, metrics, fields, status badges, tables, tabs, drawers, dialogs, empty states, and feedback messages.
- **FR-017**: Domain content and simulated records MUST be supplied through replaceable data and service boundaries so prospective remote integrations do not require page rewrites.
- **FR-018**: Primary navigation, controls, dialogs, fields, and tables MUST remain keyboard accessible and expose visible focus and descriptive labels.
- **FR-019**: The system MUST retain the supplied dark, information-dense desktop visual language while adapting safely to narrower desktop and tablet-sized viewports.
- **FR-020**: The prototype MUST avoid initiating real trades, presenting financial advice, or implying that simulated performance guarantees future results.

### Key Entities

- **Market**: A supported trading pair with display identity, provider availability, price summary, and watchlist state.
- **Chart Pane**: One market visualization slot with its own timeframe, indicators, and visible state.
- **Analysis Method**: A registered strategy building block with category, description, availability, parameter schema, and default values.
- **Composite Strategy**: A named set of configured analysis methods plus its decision rule, weights, thresholds, version, and review status.
- **Backtest Configuration**: A strategy, market, timeframe, date range, capital assumptions, execution assumptions, and reproducibility seed.
- **Backtest Run**: A lifecycle record with status, progress, metrics, trades, source configuration, and provenance.
- **Leaderboard Entry**: A ranked strategy evaluation with performance, risk, score, and linked run details.
- **News Item**: A source record with headline, time, related markets, sentiment label, score, and classification context.
- **Operational Snapshot**: Current loop, dependency, worker, queue, and active-run states.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time user can enter the market workspace and change one chart timeframe in under 60 seconds without external instructions.
- **SC-002**: A user can compose and review a two-method strategy in under 3 minutes with invalid configurations prevented before review.
- **SC-003**: All seven top-level destinations remain reachable in one action from the persistent workspace navigation.
- **SC-004**: At 1440 by 900 pixels, all primary workspace controls and the active page header are visible without unintended page-level horizontal scrolling.
- **SC-005**: At 1024 pixels wide, every primary flow remains usable and no persistent navigation or action control is clipped beyond reach.
- **SC-006**: Every interactive control in the primary market, strategy, backtest, leaderboard, news, and operations journeys is keyboard reachable and shows a visible focus state.
- **SC-007**: Replacing the simulated market, strategy, run, leaderboard, news, or operations provider requires changes at the data/service boundary rather than changes to the page composition.
- **SC-008**: Visual comparison with the supplied mock identifies no unresolved high- or medium-impact differences in layout hierarchy, typography, spacing, colors, visible assets, or core copy.

## Assumptions

- The requested deliverable is an integration-ready frontend prototype; authentication, persistence, real exchange connections, and backend API wiring are outside this feature's implementation scope.
- The existing backend remains the prospective integration target and will be connected through documented frontend service contracts later.
- The supplied mock and design tokens are the visual source of truth, with a preferred 1440 by 900 desktop viewport.
- Realistic deterministic sample records are acceptable for demonstrating loading, empty, success, warning, and running states.
- The first delivery is dark-theme only and English only.
- Mobile-native layouts and live trading execution are outside the first delivery.

## Scope Boundaries

### In Scope

- A reusable multi-page frontend, working core interactions, deterministic sample data, replaceable service interfaces, responsive desktop/tablet behavior, and validation evidence.

### Out of Scope

- Authentication, user accounts, database persistence, real-time exchange connections, actual order execution, production sentiment inference, and deployment.
