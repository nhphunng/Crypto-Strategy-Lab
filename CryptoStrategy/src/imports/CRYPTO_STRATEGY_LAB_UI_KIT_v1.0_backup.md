# Crypto Strategy Lab — UI Kit v1.0

A desktop-first UI kit for generating a functional prototype of **Crypto Strategy Lab**. The system is inspired by the interaction grammar of professional charting and crypto analytics products such as TradingView, CoinGlass, CoinMarketCap, and Binance, but it intentionally avoids pixel-copying any brand.

## 0. Product fit

The UI kit is designed around these product capabilities:

- Realtime and historical crypto market data.
- Up to four candlestick charts with independent timeframes.
- Built-in strategies: MA, RSI, Bollinger Bands, Support/Resistance.
- Strategy plugin discovery and versioning.
- Composite strategies using majority vote or weighted combination.
- Search configuration and continuous search loop.
- Historical backtesting with trade simulation.
- Evaluation metrics and Top-K leaderboard.
- Signal/trade overlays on charts.
- News collection and sentiment analysis.
- Operational visibility for stream, worker, queue, retry, and loop health.

The product is an **analysis and simulation lab**, not a real-money execution terminal. Do not introduce wallet, deposit, withdrawal, order placement, leverage, or exchange trading controls into the MVP.

---

# 1. Design direction

## 1.1 Visual character

**Keywords:** analytical, dense, calm, precise, professional, realtime, modular.

The interface should feel closer to a professional research terminal than a consumer crypto app.

Use:

- dark-first neutral surfaces;
- compact information density;
- thin separators instead of floating cards everywhere;
- edge-to-edge charts inside workspaces;
- small, strong typography hierarchy;
- semantic colors only when they communicate meaning;
- monospace numerals for prices, percentages, timestamps, IDs, and metrics;
- persistent controls near the data they affect.

Avoid:

- oversized hero sections;
- decorative crypto illustrations;
- neon gradient backgrounds;
- glassmorphism as a default surface;
- large 20–32 px radii on every container;
- excessive shadows;
- card grids where a table or split-pane is more efficient;
- rainbow chart colors without semantic purpose;
- giant empty padding typical of marketing pages.

## 1.2 UX principles

1. **Chart first, controls second.** The chart or evaluation result should dominate the workspace.
2. **Preserve analytical context.** Opening details should use drawers, split panes, or expandable rows before navigating away.
3. **Realtime state is explicit.** Always distinguish `Live`, `Reconnecting`, `Stale`, `Paused`, and `Error`.
4. **Dense but scannable.** Use alignment, tabular numerals, column grouping, and subtle borders instead of large spacing.
5. **Progressive disclosure.** Basic strategy settings stay visible; advanced parameters move into drawers/accordions.
6. **No hidden destructive state.** Stopping a search or loop requires clear outcome text.
7. **Explainability by default.** A strategy result should reveal members, parameters, versions, signals, metrics, trades, and provenance.
8. **Keyboard-friendly desktop workflow.** Pair search, command search, timeframe changes, and table navigation should work without relying only on the mouse.

---

# 2. Foundations

## 2.1 Color tokens — dark theme

| Token | Value | Usage |
|---|---:|---|
| `bg.canvas` | `#0B0E13` | App background |
| `bg.workspace` | `#0E1218` | Main chart/data workspace |
| `bg.surface` | `#131820` | Panels, tables, drawers |
| `bg.surface.hover` | `#181F29` | Hover rows / controls |
| `bg.surface.active` | `#1D2632` | Selected item |
| `border.subtle` | `#202936` | Panel separators |
| `border.default` | `#2B3543` | Inputs, focused panel edges |
| `text.primary` | `#E7ECF3` | Main text |
| `text.secondary` | `#9AA7B6` | Secondary labels |
| `text.muted` | `#687586` | Metadata / disabled |
| `accent.primary` | `#4F7CFF` | Primary action / selected tab |
| `accent.primary.hover` | `#638BFF` | Hover |
| `semantic.positive` | `#21C58B` | Profit / BUY / healthy |
| `semantic.negative` | `#F05B64` | Loss / SELL / failed |
| `semantic.warning` | `#E6B94A` | Stale / degraded / warning |
| `semantic.info` | `#59A8FF` | Informational status |
| `semantic.neutral` | `#8894A3` | HOLD / neutral sentiment |
| `semantic.purple` | `#A78BFA` | Search/ML-specific highlight, sparingly |
| `chart.grid` | `#1B2430` | Chart grid |
| `chart.crosshair` | `#667386` | Crosshair |
| `chart.support` | `#22C98A33` | Support zone fill |
| `chart.resistance` | `#F05B6433` | Resistance zone fill |

