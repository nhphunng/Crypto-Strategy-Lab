# MASTER PROMPT — CRYPTO STRATEGY LAB PROTOTYPE

You are building a high-fidelity, functional desktop prototype for **Crypto Strategy Lab**.

Before writing code, read these project files completely:

1. `CRYPTO_STRATEGY_LAB_UI_KIT.md`
2. `design-tokens.json`
3. `SRS.md`
4. `REQUIREMENT.md`

Treat them as the source of truth.

Priority when requirements conflict:

1. `SRS.md` and `REQUIREMENT.md` define product scope and behavior.
2. `CRYPTO_STRATEGY_LAB_UI_KIT.md` defines UX/UI direction, screen structure, components, states, and interaction patterns.
3. `design-tokens.json` defines visual tokens.

Do not redesign the product from scratch.

Do not blindly imitate TradingView, Binance, CoinGlass, or CoinMarketCap. Use the professional interaction grammar of crypto analysis products while preserving a distinct Crypto Strategy Lab identity.

---

# 1. PRODUCT GOAL

Build a professional research workspace where users can:

* monitor realtime and historical crypto market data;
* view up to four candlestick charts simultaneously;
* analyze different timeframes independently;
* configure technical strategies;
* combine strategies;
* run historical backtests;
* automatically search candidate strategy combinations;
* compare strategies using quantitative metrics;
* inspect simulated trades and signals;
* rank strategies through a Top-K leaderboard;
* review crypto news and sentiment;
* monitor continuous strategy-search loops and backend-style operational health.

This application is a **research, analysis, simulation, and experimentation platform**.

It is NOT a real-money exchange.

Never add:

* wallet;
* portfolio balance;
* deposit;
* withdrawal;
* Buy Crypto;
* order ticket;
* market/limit order form;
* leverage;
* futures execution;
* real order book;
* exchange account balance;
* copy trading;
* PnL from real trading.

Backtest trades are simulated trades only.

---

# 2. PROTOTYPE SCOPE

Build exactly **7 top-level screens/routes**:

1. Landing
2. Market
3. Strategies
4. Backtests
5. Leaderboard
6. News & Sentiment
7. Operations

Do not create additional top-level routes.

Use:

* drawers;
* split panes;
* tabs;
* popovers;
* expandable rows;
* contextual inspectors;
* modals

for secondary interactions.

Specifically, DO NOT create separate routes for:

* Login / Register
* Strategy Detail
* Edit Strategy
* Composite Detail
* Plugin Management
* Search Lab
* Backtest Detail
* Strategy Visualization
* News Detail
* Trade Detail
* Settings
* Wallet
* Portfolio
* Order Book

---

# 3. VISUAL DIRECTION

The application should feel like a **professional quantitative research terminal**, not a generic SaaS dashboard.

Keywords:

* analytical;
* dense;
* calm;
* precise;
* professional;
* realtime;
* technical;
* modular.

Use a **dark-first interface**.

## Core colors

* Canvas: `#0B0E13`
* Workspace: `#0E1218`
* Surface: `#131820`
* Surface hover: `#181F29`
* Surface active: `#1D2632`
* Subtle border: `#202936`
* Default border: `#2B3543`
* Primary text: `#E7ECF3`
* Secondary text: `#9AA7B6`
* Muted text: `#687586`

### Primary product accent

`#4F7CFF`

Use blue for:

* selected navigation;
* active tabs;
* primary actions;
* selected controls;
* focus states.

Do NOT use blue to represent financial profit.

### Semantic colors

Positive / BUY / healthy:

`#21C58B`

Negative / SELL / failed:

`#F05B64`

Warning / stale / degraded:

`#E6B94A`

Information:

`#59A8FF`

Neutral / HOLD:

`#8894A3`

Search/ML special accent:

`#A78BFA`

Use purple sparingly.

---

# 4. TYPOGRAPHY

Use:

* `Inter`, `Geist`, or system sans-serif for interface text;
* `JetBrains Mono`, `IBM Plex Mono`, or equivalent monospace for:

  * prices;
  * percentages;
  * timestamps;
  * Strategy IDs;
  * Run IDs;
  * Job IDs;
  * versions;
  * parameters;
  * metrics.

Keep application typography compact.

Suggested:

* Landing hero: 40/48 semibold
* App page title: 20px
* Panel title: 16px
* Body: 14px
* Metadata: 12px
* Micro labels: 11px

Never create huge 48–72px dashboard headings inside the product.

---

# 5. LAYOUT SYSTEM

Primary desktop target:

`1440 × 900`

Desktop-first.

The product itself does not need to be mobile-first because multi-chart analysis requires horizontal space.

Use:

* compact 48px app top bar;
* collapsible left navigation;
* 1px pane separators;
* sticky toolbars;
* sticky table headers;
* resizable split panes where appropriate;
* 360–420px contextual right drawer.

Default app navigation:

* Market
* Strategies
* Backtests
* Leaderboard
* News & Sentiment
* Operations

Maintain the same application shell across all six product screens.

Do not redesign navigation from page to page.

---

# 6. ANTI AI-GENERATED DESIGN RULES

Follow these strictly.

DO NOT produce:

* gradient mesh backgrounds;
* neon crypto backgrounds;
* glassmorphism everywhere;
* giant floating cards;
* repeated rows of three feature cards;
* 20–30px corner radii everywhere;
* giant KPI cards;
* excessive shadows;
* decorative Bitcoin/Ethereum coin illustrations;
* random purple gradients;
* huge empty spaces;
* pill-shaped controls everywhere;
* generic “AI-powered trading” visual language;
* motivational headlines such as “Trade Smarter with AI”.

Inside the product, prefer:

* data tables;
* split panes;
* compact toolbars;
* metric strips;
* charts;
* contextual drawers;
* thin borders;
* precise alignment.

Charts should occupy meaningful screen space.

Do not put a tiny chart under six giant metric cards.

---

# 7. GLOBAL PRODUCT STATE

Use connected deterministic mock data throughout the entire prototype.

The screens must feel like parts of the same active experiment.

Default market:

`BTCUSDT`

Provider:

`Binance`

Current price:

`63,008.57`

24h:

`+1.82%`

Default chart timeframes:

* 5m
* 15m
* 1h
* 4h

Current best strategy:

`MA20 + RSI14 + SR`

Score:

`84.1`

Current search run:

`SR-0184`

Generator:

`Random Search v1`

Seed:

`424242`

Candidate limit:

`2,000`

Candidates tested:

`364`

Workers:

`4/4`

Failed:

`3`

Retried:

`2`

---

# 8. SCREEN 01 — LANDING PAGE

## Purpose

Introduce Crypto Strategy Lab clearly before the user enters the analytical workspace.

This is the only screen allowed to behave like a marketing/product page.

Still keep it restrained and technical.

## Navigation

Top navigation height approximately 64px.

Left:

`CSL`
`Crypto Strategy Lab`

Center/right anchors:

* Product
* Workflow
* Capabilities

Actions:

* View Demo
* Open Strategy Lab

No Login or Register.

`Open Strategy Lab` must route directly to `/market`.

---

## Hero

Use a two-column layout.

### Left

Eyebrow:

`Crypto Strategy Research & Simulation`

Headline:

`Research crypto strategies with reproducible evidence.`

Supporting text:

`Build, backtest, compare and continuously improve strategies using realtime market data — without placing real trades.`

Primary CTA:

`Open Strategy Lab`

Secondary CTA:

`View Workflow`

Add one small trust/status line such as:

`Realtime market data · Deterministic backtests · Versioned experiments`

Do not mention guaranteed returns.

---

## Hero product preview

The right side should be a **realistic preview of the actual application**, not an illustration.

Combine:

* two small candlestick charts;
* compact BTCUSDT header;
* Search Run `SR-0184`;
* progress `364 / 2,000`;
* compact Top-K table;
* Top-1 `MA20 + RSI14 + SR`;
* Score `84.1`.

