# Crypto Strategy Lab — UI Kit v1.1

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
- A restrained public landing page that introduces the product and routes directly into the lab.

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

- oversized hero sections inside the authenticated product; the public landing page may use one restrained hero;
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
9. **Separate marketing from analysis.** The landing page may be more spacious, but once the user enters the lab the UI immediately becomes compact and data-first.

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
| Landing display | 40 / 48 | 650 | Public landing hero only |
| Display | 24 / 32 | 600 | Rare app page heading |
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

This product should not be designed mobile-first because the core job involves multi-chart and data-heavy analysis. The landing page may adapt responsively, but the lab itself remains desktop-first.

## 3.2 Public landing shell

The landing page is the only public/marketing-oriented screen in the prototype.

### Landing top bar — 64 px

Left to right:

1. Product mark: `CSL` + `Crypto Strategy Lab`.
2. Anchor links: `Product`, `Workflow`, `Capabilities`.
3. Secondary action: `View Demo` or `Explore Features`.
4. Primary action: `Open Strategy Lab`.

No login/register flow is required for the MVP prototype.

### Landing layout

- Max content width: 1180–1240 px.
- Use one restrained hero, not a full-screen decorative splash.
- Hero should contain a concise product statement, two CTAs, and a realistic product preview.
- The preview should show a cropped multi-chart/search/leaderboard workspace so visitors understand the product before entering it.
- Below the fold, prefer a workflow strip and capability sections over generic marketing cards.
- Landing surfaces may use slightly more breathing room than the app, but must preserve the same dark palette, typography, borders, and semantic colors.

Recommended sections:

1. Hero + product preview.
2. `Analyze → Build → Backtest → Rank → Improve` workflow.
3. Core capabilities: Multi-timeframe Market, Strategy Builder, Backtesting/Search, Leaderboard, News/Sentiment, Operations.
4. Architecture/credibility strip: realtime data, deterministic backtests, versioned strategies, reproducible results.
5. Final CTA: `Open Strategy Lab`.

Do not add pricing, testimonials, token sale language, portfolio returns, wallet balances, exchange execution, or speculative profit promises.

## 3.3 App shell

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
3. Backtests
4. Leaderboard
5. News & Sentiment
6. Operations

`Strategy Search` is not a standalone navigation page. It lives inside **Backtests / Experiment Lab** as a tab next to Single Backtest and Runs.

The active section uses a subtle filled state and a 2 px accent indicator.

Do not expose provider-internal or worker-internal actions as normal product navigation items.

### Workspace

Use resizable split panes. Prefer separators and nested panes over independent rounded cards.

### Context panel — 320–380 px

Optional right drawer for:

- strategy parameters;
- chart indicator settings;
- leaderboard result details;
- backtest provenance;
- job detail;
- news detail.

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

The prototype uses **7 top-level screens total**: one public landing page and six product screens. Detail views should use tabs, drawers, split panes, expandable rows, and modals instead of adding routes.

## Screen 01 — Landing Page

```text
┌──────────────────────────────────────────────────────────────────────┐
│ CSL  Crypto Strategy Lab     Product  Workflow  Capabilities   [Open]│
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Research crypto strategies                                         │
│  with reproducible evidence.              ┌───────────────────────┐ │
│                                           │ Multi-chart preview   │ │
│  Build, backtest, compare and improve     │ + live Top-K strip    │ │
│  strategies without placing real trades. │ + search progress     │ │
│                                           └───────────────────────┘ │
│  [ Open Strategy Lab ] [ View Workflow ]                            │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│ Analyze → Build → Backtest → Rank → Improve                          │
├──────────────────────────────────────────────────────────────────────┤
│ Capability sections + architecture credibility strip                 │
├──────────────────────────────────────────────────────────────────────┤
│ Ready to test a strategy?                         [ Open Strategy Lab]│
└──────────────────────────────────────────────────────────────────────┘
```

Primary tasks:

- understand what Crypto Strategy Lab does;
- see a realistic preview of the product;
- understand the end-to-end workflow;
- enter the Market screen through `Open Strategy Lab`.

Landing content should state clearly that the platform performs **analysis and simulation only**, not real-money trading.

## Screen 02 — Market / Multi-Timeframe Dashboard

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
- add/remove MA, RSI, Bollinger, and Support/Resistance overlays;
- inspect BUY/SELL and Entry/Exit markers;
- inspect realtime state;
- switch 1/2/4-chart layout.

Use popovers/drawers for indicator settings. Do not create separate indicator screens.

## Screen 03 — Strategies

Left: strategy library with MA, RSI, Bollinger Bands, Support/Resistance, and optional registered strategies.

Center: selected strategy configuration or Composite Strategy builder.

Right drawer: parameter schema, validation, version metadata, signal explanation, and member decision trace.