### Semantic rules

- Green means positive outcome, BUY, profitable trade, healthy state.
- Red means negative outcome, SELL, loss, failed state.
- Yellow means warning, stale data, degraded dependency.
- Blue is the product interaction accent, not a financial signal.
- Purple is reserved for search/ML/system-generated candidate concepts; do not use it as the global accent.
- Never use only color to convey status; pair it with text/icon/shape.

## 2.2 Optional light theme

Keep light theme secondary for the prototype. If implemented, invert surfaces but preserve semantic hues and contrast. Do not make the two themes visually unrelated.

## 2.3 Typography

### UI font

- Primary: `Inter`, `Geist`, or system sans-serif.
- Fallback: `ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`.

### Numeric / code font

- `JetBrains Mono`, `IBM Plex Mono`, or `ui-monospace`.
- Use for prices, timestamps, strategy IDs, job IDs, versions, percentages, and parameters.

### Scale

| Style | Size / line | Weight | Usage |
|---|---|---:|---|
| Display | 24 / 32 | 600 | Rare page heading |
| H1 | 20 / 28 | 600 | Workspace title |
| H2 | 16 / 24 | 600 | Panel title |
| Body | 14 / 20 | 400 | Default UI text |
| Body strong | 14 / 20 | 550 | Important values |
| Small | 12 / 18 | 400 | Metadata |
| Micro | 11 / 16 | 500 | Table labels, tags |
| Numeric | 12–14 / 18–20 | 500 | Market values |

Use uppercase only for very short market/status labels such as `LIVE`, `BUY`, `SELL`.

## 2.4 Spacing

Use a 4 px base scale:

`4, 8, 12, 16, 20, 24, 32, 40, 48`

Rules:

- data tables: 8–12 px horizontal cell padding;
- panel padding: 12 or 16 px;
- major workspace gaps: 1 px separator or 8 px where cards are necessary;
- avoid 32+ px internal whitespace in data-heavy areas.

## 2.5 Radius

| Token | Value | Usage |
|---|---:|---|
| `radius.xs` | 3 px | status tags |
| `radius.sm` | 5 px | buttons, inputs |
| `radius.md` | 8 px | popovers, cards |
| `radius.lg` | 10 px | drawers/modals only |

Never make data tables, chart panels, and every section independently pill-shaped.

## 2.6 Borders and elevation

- Use 1 px separators for most hierarchy.
- Use shadows only for floating popovers, command palette, dropdowns, and modals.
- Side panels and chart panes should usually be separated by borders, not shadows.

## 2.7 Iconography

Use Lucide-style 16–18 px line icons.

Recommended icons:

- Market: `CandlestickChart`
- Strategies: `BrainCircuit` or `Workflow`
- Backtests: `History`
- Leaderboard: `Trophy`
- News: `Newspaper`
- Sentiment: `Activity`
- Operations: `ServerCog`
- Search: `Search`
- Filter: `SlidersHorizontal`
- Run: `Play`
- Stop: `Square`
- Pause: `Pause`
- Refresh/reconnect: `RefreshCw`
- Details/provenance: `GitBranch` or `Fingerprint`

---

# 3. Shell and information architecture

## 3.1 Desktop target

Primary prototype canvas: **1440 × 900**.

Minimum supported desktop width: **1180 px**.

This product should not be designed mobile-first because the core job involves multi-chart and data-heavy analysis.

## 3.2 App shell

### Top bar — 48 px

Left to right:

1. Product mark: `CSL` + `Crypto Strategy Lab`.
2. Pair selector: `BTC / USDT`.
3. Global command/search trigger: `⌘ K` / `Ctrl K`.
4. Current dataset/realtime status.
5. Optional clock / last sync.
6. Theme/help/profile placeholders if needed.

### Primary navigation — left rail, 52 px collapsed / 184 px expanded

