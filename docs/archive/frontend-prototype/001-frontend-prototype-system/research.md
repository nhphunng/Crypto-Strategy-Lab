# Research: Crypto Strategy Lab Frontend System

## Decision 1 — Feature-sliced application structure

**Decision**: Use a feature-sliced React SPA with a thin app composition layer, shared layout/UI primitives, typed domain models, and isolated feature workflows.

**Rationale**: The seven screens share a strong visual grammar but have distinct state machines. Feature slices keep orchestration local while common primitives remain reusable and independently testable.

**Alternatives considered**:

- Copy the reference files verbatim: fastest visually, but preserves direct fixture imports, scattered literals, monolithic state, and refresh-unsafe navigation payloads.
- Organize only by technical layer: initially simple, but each user journey becomes spread across unrelated folders.
- Microfrontends: unnecessary operational and dependency complexity for one prototype.

## Decision 2 — React, TypeScript, Vite, Tailwind, and Lucide

**Decision**: Align the target with the reference using React 19, TypeScript, Vite, Tailwind CSS v4, lucide-react, Inter, and JetBrains Mono.

**Rationale**: TypeScript protects entity and gateway contracts; Tailwind v4 can reproduce the provided token-driven design; the icon and font choices match the source mock. The existing Sites build shell remains compatible.

**Alternatives considered**:

- JavaScript plus JSDoc and plain CSS: fewer packages, but weaker service/schema guarantees and substantially more visual migration work.
- A different component system: would introduce styling drift and duplicate the supplied UI kit.

## Decision 3 — Route, workspace, and feature state separation

**Decision**: Keep route state in URLs, stable cross-screen context in `WorkspaceProvider`, and transient page workflow state in feature reducers/hooks. Persist only explicitly durable preferences through a storage adapter.

**Rationale**: Selected market, watchlist, explanation preference, connection summary, active strategy, and toasts are shared. Chart layouts, filters, dialogs, draft steps, and selected rows are feature-local. Progress simulation belongs in mock services.

**Alternatives considered**:

- One global store: couples timers, navigation, filters, and domain context and causes broad rerenders.
- Add an external state library: no current state complexity justifies another abstraction.

## Decision 4 — Gateway, mapper, and adapter boundary

**Decision**: Pages consume injected UI-facing gateways and normalized domain records. Deterministic mock adapters implement them now; future HTTP/WebSocket adapters and transport mappers can be selected at application composition.

**Rationale**: The checked-out backend has no readable source, and `origin/main` currently implements only health and market-data HTTP routes. Strategies, backtests, leaderboards, realtime events, search, news, and operations are contract-only or missing. Stable frontend ports prevent partial or inconsistent transport contracts from leaking into pages.

**Alternatives considered**:

- Import fixtures directly in screens: hard-codes the prototype and makes every page an integration point.
- Fetch directly in components: leaks envelopes, error shapes, version drift, and lifecycle differences into presentation code.
- Generate a client from all available OpenAPI documents: the contracts are partial and inconsistent, and several UI flows have no endpoint definitions yet.
- Invent future endpoints: would pre-empt backend specification ownership.

## Decision 5 — Current and prospective backend mapping

**Decision**: Define `MarketGateway`, `StrategyGateway`, `BacktestGateway`, `LeaderboardGateway`, `NewsGateway`, and `OperationsGateway`; keep source status/version/provenance alongside normalized frontend status.

**Rationale**: Existing market data exposes dimensions, candles, immutable datasets, and health; prospective contracts describe market streaming, strategy analyses, backtest/evaluation, and leaderboard snapshots. Gateway mappers can reconcile version, envelope, time-range, decimal, and lifecycle differences.

**Alternatives considered**:

- One universal repository: obscures meaningful domain behaviors.
- One shared backend enum: already conflicts with documented `REQUESTED`, `RUNNING`, `COMPLETED`, `FAILED`, `QUEUED`, `SUCCEEDED`, `CANCELLED`, and `PAUSED` states.

## Decision 6 — Declarative content and strategy schemas