Composite builder supports:

- Majority Vote;
- Weighted Combination;
- exact member versions;
- weights and thresholds;
- save as a new immutable strategy version.

Do not create standalone Strategy Detail, Edit Strategy, Composite Detail, or Plugin pages.

## Screen 04 — Backtests / Experiment Lab

Use three tabs inside one screen:

`[ Single Backtest ] [ Strategy Search ] [ Runs ]`

### Single Backtest

- strategy/composite selector;
- pair, timeframe, historical date range, dataset;
- execution configuration;
- Run Backtest action;
- result metric strip;
- candlestick visualization with simulated BUY/SELL and Entry/Exit;
- equity/drawdown view;
- trade table;
- provenance drawer.

### Strategy Search

Left 340 px: Random Search configuration with strategy types, parameter ranges, combination size, candidate limit, seed, dataset, worker count, and stop condition.

Center: run progress + live candidate feed.

Right: current Top-K compact leaderboard.

Bottom: worker/queue health strip.

### Runs

Dense history table for search/backtest runs with status, start time, duration, tested candidates, failures, Top-1, and reproducibility metadata.

Selecting a run opens a context drawer instead of a new page.

## Screen 05 — Leaderboard

Top: scoring policy, Top-K setting, filters, sort controls.

Main: full dense leaderboard table.

Clicking a row opens a right **Result Inspector** with tabs:

`[ Overview ] [ Trades ] [ Provenance ]`

The inspector contains:

- metrics and score;
- member strategies and versions;
- parameters;
- large or expanded strategy visualization with overlays/signals;
- simulated trade list;
- dataset/generator/seed/scoring policy provenance;
- actions `Open in Backtests` and `Visualize on Market`.

There is no separate Strategy Visualization route.

## Screen 06 — News & Sentiment

Top: pair/coin, source, sentiment, and date-range filters + sentiment summary.

Main: dense news table.

Right drawer: article detail, related coin, sentiment score, model version, analyzed timestamp.

Include explicit degraded behavior where sentiment/news can fail without blocking Market or technical Backtests.

## Screen 07 — Operations / Continuous Loop

Top: Continuous Strategy Loop control and overall health strip.

Main left: dependencies + workers.

Main right: queue metrics + active run health.

Bottom: compact event log.

Show:

- Start/Stop loop;
- Generate → Backtest → Evaluate → Rank → Improve pipeline;
- candidates tested;
- elapsed duration;
- retries/failures;
- current Top-1;
- worker utilization;
- queue depth;
- market/news/sentiment dependency health.

---

## Screen inventory rule

Do **not** add top-level screens for:

- Login/Register;
- Wallet, Portfolio, Deposit, Withdraw;
- Buy/Sell order ticket or Order Book;
- Strategy Detail/Edit;
- Composite Detail;
- Search Lab as a separate route;
- Backtest Detail as a separate route;
- Strategy Visualization as a separate route;
- News Detail;
- Trade Detail;
- Settings.

Those interactions belong inside the seven screens above through drawers, tabs, modals, and contextual controls.

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

1. No hero section inside the authenticated product. The public Landing Page may use exactly one restrained hero.
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

## Landing

- Eyebrow: `Crypto Strategy Research & Simulation`
- Headline: `Research crypto strategies with reproducible evidence.`
- Supporting copy: `Build, backtest, compare and continuously improve strategies using realtime market data — without placing real trades.`
- Primary CTA: `Open Strategy Lab`
- Secondary CTA: `View Workflow`
- Workflow: `Analyze → Build → Backtest → Rank → Improve`
- Preview pair: `BTCUSDT`
- Preview Top-1: `MA20 + RSI14 + SR · Score 84.1`

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
Create a professional crypto strategy research and simulation product. The prototype has exactly 7 top-level screens: 1 public Landing Page plus 6 product screens. It is not a consumer trading app and not a real-money trading terminal.

The product supports realtime charts, strategy construction, composite strategies, Random Search, historical backtesting, ranking, strategy visualization, news/sentiment, continuous strategy loops, and operational health.

VISUAL DIRECTION
Use a dark, dense, professional research-terminal aesthetic inspired by the interaction grammar of professional charting and crypto analytics products, but do not copy their branding or exact layouts.

The authenticated product must NOT look like a generic AI-generated SaaS dashboard:
- no hero sections inside the app;
- no giant gradient backgrounds;
- no glassmorphism everywhere;
- no repeated 3-card grids;
- no huge rounded cards;
- no decorative crypto illustrations;
- no excessive purple;
- no giant empty padding.

The public Landing Page is the only exception: it may use exactly one restrained hero with a realistic product preview. Do not use token/coin illustrations, price speculation, testimonials, pricing, profit promises, or crypto-casino aesthetics.

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
Landing hero display can use 40/48 semibold. App headings remain compact.
Spacing: 4px base scale.
Radii: 3/5/8/10px. Avoid pill-heavy design.