It should look like a crop from the actual product.

---

## Workflow section

Show:

`Analyze → Build → Backtest → Rank → Improve`

Each step gets:

* one small icon;
* title;
* one-line explanation.

Avoid five giant cards.

Prefer a connected horizontal workflow.

---

## Capability section

Present six product capabilities:

### Multi-Timeframe Market

Analyze up to four independent crypto timeframes.

### Strategy Builder

Configure MA, RSI, Bollinger Bands, Support/Resistance, and composite strategies.

### Backtesting & Search

Test strategies historically and automatically generate candidate combinations.

### Strategy Ranking

Compare candidate performance through quantitative metrics and Top-K ranking.

### News & Sentiment

Connect market news with model-generated sentiment signals.

### Operations

Monitor workers, queue, search loops, retries, and service health.

Use editorial alternating sections or compact rows rather than a generic card grid.

---

## Credibility strip

Display:

* Realtime Data
* Deterministic Backtests
* Versioned Strategies
* Reproducible Results

Finish with:

`Ready to test a strategy?`

Button:

`Open Strategy Lab`

---

# 9. SCREEN 02 — MARKET / MULTI-TIMEFRAME DASHBOARD

## Purpose

This is the main market-analysis workspace.

The chart is the dominant element.

Do not reproduce TradingView's full UI.

Only implement controls relevant to Crypto Strategy Lab.

---

## Header toolbar

Show:

`BTC / USDT`

Provider:

`Binance`

Price:

`63,008.57`

Change:

`+1.82%`

Realtime badge:

`LIVE`

Last sync:

`2s ago`

Controls:

* pair selector;
* date/range selector;
* chart layout 1 / 2 / 4;
* synchronize crosshair toggle if useful;
* indicators;
* refresh/reconnect;
* fullscreen workspace.

---

## Default layout

Use four chart panes in a 2×2 grid:

Top left:

`BTCUSDT · 5m`

Top right:

`BTCUSDT · 15m`

Bottom left:

`BTCUSDT · 1h`

Bottom right:

`BTCUSDT · 4h`

Do not render them as four independent floating cards.

Use one workspace divided by 1px borders.

---

## Every chart pane must contain

* candlestick chart;
* volume;
* OHLC information;
* current price;
* timeframe selector;
* compact toolbar;
* crosshair;
* timestamp axis;
* price axis;
* active indicator legend;
* realtime state.

Provide states:

* LIVE
* RECONNECTING
* STALE
* ERROR

---

## Indicators

Support:

* Moving Average
* RSI
* Bollinger Bands
* Support / Resistance

Indicator configuration opens through a popover or right drawer.

Do not create an Indicator page.

---

## Signals

Display sample markers:

* BUY
* SELL
* Entry
* Exit

Do not rely only on green/red.

BUY should use:

* icon/arrow;
* BUY label;
* semantic positive color.

SELL should use:

* icon/arrow;
* SELL label;
* semantic negative color.

---

## Interactions

Implement:

* switch 1 / 2 / 4 chart layouts;
* independently change the timeframe of each chart;
* enable/disable overlays;
* clicking indicator legend opens settings;
* change connection state among LIVE / RECONNECTING / STALE for demo;
* chart panes retain their individual state when another pane changes.

Changing Chart 1 from 5m to 1h must not reload the other three chart panes.

---

# 10. SCREEN 03 — STRATEGIES

## Purpose

Allow analysts to configure built-in strategies and build composite strategies.

Use a three-area workspace.

---

## Left pane — Strategy Library

Width approximately 260–300px.

Group strategies by type.

### Trend

`MA Cross v3`

Parameters summary:

`20 / 50`

### Momentum

`RSI Reversal v2`

Summary:

`14 · 30 / 70`

### Volatility

`Bollinger Mean Reversion v1`

Summary:

`20 · σ2`

### Structure

`Support Resistance v4`

Summary:

`120 · 0.7%`

Optional registered strategies may appear below.

Each list row should show:

* strategy name;
* version;
* category;
* compact parameter summary;
* active/valid status.