Order:

1. Market
2. Strategies
3. Search Lab
4. Backtests
5. Leaderboard
6. News & Sentiment
7. Operations

The active section uses a subtle filled state and a 2 px accent indicator.

Do not expose provider-internal or worker-internal actions as normal product navigation items.

### Workspace

Use resizable split panes. Prefer separators and nested panes over independent rounded cards.

### Context panel — 320–380 px

Optional right drawer for:

- strategy parameters;
- chart indicator settings;
- leaderboard details;
- provenance;
- job detail;
- news detail.

---

# 4. Core components

## 4.1 Global controls

### `PairSelector`

- 220–260 px wide searchable combobox.
- Row: coin icon, pair symbol, provider, 24h change if available.
- Selected display: `BTCUSDT` + provider badge.
- Keyboard searchable.

### `TimeframeTabs`

Compact segmented toolbar:

`1m  5m  15m  30m  1h  2h  4h  1d`

- 28 px high.
- Active timeframe uses accent text + subtle fill.
- Each chart owns its own instance.
- Avoid pill styling for each option; treat as toolbar tabs.

### `ConnectionStatus`

States:

- green dot + `Live`
- blue spinner + `Connecting`
- yellow dot + `Stale · 18s`
- yellow spinner + `Reconnecting`
- red dot + `Disconnected`

Tooltip shows provider and last update timestamp.

### `CommandPalette`

Actions:

- switch page;
- open pair;
- change timeframe;
- add indicator;
- open strategy;
- start backtest;
- open recent run.

---

# 5. Chart system

## 5.1 `ChartPanel`

Structure:

```text
┌ Panel header ───────────────────────────────────────────┐
│ BTCUSDT · Binance     15m      LIVE        ⋯           │
├ Chart toolbar ──────────────────────────────────────────┤
│ Indicators  Strategy overlay  Layout  Reset  Settings  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│              Candlestick workspace                      │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ Volume / optional indicator pane                        │
└─────────────────────────────────────────────────────────┘
```

### Required chart layers

- candlestick;
- volume;
- MA;
- Bollinger Bands;
- Support zones;
- Resistance zones;
- BUY / SELL signal markers;
- Entry / Exit markers;
- optional Stop Loss / Take Profit if a later feature adds them.

### Chart marker grammar

- BUY: upward triangle, green, below candle.
- SELL: downward triangle, red, above candle.
- Entry: small outlined circle with `E`.
- Exit: small outlined circle with `X`.
- Selected trade: highlight the interval between entry and exit.
- Support/Resistance: translucent zone, not a giant solid block.

### Chart legend

Place active overlays in one compact row inside the chart top-left:

`MA20  62,840` · `RSI14  57.2` · `SR v3`

Clicking an item opens its settings in the right drawer.

## 5.2 Multi-chart layouts

Provide layout presets:

- 1 chart;
- 2 horizontal;
- 2 vertical;
- 3 charts: 1 large + 2 stacked;
- 4 charts: 2 × 2.

For MVP, max 4.

Each panel keeps independent timeframe state. Pair synchronization can be a global toggle.

## 5.3 Chart interaction

- crosshair synchronized across charts only when enabled;
- wheel zoom;
- drag pan;
- reset view action;
- visible selected historical range;
- never render unbounded full history by default;
- realtime update should update affected candles without remounting the whole dashboard.

---

# 6. Data-display components

## 6.1 `MetricCardCompact`

Use only for 4–6 primary metrics, not every value.

Example:

```text
RETURN
+18.2%
vs baseline +4.8%
```

Height: 72–88 px.

## 6.2 `MetricStrip`

Preferred for dense pages:

`Return +18.2% | Win rate 61% | MDD -6.1% | Trades 81 | Sharpe 1.42`

## 6.3 `DataTable`

Default row height: 36 px.

Header height: 34 px.

Capabilities:

- sticky header;
- sortable columns;
- filter chips;
- pagination;
- column visibility;
- row selection;
- keyboard focus;
- compact numeric alignment;
- monospace numeric cells;
- skeleton state;
- empty/partial/failed state.

Positive/negative cells use semantic text colors but keep the row background neutral.

## 6.4 `StatusBadge`

Variants:

- `LIVE`
- `RUNNING`
- `QUEUED`
- `COMPLETED`
- `FAILED`
- `CANCELLED`
- `DEGRADED`
- `STALE`
- `BUY`
- `SELL`
- `HOLD`
- `POSITIVE`
- `NEUTRAL`
- `NEGATIVE`

Use square-ish tags with 3–5 px radius, not full pills by default.

---

# 7. Strategy components

## 7.1 `StrategyLibraryRow`

Columns:

- strategy name;
- type/category;
- version;
- parameters summary;
- compatible contract version;
- last test status;
- actions.

Example:

`Moving Average | Trend | v3 | fast=20 slow=50 | contract v1 | Tested`

## 7.2 `StrategyChip`

Compact selectable item used in builders:

`MA · v3`

Selected chips can be reordered in a composite strategy.

## 7.3 `ParameterField`

Supported controls:

- integer/decimal input;
- slider only when range tuning benefits from it;
- select;
- toggle;
- min/max range pair.

Always show:

- field label;
- current value;
- valid range/default if needed;
- field-level validation message.

## 7.4 `CompositeBuilder`

Desktop split layout:

```text
Strategy members             Combination policy
────────────────────         ─────────────────────────
MA v3       weight 0.2       Weighted combination
RSI v2      weight 0.3       Buy threshold    0.30
SR v1       weight 0.5       Sell threshold  -0.30
                             Tie / neutral rule
```

Support two policy modes:

- Majority vote.
- Weighted combination.

Always expose an `Explain decision` preview that shows how sample member signals produce the final signal.

## 7.5 `StrategyVersionBadge`

Examples:

- `v1`
- `v2`
- `Immutable`

Click opens provenance/version history, not an inline editor for historical versions.

---

# 8. Search and loop components

## 8.1 `SearchConfigPanel`

Sections:

1. Strategy types.
2. Parameter ranges.
3. Combination size.
4. Candidate limit.
5. Generator: Random Search for MVP.
6. Seed.
7. Dataset / pair / timeframe / date range.
8. Stop condition.

Primary action: `Start search`.

Secondary: `Save configuration` if prototype scope permits.

## 8.2 `RunProgressHeader`

```text
RUNNING   Search #SR-0184
364 / 2,000 candidates     18.2%     ETA 06:41
```

Actions: `Stop` and optional `Pause` only if supported by the feature spec.

## 8.3 `RunHealthStrip`

`Workers 4/4 | Queue 218 | Failed 3 | Retried 2 | Throughput 6.8 jobs/s | Top-1 84.1`

## 8.4 `LiveCandidateFeed`

Compact event stream:

```text
#364  MA20 + RSI14 + SR   score 81.4   rank #2
#365  MA50 + BB20         score 74.2   rank #8
#366  RSI21 + SR          failed       retry 1/3
```

Avoid animated casino-like effects. New rows can use a subtle 400 ms background fade.

---

# 9. Backtest components

## 9.1 `BacktestSummary`

Header:

- strategy name/version;
- pair/timeframe;
- historical range;
- dataset version/checksum shortcut;
- execution config shortcut;
- run status.

Then use `MetricStrip` or 4–6 compact metric blocks.

## 9.2 Required metrics

Primary:

- Total Return;
- Win Rate;
- Maximum Drawdown;
- Number of Trades.

Secondary when available:

- Profit Factor;
- Sharpe Ratio;
- final equity;
- duration.

## 9.3 `EquityCurve`

Line chart with optional drawdown area in a separate pane.

Do not make the equity curve visually more prominent than the market chart when the user is inspecting actual signals.

## 9.4 `TradeTable`

Columns:

`# | Side | Entry time | Entry | Exit time | Exit | P/L | Duration`

Selecting a trade highlights it on the market chart.

## 9.5 `ProvenanceDrawer`

Show:

- strategy ID/version;
- member strategy versions;
- parameter set;
- dataset provider/pair/timeframe/range/version;
- search generator/version;
- seed;
- scoring policy/version;
- backtest config;
- result ID/checksum if available.

This drawer is a first-class feature, not hidden debug metadata.

---

# 10. Leaderboard components

## 10.1 `LeaderboardTable`

Columns:

`Rank | Strategy | Score | Return | Win Rate | MDD | Trades | Sharpe | Updated`