PUBLIC LANDING SHELL
- 64px top navigation.
- left: CSL + Crypto Strategy Lab.
- anchors: Product, Workflow, Capabilities.
- actions: View Demo and Open Strategy Lab.
- max content width about 1200px.
- CTA Open Strategy Lab routes directly to Market.
- no login/register requirement.

APP SHELL
- 48px top bar.
- left navigation rail, 52px collapsed / about 184px expanded.
- navigation must contain exactly: Market, Strategies, Backtests, Leaderboard, News & Sentiment, Operations.
- DO NOT create Search Lab as a standalone navigation item.
- optional 360–420px right context drawer.
- primary desktop frame: 1440x900.

TOP BAR
Include product name, BTCUSDT pair selector, global search/command trigger, realtime connection state, and last-sync metadata.

SCREEN 01 — LANDING PAGE
Create a restrained product landing page that explains the lab before users enter it.
Hero content:
- eyebrow: “Crypto Strategy Research & Simulation”
- headline: “Research crypto strategies with reproducible evidence.”
- supporting copy: “Build, backtest, compare and continuously improve strategies using realtime market data — without placing real trades.”
- primary CTA: Open Strategy Lab
- secondary CTA: View Workflow
- right side: realistic product preview, not an illustration. Preview should combine a small 2-chart market workspace, a compact search progress strip, and a Top-K leaderboard fragment.

Below hero:
1. Workflow strip: Analyze → Build → Backtest → Rank → Improve.
2. Capability sections for Multi-Timeframe Market, Strategies, Backtests/Search, Leaderboard, News/Sentiment, Operations.
3. Credibility strip: Realtime data, Deterministic backtests, Versioned strategies, Reproducible results.
4. Final CTA: Open Strategy Lab.

The landing page can be more spacious than the app but must use the same design system. Avoid generic marketing card grids; use editorial split sections, product screenshots/previews, thin separators, and concise copy.

SCREEN 02 — MARKET / MULTI-TIMEFRAME DASHBOARD
Create a chart-first page that supports 1–4 charts. Default to a 2x2 layout with BTCUSDT timeframes 5m, 15m, 1h and 4h. Each chart must have independent timeframe controls.
Each chart contains candlesticks, volume, compact overlay legend, chart toolbar, pair/timeframe label and explicit Live/Reconnecting/Stale/Error state.
Provide overlay controls for MA, RSI, Bollinger Bands and Support/Resistance.
Show BUY/SELL and Entry/Exit markers.
Use split-pane borders, not four floating rounded cards.

SCREEN 03 — STRATEGIES
Left pane: strategy library with MA, RSI, Bollinger and Support/Resistance, including strategy version and parameter summary.
Center: selected strategy configuration or composite builder.
Composite modes: Majority Vote and Weighted Combination.
Use MA weight .20, RSI .30, SR .50, buy threshold .30 and sell threshold -.30 as default mock data.
Right drawer: parameters, validation, version metadata and Explain Decision / decision trace.
Allow saving a new immutable strategy version.
Do not create separate Strategy Detail, Edit Strategy, Composite Detail, or Plugin pages.

SCREEN 04 — BACKTESTS / EXPERIMENT LAB
This screen replaces separate Search Lab and Backtest Detail routes.
Use exactly three tabs: Single Backtest, Strategy Search, Runs.

Single Backtest tab:
- strategy/composite selector;
- BTCUSDT, timeframe, historical date range, dataset and execution configuration;
- Run Backtest action;
- metric strip: Return, Win Rate, Max Drawdown, Trades, Sharpe;
- candlestick chart with overlays, BUY/SELL and Entry/Exit;
- equity curve + drawdown;
- simulated trade table;
- provenance drawer with strategy version, parameters, dataset, scoring policy and execution configuration.

Strategy Search tab:
- left configuration pane: strategy types, parameter ranges, combination size, candidate limit, Random Search generator, seed, dataset, worker count and stop condition;
- center: running search SR-0184 with progress 364/2000 candidates and live candidate feed;
- right: compact live Top-K leaderboard;
- bottom strip: Workers 4/4, Queue 218, Failed 3, Retried 2, Throughput 6.8 jobs/s, Top-1 84.1;
- Start Search transitions to running state with deterministic mock progress.

Runs tab:
- dense history table for backtest/search runs;
- columns include Run ID, Type, Strategy/Search Space, Status, Started, Duration, Tested, Failed, Top-1;
- selecting a run opens a context drawer instead of navigating to a new page.

