# Crypto Strategy Lab

A UI-faithful, integration-ready React prototype for researching, composing, backtesting, and comparing simulated crypto strategies. It implements the seven-screen reference in `UI_ref` while keeping all visible trading activity explicitly historical or simulated.

## Implemented scope

- Responsive landing page and seven-destination research shell
- One-, two-, and four-pane market workspace with independent timeframe and indicator state
- Searchable market selection, watchlist persistence, unavailable-market feedback, and live/reconnecting/stale presentation
- Four-step, registry-driven strategy builder with generic schema and relationship validation
- Single backtest, deterministic strategy search, run history, trades, metrics, drawdown/equity views, and provenance
- Stable sortable/filterable leaderboard with keyboard-operable inspector
- Composed news/sentiment filters plus healthy, degraded, and empty states
- Operations dependency health, workers, queue, event filtering, and confirmed loop stop/resume
- 1024 px compact layout, keyboard/focus semantics, live regions, and reduced-motion support

## Architecture

The pages depend on UI-facing gateways defined in `src/services/ports.ts`. `ServiceProvider` injects deterministic mock adapters from `src/services/mock/createMockServices.ts`; pages do not import fixture collections or call transport APIs directly. Future REST/WebSocket adapters can be selected at app composition without rewriting screen components.

State is deliberately split:

- URL: current top-level destination
- workspace provider: selected market, watchlist, explanation preference, strategy context, connection state, notifications
- page state: chart panes, builder draft, tabs, filters, drawers, and confirmation state
- service adapters: deterministic market, strategy, backtest, leaderboard, news, and operations records

Configuration such as navigation, chart layouts, defaults, strategy presentation metadata, parameter constraints, presets, and product disclaimer lives under `src/config/` instead of inside page markup.

## Verification

```powershell
npm run typecheck
npm run test:unit
npm run build
npm run test:sites
```

The release gate currently passes 10 unit/contract tests and 4 Sites worker tests. Detailed visual, responsive, interaction, and console verification is recorded in `design-qa.md`.

## Spec Kit artifacts

The feature workflow is in `specs/001-frontend-prototype-system/`:

- `spec.md` — user stories, requirements, and measurable success criteria
- `plan.md` and `research.md` — architecture and integration decisions
- `data-model.md` and `contracts/frontend-services.md` — UI/domain and gateway boundaries
- `tasks.md` — completed dependency-ordered implementation tasks
- `quickstart.md` — local validation journeys

## Backend integration status

The frontend boundary is ready, but remote adapters are intentionally not fabricated for missing backend contracts.

- Available backend boundary: health and REST market-data dimensions/candles/datasets
- Contract-defined but not currently runnable from this checkout: realtime market stream, strategy registry/analysis, backtest/evaluation, and leaderboard APIs
- Backend contract still pending: composite strategy persistence, strategy search lifecycle, run listing/cancellation, news/sentiment, operations controls, tickers, and watchlists

When those contracts stabilize, add transport DTOs and mappers behind the existing gateway interfaces. Preserve source IDs, decimal strings, versions, checksums, lifecycle source status, and provenance; convert values for charts only at the presentation boundary.