Defaults:

- Top-K = 10 for demo;
- current scoring policy shown above table;
- sort by Score unless the user chooses a metric;
- sticky top three rows only if it does not interfere with sorting.

Rank visual:

- #1 accent border/icon, not a gold gradient card;
- #2/#3 subtle emphasis;
- others neutral.

## 10.2 Drill-down

Click a row → open a right-side detail pane with:

1. metrics;
2. strategy members/parameters;
3. recent signal summary;
4. actions: `Visualize`, `Open backtest`, `View provenance`.

`Visualize` opens the chart with strategy overlays, BUY/SELL, Entry/Exit, and trade table.

Leaderboard updates should not refresh the whole page.

---

# 11. News and sentiment components

## 11.1 `NewsTable`

Columns:

`Published | Source | Headline | Related coin | Sentiment | Score`

Filters:

- coin/pair;
- source;
- sentiment;
- date range.

## 11.2 `SentimentBadge`

- Positive: green icon + label + score.
- Neutral: gray label + score.
- Negative: red icon + label + score.

## 11.3 `SentimentSummary`

Use a compact distribution bar or small horizontal bars rather than a large donut by default.

Example:

`Positive 48% | Neutral 32% | Negative 20%`

Show model version and analysis period nearby.

## 11.4 Failure behavior

If news/sentiment is unavailable:

- show a local degraded state in this module;
- do not block Market, Strategy, or Backtest workspaces;
- show `Sentiment unavailable — technical analysis continues`.

---

# 12. Operations components

## 12.1 `SystemHealthTable`

Rows:

- Market Data Provider;
- realtime stream;
- database;
- queue;
- backtest workers;
- news provider;
- sentiment service.

Columns:

`Component | Status | Latency/lag | Last healthy | Detail`

Required dependencies and optional dependencies should be visually distinguishable.

## 12.2 `WorkerGrid`

Compact list, not decorative cards:

`worker-01 | RUNNING | job BT-9081 | 82% | 1.8 jobs/s`

## 12.3 `QueuePanel`

Metrics:

- queue depth;
- oldest job age;
- processing rate;
- failures;
- retries.

## 12.4 `EventLog`

Monospace compact timeline with filters for:

- market events;
- search events;
- backtest events;
- evaluation/ranking events;
- news/sentiment events.

---

# 13. Page templates

## Screen A — Market Lab

```text
┌ Top bar ───────────────────────────────────────────────────────────────┐
├ Nav ┬─────────────────────────────────────────────────────────────────┤
│     │ Pair + layout + sync controls                                  │
│     ├───────────────────────────────┬─────────────────────────────────┤
│     │ BTCUSDT · 5m                  │ BTCUSDT · 15m                   │
│     │ Candlestick                   │ Candlestick                     │
│     ├───────────────────────────────┼─────────────────────────────────┤
│     │ BTCUSDT · 1h                  │ BTCUSDT · 4h                    │
│     │ Candlestick                   │ Candlestick                     │
└─────┴───────────────────────────────┴─────────────────────────────────┘
```

Primary tasks:

- choose pair;
- change each timeframe independently;
- add/remove overlays;
- inspect realtime state;
- switch layout.

## Screen B — Strategy Builder

Left: strategy library.

Center: selected strategy/composite builder.

Right: parameter/version/explanation drawer.

Bottom optional pane: sample signals preview.

## Screen C — Search Lab

Left 340 px: search configuration.

Center: run progress + live candidate feed.

Right 360 px: current Top-K compact leaderboard.

Bottom: workers/queue health strip.

## Screen D — Backtest Detail

Top: identity + metric strip.

Main left: market chart with selected strategy signals/trades.

Main right: equity/drawdown + strategy explanation.

Bottom: trade table.

Right drawer: provenance.

## Screen E — Leaderboard

Top: scoring policy + filters.

Main: full leaderboard table.

Right context pane: selected strategy detail.

## Screen F — Strategy Visualization

Main: large chart.

Bottom: trade list.

Right: selected strategy members, metrics, provenance shortcuts.

## Screen G — News & Sentiment

Top: filters + sentiment summary.

Main: news table.

Right: article detail + model/version metadata.

## Screen H — Operations

Top: overall health strip.

Main left: dependencies + workers.

Main right: queue metrics + run health.

