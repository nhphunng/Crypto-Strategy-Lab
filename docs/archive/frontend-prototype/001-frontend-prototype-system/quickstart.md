# Quickstart: Validate the Crypto Strategy Lab Frontend

## Prerequisites

- Node.js 24+
- Dependencies installed in `CryptoStrategy`
- A desktop browser viewport capable of 1440×900 and 1024×768

## Install and Verify

```powershell
npm.cmd install
npm.cmd run test:unit
npm.cmd run build
npm.cmd run test:sites
```

Expected outcome:

- Unit and interaction tests pass.
- The build produces `dist/client/index.html`, `dist/server/index.js`, and `dist/.openai/hosting.json`.
- The Sites worker test confirms static assets, SPA fallback, and non-fallback behavior for API/write requests.

## Run the Prototype

```powershell
npm.cmd run dev -- --host 0.0.0.0 --port 4173 --strictPort
```

Open the local preview with the Codex in-app browser and verify there are no page or console errors.

## Primary Validation Journeys

### 1. Market workspace

1. Open the overview and enter the Strategy Lab.
2. Confirm the persistent shell exposes all six workspace destinations.
3. Select the four-pane layout.
4. Change only the second pane from `15m` to `30m`; the remaining panes must retain their settings.
5. Search for an unavailable market and verify the active market is preserved with non-blocking feedback.
6. Exercise live, reconnecting, and stale connection states; last successful chart data remains visible.

### 2. Strategy composition

1. Select a two-method preset.
2. Set an invalid moving-average relationship; progression must be blocked with a labelled inline error.
3. Repair the parameters and select weighted combination.
4. Make weights total something other than 100%; review must remain disabled.
5. Balance the weights, review the strategy, and choose Run Backtest.
6. Confirm the backtest page receives the composed strategy and current market context.

### 3. Backtests and leaderboard

1. Complete a single backtest and verify return, win rate, drawdown, trades, Sharpe, profit factor, and provenance.
2. Start a strategy search, cancel the stop dialog once, then confirm stop and ensure tested count/results remain.
3. Inspect completed and failed run details.
4. Sort leaderboard score in both directions, filter strategy type, open an inspector, switch its tabs, and confirm sorting/filtering persist after close.

### 4. News and operations

1. Compose market, sentiment, and range filters; force an empty result and verify the explicit empty state.
2. Exercise degraded sentiment and confirm articles plus Market/Backtests remain accessible.
3. Stop the continuous loop with confirmation, verify counters stop, restart it, and verify counters resume.
4. Filter the operations event log by category.

## Accessibility and Responsive Checks

- Navigate primary flows using only Tab, Shift+Tab, arrow keys, Enter, Space, and Escape.
- Confirm dialogs/drawers are named, manage focus, close on Escape, and restore focus.
- Confirm sortable tables, segmented controls, switches, icon controls, and errors expose state and labels without relying on color alone.
- At 1440×900, 1180×820, and 1024×768 verify no document-level horizontal overflow, active page title and primary action remain reachable, and drawers fit the viewport.
- At 200% browser zoom, core flows remain usable; local table/chart scrolling is acceptable.

## Visual QA Gate

Capture the reference and implementation at the same viewport, state, font readiness, and reduced-motion setting. Compare full screens and focused regions for typography, spacing, token colors, chart/image quality, icons, and copy. Record every P0/P1/P2 iteration in project-root `design-qa.md`. Handoff is allowed only when its final line is exactly:

```text
final result: passed
```