**Decision**: Store navigation, landing content, markets, timeframes, chart presets, status metadata, metric definitions, table columns, method metadata, parameter definitions, presets, and cross-field constraints in typed configuration.

**Rationale**: This removes repeated literals from pages and allows future provider or registry metadata to replace local configuration. Strategy definitions own their labels, defaults, bounds, and generic constraints.

**Alternatives considered**:

- Separate metadata maps and ID-based validation branches: the reference already demonstrates drift and makes plugins require code edits.
- Add a full schema library now: a small typed constraint evaluator is sufficient for the prototype and keeps the dependency surface smaller.

## Decision 7 — Normalized resource and job states

**Decision**: Use discriminated resource states for `idle`, `loading`, `success`, `empty`, and `error`, plus freshness/availability states such as `live`, `partial`, `stale`, `reconnecting`, and `degraded`. Model searches and loops as explicit state machines.

**Rationale**: The mock requires non-happy states across every feature. Shared semantics prevent contradictory combinations of booleans and make remote adapters predictable.

**Alternatives considered**:

- Independent booleans per page: easy to start, but permits impossible states and inconsistent feedback.

## Decision 8 — Presentational chart boundary

**Decision**: `CandleChart` receives candles, overlays, markers, interval, selected range, and dimensions. Data generation, indicator calculation, transport normalization, and stream merging stay in services and hooks.

**Rationale**: The chart appears in the landing preview, market panes, backtest analysis, and leaderboard details. A pure input-driven component is reusable, testable, and replaceable by a future charting library.

**Alternatives considered**:

- Chart-owned fetching and global context reads: makes multi-pane independence and reuse difficult.

## Decision 9 — Testing and validation stack

**Decision**: Use Vitest with jsdom, React Testing Library, user-event, and jest-dom for domain/component/integration tests; retain the Node Sites worker test; use the Codex in-app browser for real interaction, responsive, accessibility, console, and visual comparison evidence.

**Rationale**: Vitest shares Vite transforms, Testing Library exercises user-visible behavior, and browser verification covers layout and focus behavior that jsdom cannot. Existing packaging tests protect the Sites-ready output.

**Alternatives considered**:

- Jest: adds transform and configuration duplication.
- jsdom-only verification: cannot establish visual fidelity, layout, real focus behavior, or console cleanliness.
- Storybook in the first delivery: useful later, but disproportionate to this prototype.

## Decision 10 — Responsive and accessibility baseline

**Decision**: Treat 1440×900 as the visual source viewport, validate 1180×820 and 1024×768, target WCAG 2.2 AA, and prefer accessibility improvements over exact cloning of inaccessible reference behaviors.

**Rationale**: The design is intentionally dense and desktop-first. Compact widths require a collapsed rail, internal table scrolling, stacked secondary panels, viewport-bounded drawers, and preserved primary actions. Dialog semantics, focus restoration, keyboard tables, labelled icon controls, non-color status cues, and reduced motion are release gates.

**Alternatives considered**:

- Mobile-native redesign: outside current scope and would diverge from the selected desktop source.
- Pixel matching inaccessible controls: violates the specification and leaves core journeys unusable for keyboard users.

## Backend Integration Risks

- Only health and market-data HTTP routes are currently implemented on the authoritative remote branch; other flows must remain clearly simulated.
- HTTP/WS schema versions use inconsistent formats (`1`, `"1"`, and `"1.0.0"`).
- Market ranges are half-open while a leaderboard visualization contract describes an inclusive end.
- Success/error envelopes and lifecycle names vary by feature contract.
- Strategy parameter relationship rules are not yet machine-readable enough for a generic remote validator.
- Strategy persistence, strategy search, run listing/cancellation, news/sentiment, operations, ticker summaries, and watchlists have no authoritative API contract.
- Decimal values and provenance identifiers must remain lossless until presentation mapping.
- Future remote mode should use same-origin deployment or a development proxy unless the backend adds CORS.

All planning unknowns are resolved for the frontend prototype. Missing backend contracts are explicit integration dependencies, not blockers for deterministic mock adapters.