---

## Center — Strategy Configuration

When `MA Cross v3` is selected, show:

Strategy:

`MA Cross`

Version:

`v3`

Parameters:

Fast MA
`20`

Slow MA
`50`

Signal rules:

`MA20 crosses above MA50 → BUY`

`MA20 crosses below MA50 → SELL`

Show parameter validation.

Invalid values should produce field-level errors before the strategy can be used.

Actions:

* Reset
* Run Backtest
* Create New Version

---

## Composite Strategy Builder

Provide switch/action:

`Create Composite Strategy`

Member strategies:

* MA Cross v3
* RSI Reversal v2
* Support Resistance v4

Combination methods:

* Majority Vote
* Weighted Combination

Default weighted configuration:

MA:

`0.20`

RSI:

`0.30`

Support/Resistance:

`0.50`

BUY threshold:

`0.30`

SELL threshold:

`-0.30`

Show a live decision preview such as:

MA → BUY
RSI → SELL
SR → BUY

Weighted score:

`0.40`

Final decision:

`BUY`

This should communicate explainability.

---

## Right drawer — Strategy Inspector

Show:

* parameter schema;
* valid ranges;
* member versions;
* strategy version;
* created timestamp;
* signal explanation;
* composite decision trace;
* immutable version warning.

Action:

`Save as MA + RSI + SR v3`

Do not overwrite historical versions.

---

# 11. SCREEN 04 — BACKTESTS / EXPERIMENT LAB

## Purpose

This screen combines:

* manual backtesting;
* automated Strategy Search;
* run history.

Do not create separate Search Lab or Backtest Detail screens.

Use exactly these tabs:

`Single Backtest`
`Strategy Search`
`Runs`

---

## TAB A — SINGLE BACKTEST

### Configuration toolbar/panel

Strategy:

`MA + RSI + SR v2`

Pair:

`BTCUSDT`

Timeframe:

`15m`

Historical range:

`2026-01-01 → 2026-07-01`

Dataset:

`BINANCE-BTCUSDT-15M-2026H1`

Initial capital:

`$10,000`

Execution configuration can include reasonable simulation values such as:

* fee;
* slippage;
* position size.

Do not add real exchange order execution.

Primary action:

`Run Backtest`

---

## Results

Use a compact metric strip, not giant KPI cards:

Return:

`+24.2%`

Win Rate:

`62%`

Max Drawdown:

`-7.1%`

Trades:

`81`

Sharpe:

`1.56`

Below the strip:

### Main backtest chart

Candlestick chart showing:

* strategy overlays;
* BUY;
* SELL;
* Entry;
* Exit.

### Secondary analytical visualization

Allow tabs or compact stacked panels:

* Equity Curve
* Drawdown

### Simulated trade table

Columns:

* #
* Entry Time
* Side
* Entry Price
* Exit Time
* Exit Price
* P/L
* Result

Clicking a trade should highlight the relevant interval on the chart.

---

## Provenance

Open in a right drawer.

Show:

* Strategy Definition
* Strategy Version
* Parameters
* Dataset
* Dataset range
* Generator if applicable
* Seed
* Execution configuration
* Scoring Policy
* Backtest Run ID
* Timestamp

This is important for reproducibility.

---

## TAB B — STRATEGY SEARCH

Use a three-column analytical workspace.

### Left — Search Configuration

Width approximately 340px.

Fields:

Generator:

`Random Search v1`

Available strategies:

* MA
* RSI
* Bollinger
* Support / Resistance

Parameter ranges.

Combination size:

`2 – 4`

Candidate limit:

`2,000`

Seed:

`424242`

Dataset:

`BTCUSDT · 15m · 2026 H1`

Workers:

`4`

Stop condition:

`Candidate limit reached`

Primary action:

`Start Search`

---

### Center — Search Run

Show:

`SR-0184`

Status:

`RUNNING`

Progress:

`364 / 2,000`

Progress bar.

Display:

* elapsed time;
* estimated remaining candidate count;
* generated candidates;
* completed;
* queued;
* running;
* failed;
* retried.

Include a live candidate feed:

`#0362 · MA20 + RSI14 · Score 76.8`

`#0363 · RSI14 + SR · Score 79.8`

`#0364 · MA20 + RSI14 + SR · Score 84.1 · NEW TOP`

Purple may be used sparingly for generated candidate/search-specific metadata.

---

### Right — Live Top-K

Compact table:

1. MA20 + RSI14 + SR — 84.1
2. MA20 + BB20 — 81.4
3. RSI14 + SR — 79.8
4. MA50 — 63.5

Leaderboard should update without reloading the page.

---

### Bottom health strip

Workers:

`4 / 4`

Queue:

`218`

Failed:

`3`

Retried:

`2`

Throughput:

`6.8 jobs/s`

Top-1:

`84.1`

---

### Start Search interaction

Before click:

status `READY`

After click:

status `RUNNING`

Animate deterministic mock progress rather than random uncontrolled values.

Provide Stop Search.

Stopping an active run should show a confirmation explaining what happens to running jobs.

---

## TAB C — RUNS

Create a dense experiment-history table.

Columns:

* Run ID
* Type
* Strategy / Search Space
* Status
* Started
* Duration
* Tested
* Failed
* Top-1
* Generator
* Seed

Statuses:

* QUEUED
* RUNNING
* COMPLETED
* FAILED
* CANCELLED

Clicking a row opens a right context drawer.

Do not navigate to a new screen.

---

# 12. SCREEN 05 — LEADERBOARD

## Purpose

Rank and compare strategy evaluation results.

This is a table-first screen.

---

## Top controls

Show:

Scoring Policy:

`Balanced v2`

Top-K:

`10`

Filters:

* Strategy type
* Run
* Date range
* Status

Sort options:

* Score
* Return
* Win Rate
* MDD
* Sharpe

Make metric direction obvious:

higher Return = better;

higher Win Rate = better;

higher Sharpe = better;

less severe MDD = better.

---

## Main leaderboard

Columns:

* Rank
* Strategy
* Score
* Return
* Win Rate
* MDD
* Trades
* Sharpe
* Updated

Use mock rows:

1
`MA20 + RSI14 + SR`
Score `84.1`
Return `+24.2%`
Win Rate `62%`
MDD `-7.1%`
Trades `81`
Sharpe `1.56`

2
`MA20 + BB20`
Score `81.4`
Return `+21.7%`
Win Rate `55%`
MDD `-8.4%`
Trades `105`
Sharpe `1.42`

3
`RSI14 + SR`
Score `79.8`
Return `+18.4%`
Win Rate `64%`
MDD `-6.7%`
Trades `52`
Sharpe `1.39`

4
`MA50`
Score `63.5`
Return `+9.1%`
Win Rate `48%`
MDD `-14.2%`
Trades `140`
Sharpe `0.82`

Use sticky headers.

Rows should remain compact.

---

## Result Inspector

Single-click a leaderboard row to select it.

Open a right-side Result Inspector.

Do not navigate to another route.

Tabs:

`Overview`
`Trades`
`Provenance`

### Overview

Show:

* rank;
* overall score;
* Return;
* Win Rate;
* MDD;
* Sharpe;
* number of trades;
* member strategies;
* exact versions;
* parameters;
* strategy decision method.

Include an expanded chart containing:

* candlesticks;
* indicators;
* Support / Resistance;
* BUY;
* SELL;
* Entry;
* Exit.

### Trades

Dense simulated trade table.

Selecting a trade highlights its position on the visualization.

### Provenance

Show:

* Backtest Run;
* Search Run;
* Generator;
* Generator Version;
* Seed;
* Dataset;
* Dataset Version;
* Strategy Versions;
* Scoring Policy;
* Execution Configuration.

Actions:

`Open in Backtests`

`Visualize on Market`

These actions should preserve the selected strategy context.

---

# 13. SCREEN 06 — NEWS & SENTIMENT

## Purpose