SCREEN 05 — LEADERBOARD
Full dense table with columns Rank, Strategy, Score, Return, Win Rate, MDD, Trades, Sharpe, Updated.
Default sample rows:
1 MA20 + RSI14 + SR | 84.1 | +24.2% | 62% | -7.1% | 81 | 1.56
2 MA20 + BB20 | 81.4 | +21.7% | 55% | -8.4% | 105 | 1.42
3 RSI14 + SR | 79.8 | +18.4% | 64% | -6.7% | 52 | 1.39
4 MA50 | 63.5 | +9.1% | 48% | -14.2% | 140 | .82

Clicking a row opens a right Result Inspector with tabs Overview, Trades, Provenance.
Overview includes metrics, member strategies, parameters, and an expanded chart with signals and Entry/Exit.
Trades shows simulated trades and can highlight the corresponding chart interval.
Provenance shows dataset, strategy versions, generator, seed, scoring policy and execution configuration.
Actions: Open in Backtests and Visualize on Market.
Do not create a standalone Strategy Visualization page.
Leaderboard updates should not refresh the whole page.

SCREEN 06 — NEWS & SENTIMENT
Top filters: coin/pair, source, sentiment and date range.
Compact sentiment distribution.
Main dense news table: Published, Source, Headline, Related coin, Sentiment, Score.
Right pane: article detail and sentiment model/version.
Include a degraded state: “Sentiment unavailable — technical analysis continues.”

SCREEN 07 — OPERATIONS / CONTINUOUS LOOP
Top: continuous loop control plus health strip.
Show pipeline: Generate → Backtest → Evaluate → Rank → Improve.
Show Candidates Tested, elapsed duration, Current Top Strategy and Score.
Main left: dependency health plus worker list.
Main right: queue metrics and active run health.
Bottom: compact event log.
Include market provider, realtime stream, database, queue, backtest workers, news provider and sentiment service.
Show required vs optional dependencies and explicit degraded/failed states.

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
Make Landing Page anchors interactive and make Open Strategy Lab route to Market.
Make app navigation interactive.
Make chart layout buttons switch among 1, 2 and 4 chart layouts.
Make timeframe controls independently selectable per chart.
Make strategy selection and composite weights editable.
Make Backtests tabs switch between Single Backtest, Strategy Search and Runs without page navigation.
Make Start Search transition to a running state and update progress with deterministic mock values.
Make leaderboard rows selectable and open the Result Inspector.
Make trade rows highlight a corresponding mock chart interval.
Make news filters update visible mock rows.
Make connection-state control toggle between Live, Reconnecting and Stale for demonstrating UI states.
Make Continuous Loop Start/Stop change status and worker/queue mock metrics.

SCREEN COUNT CONSTRAINT
Keep exactly 7 top-level screens/routes:
1 Landing
2 Market
3 Strategies
4 Backtests
5 Leaderboard
6 News & Sentiment
7 Operations

Do not add separate routes for Search Lab, Backtest Detail, Strategy Visualization, News Detail, Trade Detail, Settings, Login, Register, Portfolio, Wallet, Order Book, or order placement.

Do not add wallet, deposit, withdrawal, real order placement, leverage, Buy Crypto, or exchange execution screens.
```

---

# 20. Implementation handoff checklist

- [ ] Prototype contains exactly 7 top-level screens: Landing + 6 product screens.
- [ ] Landing page uses one restrained hero and a realistic product preview.
- [ ] `Open Strategy Lab` routes from Landing to Market.
- [ ] App shell remains consistent across all six product screens.
- [ ] App navigation is exactly Market, Strategies, Backtests, Leaderboard, News & Sentiment, Operations.
- [ ] Strategy Search lives inside Backtests as a tab, not a separate route.
- [ ] 1–4 chart layout works in the prototype.
- [ ] Each chart timeframe changes independently.
- [ ] Connection state is visible per relevant workspace.
- [ ] Built-in strategies and versions are visible.
- [ ] Composite strategy supports majority and weighted modes.
- [ ] Backtests has Single Backtest, Strategy Search, and Runs tabs.
- [ ] Search config includes Random Search, seed, limit, workers, and stop condition.
- [ ] Search progress and Top-K update without page refresh.
- [ ] Single Backtest includes Return, Win Rate, MDD, Trades, chart visualization, trade table, and provenance.
- [ ] Leaderboard supports sort/filter/drill-down through a Result Inspector rather than a new route.
- [ ] Strategy visualization includes signals and Entry/Exit inside the Result Inspector or Market.
- [ ] News and sentiment can degrade independently.
- [ ] Operations exposes Continuous Loop, stream/worker/queue/dependency health.
- [ ] Empty, stale, reconnecting, failed, no-trade, and partial states are designed.
- [ ] No separate Login, Wallet, Portfolio, Order Book, Search Lab, Backtest Detail, or Strategy Visualization route exists.
- [ ] No real-money trading controls appear in the MVP.