Bottom: event log.

---

# 14. Required states

Every generated prototype should include explicit examples of these states:

## Loading

- skeleton rows;
- chart placeholder with axes/grid retained where possible;
- no full-screen spinner for a local data refresh.

## Empty

Examples:

- `No backtests yet. Configure a strategy and run your first backtest.`
- `No news found for BTC in this period.`

## No-trade

`Backtest completed with 0 simulated trades. Metrics that require trades are unavailable.`

## Partial

`312 / 500 candles loaded · backfilling missing range…`

## Stale

`Market data stale · last update 18s ago`.

## Reconnecting

Keep the last visible chart but clearly label it as not live.

## Failed result

Show failure reason and retry state. Do not render missing numeric metrics as zero.

## Degraded optional service

`Sentiment unavailable. Market and backtest features remain operational.`

---

# 15. Interaction rules

## Tables

- single click selects;
- double click or `Enter` opens detail only if needed;
- row hover remains subtle;
- selected row persists while detail pane is open;
- filters should be visible and removable;
- preserve sort/filter state when returning from detail.

## Drawers

- width 360–420 px;
- support `Esc` close;
- never cover a critical chart marker when possible; shrink workspace using split pane for high-value details.

## Toasts

Use only for action confirmation and non-blocking failures:

- `Search started — 2,000 candidate limit`.
- `Strategy v3 registered`.
- `Realtime connection restored`.

Persistent issues belong inline in the affected panel.

## Confirmation dialogs

Use for:

- stopping a running search/continuous loop if it changes job behavior;
- deleting a draft/config if prototype includes deletion.

Avoid confirmations for harmless navigation.

---

# 16. Accessibility and readability

- Minimum text contrast should target WCAG AA.
- Never encode BUY/SELL or positive/negative by color alone.
- Use tabular numerals for columns.
- Keep hit targets at least 28–32 px in dense desktop toolbars; primary actions 36 px+.
- Visible focus rings on keyboard navigation.
- Tooltip delay around 300–500 ms.
- Do not use tiny text below 11 px.
- Avoid red/green adjacent fills without icons/labels.

---

# 17. Anti “AI-generated dashboard” constraints

Apply these strictly when generating prototypes:

1. No hero section inside the authenticated product.
2. No motivational headline such as “Trade smarter with AI”.
3. No gradient mesh background.
4. No floating glass cards on a giant empty canvas.
5. No default three-card row repeated down every screen.
6. No 16–24 px radius on all surfaces.
7. No random purple accents; use semantic color roles.
8. No decorative crypto coin illustrations.
9. No giant KPI cards when a metric strip communicates the same information.
10. Do not place every control inside a rounded pill.
11. Use 1 px pane dividers and edge-to-edge workspaces.
12. Use compact toolbars and tables where professional terminals do.
13. Charts should occupy meaningful area, not be tiny cards under KPIs.
14. Use realistic labels, IDs, timestamps, error states, progress states, and versions.
15. Maintain layout continuity across screens instead of redesigning the shell per page.
16. Preserve selected pair/timeframe/run context when moving between related pages.
17. Avoid features not present in the product scope just because other crypto terminals have them.

---

# 18. Prototype mock data

Use deterministic mock values so screens feel connected.

## Market

- Pair: `BTCUSDT`
- Provider: `Binance`
- Last price: `63,008.57`
- 24h: `+1.82%`
- Timeframes: `5m`, `15m`, `1h`, `4h`

## Strategies

- `MA Cross v3` — fast 20 / slow 50
- `RSI Reversal v2` — period 14 / buy 30 / sell 70
- `Bollinger Mean Reversion v1` — period 20 / std 2
- `Support Resistance v4` — lookback 120 / tolerance 0.7%
- Composite: `MA + RSI + SR v2`

## Example composite weights

- MA: `0.20`
- RSI: `0.30`
- SR: `0.50`
- BUY threshold: `0.30`
- SELL threshold: `-0.30`

## Leaderboard