Inspect crypto news and ML sentiment without overwhelming technical analysis.

News and sentiment are optional supporting services.

The application must visibly degrade gracefully if they fail.

---

## Top filter bar

Filters:

Coin / Pair:

`BTC`

Source:

`All`

Sentiment:

`All`

Range:

`7D`

Allow filters to update the visible mock news.

---

## Sentiment summary

Use a compact horizontal summary.

Positive:

`47%`

Neutral:

`32%`

Negative:

`21%`

Optionally include a small sentiment trend visualization.

Do not create giant sentiment cards.

---

## News table

Columns:

* Published
* Source
* Headline
* Related Coin
* Sentiment
* Score

Example:

`12 min ago`
`CoinDesk`
`Bitcoin gains as institutional inflows accelerate`
`BTC`
`POSITIVE`
`0.84`

Second example:

`1h ago`
`Reuters`
`Crypto markets face renewed macro volatility`
`BTC`
`NEGATIVE`
`0.71`

Include neutral examples.

---

## Article drawer

Clicking a row opens a right drawer.

Show:

* headline;
* source;
* published timestamp;
* related coin;
* article excerpt;
* sentiment label;
* sentiment score;
* model version;
* analyzed timestamp.

Example:

Model:

`FinSent-v2.3`

Analyzed:

`18:24:12`

No separate News Detail route.

---

## Degraded state

Provide a controllable demo state:

`Sentiment unavailable — technical analysis continues.`

Clearly show that:

* Market remains available;
* Backtests remain available;
* technical strategies continue to work.

Use warning color and icon.

Do not show a full-app error screen.

---

# 14. SCREEN 07 — OPERATIONS / CONTINUOUS LOOP

## Purpose

Demonstrate the architectural side of the project:

* continuous strategy generation;
* distributed jobs;
* worker status;
* queue health;
* retry behavior;
* dependency health;
* observability.

This screen should look like an engineering operations console integrated into the product.

---

## Top section — Continuous Strategy Loop

Title:

`Continuous Strategy Loop`

Status:

`RUNNING`

Control:

`Stop Loop`

Show pipeline:

`Generate → Backtest → Evaluate → Rank → Improve`

Each stage should show an active/healthy state.

Metrics:

Candidates Tested:

`1,842`

Elapsed:

`01:27:43`

Current Top Strategy:

`MA20 + RSI14 + SR`

Score:

`86.4`

Failures:

`7`

Retries:

`5`

---

## Dependency health

Show:

Market Data Provider
`HEALTHY`

Realtime Stream
`CONNECTED`

Database
`HEALTHY`

Queue
`HEALTHY`

Backtest Service
`HEALTHY`

News Provider
`DEGRADED`

Sentiment Service
`HEALTHY`

Clearly distinguish:

* required dependency;
* optional dependency.

News failure must not imply the technical pipeline has stopped.

---

## Worker panel

Show:

Worker 01
`RUNNING`
Job `BT-1842`

Worker 02
`RUNNING`
Job `BT-1843`

Worker 03
`IDLE`

Worker 04
`RUNNING`
Job `BT-1844`

Include utilization.

---

## Queue panel

Metrics:

Queue depth:

`27`

Oldest job:

`12s`

Running:

`3`

Retrying:

`1`

Failed:

`2`

Processing rate:

`6.8 jobs/s`

---

## Active run health

Show:

Run:

`SR-0184`

Generator:

`Random Search v1`

Candidates:

`1,842 / 2,000`

Top-1:

`86.4`

Failures:

`7`

Retries:

`5`

---

## Event log

Bottom section should be a dense monospace event timeline.

Examples:

`18:22:14  BacktestCompleted   BT-1841   Score 81.7`

`18:22:16  StrategyEvaluated  CS-0844   Score 86.4`

`18:22:16  LeaderboardUpdated Rank #1`

`18:22:19  NewsProvider       DEGRADED   retrying`

`18:22:22  BacktestStarted    BT-1844   Worker-04`

Filters:

* Market
* Search
* Backtest
* Ranking
* News
* Sentiment

---

## Loop interactions

`Start Loop`

changes status to:

`RUNNING`

`Stop Loop`

opens confirmation.

After confirming:

* stop generating new jobs;
* preserve completed results;
* update status visibly.

For the prototype, worker and queue values can update using deterministic mock values.

---

# 15. REQUIRED CROSS-SCREEN FLOW

Implement this complete demonstration journey:

### Step 1

User enters Landing.

### Step 2

User clicks:

`Open Strategy Lab`

Route to Market.

### Step 3

Market loads BTCUSDT with:

* 5m
* 15m
* 1h
* 4h

### Step 4

User goes to Strategies.

Select:

* MA
* RSI
* Support/Resistance

Create:

`MA + RSI + SR v2`

### Step 5

User clicks:

`Run Backtest`

Navigate to Backtests with the selected strategy prefilled.

### Step 6

Single Backtest displays:

* +24.2% Return
* 62% Win Rate
* -7.1% MDD
* 81 Trades
* 1.56 Sharpe

### Step 7

User switches to Strategy Search.

Start:

`SR-0184`

### Step 8

Search progresses and updates Top-K.

### Step 9

User goes to Leaderboard.

Top strategy:

`MA20 + RSI14 + SR`

Score:

`84.1`

### Step 10

User opens Result Inspector.

Inspect:

* chart;
* trades;
* provenance.

### Step 11

`Visualize on Market`

returns to Market while preserving strategy overlay context.

### Step 12

User opens News & Sentiment and inspects BTC sentiment.

### Step 13

User opens Operations and sees the Continuous Strategy Loop, workers, queue, and dependency health.

The product should feel like one connected workflow rather than seven unrelated mock pages.

---

# 16. REQUIRED UI STATES

Implement visible examples of:

## Loading

Use local skeletons.

Do not block the full page because one panel is loading.

## Partial market data

Example:

`312 / 500 candles loaded · backfilling missing range…`

## Stale

Example:

`Market data stale · last update 18s ago`

## Reconnecting

Keep the last chart visible.

Add:

`RECONNECTING`

Do not pretend stale data is live.

## Empty

Examples:

`No backtests yet. Configure a strategy and run your first backtest.`

`No news found for BTC in this period.`

## No Trade

Example:

`Backtest completed with 0 simulated trades. Metrics that require trades are unavailable.`

Never render unavailable values as `0`.

## Failed

Display the actual failed status and a short mock reason.

## Degraded optional service

Example:

`Sentiment unavailable. Market and backtest features remain operational.`

---

# 17. COMPONENT BEHAVIOR

Tables:

* approximately 36px row height;
* sticky header;
* subtle hover;
* selected row state;
* sortable columns where relevant;
* filters stay visible;
* tabular numerals.

Controls:

* compact controls 28–32px;
* primary actions at least 36px;
* visible keyboard focus.

Drawers:

* 360–420px;
* close with Esc;
* preserve selected row while open.

Toasts:

Only for short non-blocking feedback.

Examples:

`Search started — 2,000 candidate limit`

`Strategy v3 registered`

`Realtime connection restored`

Persistent failures belong inside the affected panel, not only inside a toast.

---

# 18. ACCESSIBILITY

Use sufficient contrast.

Never communicate BUY/SELL, profit/loss, healthy/failed, or sentiment only through color.

Pair semantic colors with:

* icons;
* arrows;
* labels;
* shapes.

Keep text at least 11px.

Add visible keyboard focus states.

Use tabular numerals for quantitative columns.

---

# 19. PROTOTYPE IMPLEMENTATION

This should be a **functional prototype**, not a collection of static screenshots.

Use the repository's existing frontend stack if one already exists.

Do not replace the project's established stack merely to implement this prototype.

If the project is greenfield, choose a modern component-based frontend architecture appropriate for a desktop analytical app.

For candlestick charts, use an actual chart implementation if practical instead of drawing fake chart rectangles.

The prototype may use deterministic local mock data.