| Rank | Strategy | Score | Return | Win Rate | MDD | Trades | Sharpe |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | MA20 + RSI14 + SR | 84.1 | +24.2% | 62% | -7.1% | 81 | 1.56 |
| 2 | MA20 + BB20 | 81.4 | +21.7% | 55% | -8.4% | 105 | 1.42 |
| 3 | RSI14 + SR | 79.8 | +18.4% | 64% | -6.7% | 52 | 1.39 |
| 4 | MA50 | 63.5 | +9.1% | 48% | -14.2% | 140 | 0.82 |

## Search run

- Run: `SR-0184`
- Generator: `Random Search v1`
- Seed: `424242`
- Candidate limit: `2,000`
- Tested: `364`
- Workers: `4/4`
- Failed: `3`
- Retried: `2`
- Current Top-1 score: `84.1`

---

# 19. Ready-to-paste prototype generation prompt

Use the following prompt with Bolt, Lovable, v0, Replit, Claude Code, Codex, or another UI generator.

```text
Build a desktop-first functional prototype named “Crypto Strategy Lab”.

GOAL
Create a professional crypto strategy research terminal for analysis and simulation, not a consumer trading app and not a real-money trading terminal. The interface must support realtime charts, strategy construction, strategy search, backtesting, ranking, visualization, news/sentiment, and operational health.

VISUAL DIRECTION
Use a dark, dense, professional research-terminal aesthetic inspired by the interaction grammar of TradingView and modern crypto analytics dashboards, but do not copy their branding or exact layouts.

The interface must NOT look like a generic AI-generated SaaS dashboard:
- no hero sections;
- no giant gradient backgrounds;
- no glassmorphism everywhere;
- no repeated 3-card grids;
- no huge rounded cards;
- no decorative crypto illustrations;
- no excessive purple;
- no giant empty padding.

Use edge-to-edge analytical workspaces, 1px panel separators, compact toolbars, resizable split panes, dense tables, tabular/monospace numerals, and restrained semantic colors.

FOUNDATION TOKENS
Canvas #0B0E13
Workspace #0E1218
Surface #131820
Hover #181F29
Active #1D2632
Border subtle #202936
Border default #2B3543
Text primary #E7ECF3
Text secondary #9AA7B6
Text muted #687586
Primary accent #4F7CFF
Positive / BUY #21C58B
Negative / SELL #F05B64
Warning / stale #E6B94A
Info #59A8FF
Neutral / HOLD #8894A3
Purple only for search/ML #A78BFA
Chart grid #1B2430

Typography: Inter/Geist for UI and JetBrains Mono/IBM Plex Mono for market values, IDs, timestamps and metrics.
Spacing: 4px base scale.
Radii: 3/5/8/10px. Avoid pill-heavy design.

APP SHELL
- 48px top bar.
- left navigation rail, 52px collapsed / about 184px expanded.
- navigation: Market, Strategies, Search Lab, Backtests, Leaderboard, News & Sentiment, Operations.
- optional 360–420px right context drawer.
- primary desktop frame: 1440x900.

TOP BAR
Include product name, BTCUSDT pair selector, global search/command trigger, realtime connection state, and last-sync metadata.

SCREEN 1 — MARKET LAB
Create a chart-first page that supports 1–4 charts. Default to a 2x2 layout with BTCUSDT timeframes 5m, 15m, 1h and 4h. Each chart must have independent timeframe controls.
Each chart contains candlesticks, volume, compact overlay legend, chart toolbar, pair/timeframe label and explicit Live/Reconnecting/Stale/Error state.
Provide overlay controls for MA, RSI, Bollinger Bands and Support/Resistance.
Show BUY/SELL and Entry/Exit markers.
Use split-pane borders, not four floating rounded cards.

SCREEN 2 — STRATEGY BUILDER
Left pane: strategy library with MA, RSI, Bollinger and Support/Resistance, including strategy version and parameter summary.
Center: strategy configuration or composite builder.
Composite modes: Majority Vote and Weighted Combination.
Use MA weight .20, RSI .30, SR .50, buy threshold .30 and sell threshold -.30 as default mock data.
Right drawer: parameters, validation, version metadata and “Explain decision”.

SCREEN 3 — SEARCH LAB
Left configuration pane: strategy types, parameter ranges, combination size, candidate limit, Random Search generator, seed, dataset and stop condition.
Center: running search SR-0184 with progress 364/2000 candidates and a live candidate event feed.
Right: compact live Top-K leaderboard.
Bottom strip: Workers 4/4, Queue 218, Failed 3, Retried 2, Throughput 6.8 jobs/s, Top-1 84.1.
Use subtle realtime row updates, not flashy animation.

SCREEN 4 — BACKTEST DETAIL
Top identity row: strategy, version, pair, timeframe, date range, dataset version and run status.
Metric strip: Return, Win Rate, Max Drawdown, Trades, Sharpe.
Main left: BTCUSDT candlestick chart with strategy overlays, BUY/SELL, Entry/Exit.
Main right: equity curve and drawdown.
Bottom: trade table.
Right drawer: provenance containing strategy version, parameters, dataset, generator, seed, scoring policy and execution configuration.

SCREEN 5 — LEADERBOARD
Full dense table with columns Rank, Strategy, Score, Return, Win Rate, MDD, Trades, Sharpe, Updated.
Default sample rows:
1 MA20 + RSI14 + SR | 84.1 | +24.2% | 62% | -7.1% | 81 | 1.56
2 MA20 + BB20 | 81.4 | +21.7% | 55% | -8.4% | 105 | 1.42
3 RSI14 + SR | 79.8 | +18.4% | 64% | -6.7% | 52 | 1.39
4 MA50 | 63.5 | +9.1% | 48% | -14.2% | 140 | .82
Clicking a row opens a right detail pane with metrics, members, parameters, and actions Visualize / Open backtest / View provenance.
Leaderboard updates should not refresh the whole page.

SCREEN 6 — NEWS & SENTIMENT
Top filters: coin/pair, source, sentiment and date range.
Compact sentiment distribution.
Main dense news table: Published, Source, Headline, Related coin, Sentiment, Score.
Right pane: article detail and sentiment model/version.
Include a degraded state: “Sentiment unavailable — technical analysis continues.”

SCREEN 7 — OPERATIONS
Health strip plus dependency table for market provider, realtime stream, database, queue, backtest workers, news provider and sentiment service.
Show required vs optional dependencies.
Add worker list, queue metrics and compact event log.

COMPONENT RULES
- table row height about 36px;
- compact controls 28–32px;
- primary actions 36px+;
- sticky table headers;
- status labels: LIVE, RUNNING, QUEUED, COMPLETED, FAILED, DEGRADED, STALE, BUY, SELL, HOLD;
- use text/icon with color, never color alone;
- visible keyboard focus;
- drawers 360–420px;
- local skeleton loading instead of full-page spinners.

REQUIRED STATES
Show at least one example of loading, empty, no-trade, partial data, stale, reconnecting, failed result and degraded optional service.
Do not display missing metrics as zero.

FUNCTIONAL PROTOTYPE BEHAVIOR
Make navigation interactive.
Make chart layout buttons switch among 1, 2 and 4 chart layouts.
Make timeframe controls independently selectable per chart.
Make strategy selection and composite weights editable.
Make Start Search transition to a running state and update progress with deterministic mock values.
Make leaderboard rows selectable and open a detail pane.
Make trade rows highlight a corresponding mock chart interval.
Make news filters update visible mock rows.
Make connection-state control toggle between Live, Reconnecting and Stale for demonstrating UI states.

Do not add wallet, deposit, withdrawal, real order placement, leverage, Buy Crypto, or exchange execution screens.
```

---

# 20. Implementation handoff checklist

- [ ] App shell remains consistent across all screens.
- [ ] 1–4 chart layout works in the prototype.
- [ ] Each chart timeframe changes independently.
- [ ] Connection state is visible per relevant workspace.
- [ ] Built-in strategies and versions are visible.
- [ ] Composite strategy supports majority and weighted modes.
- [ ] Search config includes Random Search, seed, limit, and stop condition.
- [ ] Search progress and Top-K update without page refresh.
- [ ] Backtest detail includes Return, Win Rate, MDD, Trades, and provenance.
- [ ] Leaderboard supports sort/filter/drill-down.
- [ ] Strategy visualization includes signals and Entry/Exit.
- [ ] News and sentiment can degrade independently.
- [ ] Operations page exposes stream/worker/queue health.
- [ ] Empty, stale, reconnecting, failed, no-trade, and partial states are designed.
- [ ] No real-money trading controls appear in the MVP.
- [ ] No generic AI-SaaS visual patterns dominate the interface.