Backend integration is not required unless the repository already provides suitable APIs.

Prioritize:

1. correct product flow;
2. correct information architecture;
3. working interactions;
4. realistic data states;
5. consistent UI kit;
6. responsive desktop layout;
7. clean reusable components.

Avoid spending implementation effort on features outside the seven-screen scope.

---

# 20. IMPORTANT FUNCTIONAL INTERACTIONS

At minimum, the final prototype must support:

* Landing anchor navigation.
* Landing → Market CTA.
* Working app navigation.
* Collapsible app navigation.
* BTCUSDT pair selector.
* 1 / 2 / 4 chart layout switching.
* Independent timeframe selection for every chart.
* Toggle indicators.
* Live / Reconnecting / Stale demo states.
* Strategy selection.
* Editable strategy parameters.
* Composite Majority Vote mode.
* Composite Weighted mode.
* Editable weights and thresholds.
* Save/version simulation.
* Single Backtest run simulation.
* Backtests tab switching.
* Start Strategy Search.
* Deterministic search progress.
* Stop Search.
* Search Top-K updating.
* Runs row selection.
* Leaderboard sorting/filtering.
* Leaderboard Result Inspector.
* Result Inspector tabs.
* Trade selection → chart highlight.
* `Open in Backtests`.
* `Visualize on Market`.
* News filters.
* News article drawer.
* Sentiment degraded state.
* Continuous Loop Start/Stop.
* Worker/queue metric updates.

---

# 21. FINAL VALIDATION BEFORE COMPLETION

Before considering the prototype complete, verify all of the following.

## Routes

There are exactly 7 top-level screens:

1. Landing
2. Market
3. Strategies
4. Backtests
5. Leaderboard
6. News & Sentiment
7. Operations

No unnecessary routes were created.

## Visual

The interface uses the supplied design tokens.

Primary accent is `#4F7CFF`.

The authenticated application does not look like a generic SaaS dashboard.

Charts and tables dominate analytical screens.

## Market

Supports 1–4 charts.

Each chart has an independent timeframe.

Realtime states are visible.

## Strategies

Includes:

* MA
* RSI
* Bollinger
* Support/Resistance
* versions
* Majority Vote
* Weighted Combination

## Backtests

Includes exactly:

* Single Backtest
* Strategy Search
* Runs

Single Backtest contains:

* Return
* Win Rate
* MDD
* Trades
* Sharpe
* visualization
* trade list
* provenance

Search includes:

* Random Search
* seed
* candidate limit
* workers
* stop condition
* progress
* Top-K

## Leaderboard

Supports:

* dense comparison table;
* sorting;
* filters;
* row drill-down;
* Overview;
* Trades;
* Provenance.

## News

Includes:

* source;
* coin;
* sentiment;
* score;
* model version;
* degraded behavior.

## Operations

Includes:

* Continuous Loop;
* pipeline;
* candidates tested;
* Top-1;
* workers;
* queue;
* retries;
* failures;
* dependency health;
* event log.

## Scope

There is:

* no wallet;
* no portfolio;
* no real order ticket;
* no leverage;
* no deposit;
* no withdrawal;
* no real exchange execution.

---

# 22. EXECUTION INSTRUCTION

Do not stop after creating the Landing Page.

Implement the complete seven-screen prototype.

Start by establishing:

1. global design tokens;
2. app routing;
3. public Landing shell;
4. shared authenticated app shell;
5. reusable analytical components.

Then implement screens in this order:

1. Landing
2. Market
3. Strategies
4. Backtests
5. Leaderboard
6. News & Sentiment
7. Operations

Reuse components and mock data across screens so context stays consistent.

Do not generate disconnected placeholder pages.

Do not replace complex analytical sections with generic cards simply to finish faster.

When a screen needs detail, use the UI patterns defined in `CRYPTO_STRATEGY_LAB_UI_KIT.md`.

The final result should feel like a coherent, production-oriented prototype of **Crypto Strategy Lab**, suitable for demonstrating the project's complete business flow and software architecture.
