Update the existing **Crypto Strategy Lab** prototype.

Do NOT rebuild the application from scratch.

Preserve:

* the current dark research-terminal design system;
* current routes;
* current app shell;
* existing strategy logic;
* existing Backtests / Leaderboard / Operations screens;
* current design tokens.

This task focuses on TWO improvements:

1. Add a clear **coin / market selection experience**.
2. Redesign the **Strategies screen** so a beginner can understand how to select and combine strategies without already knowing technical-analysis terminology.

The existing Strategies screen is too technical and requires too much interpretation before users know what action to take.

---

# PART A — GLOBAL MARKET / COIN SELECTION

## 1. MAKE `BTC / USDT` IN THE TOP BAR INTERACTIVE

The current top bar already displays:

`BTC / USDT`

Turn this into a clickable **Global Market Selector**.

Use:

`BTC / USDT ▼`

Secondary metadata may remain:

`Binance`

Price:

`63,008.57`

24h:

`+1.82%`

Clicking the selector opens a floating market-selection panel.

---

# 2. MARKET SELECTOR PANEL

Create a compact but beginner-friendly selector.

Structure:

```text
SELECT MARKET

Search coin or pair...
[ Bitcoin, BTC, ETH, SOL... ]

WATCHLIST

★ BTC / USDT
  Bitcoin
  63,008.57      +1.82%

★ ETH / USDT
  Ethereum
  3,482.14       +2.14%

☆ SOL / USDT
  Solana
  147.62         -0.61%

☆ BNB / USDT
  BNB
  592.18         +0.94%
```

Each item should display:

* coin icon;
* pair;
* full asset name;
* current price;
* 24h percentage;
* favorite/watchlist star;
* provider if useful.

For beginners, show:

`BTC / USDT`

and below:

`Bitcoin priced in USDT`

Do not display only `BTCUSDT`.

---

# 3. MVP / IMPLEMENTATION SAFETY

If the current backend or prototype only supports BTCUSDT, DO NOT pretend multiple coins are fully operational.

Instead show:

```text
BTC / USDT       Available

ETH / USDT       Coming later
SOL / USDT       Coming later
BNB / USDT       Coming later
```

The UI should still demonstrate that the architecture supports market selection.

Only enable a pair if actual prototype data exists for it.

---

# 4. ADD WATCHLIST TO MARKET SCREEN

Add an optional collapsible Watchlist panel to the Market screen.

Default collapsed or approximately 190–220px wide.

Example:

```text
WATCHLIST                         +

Pair          Price        24h
BTC/USDT      63,008.57    +1.82%
ETH/USDT       3,482.14    +2.14%
SOL/USDT         147.62    -0.61%
```

Clicking an available pair changes the global market context.

Allow:

* favorite/unfavorite;
* search;
* add/remove from watchlist;
* collapse panel.

Do not create a new Watchlist route.

---

# 5. MARKET CONTEXT MUST PERSIST

Selected market should persist across:

Market → Strategies → Backtests → Leaderboard → News & Sentiment.

Example:

If user selects:

`BTC / USDT`

then the Strategies page should show:

`Analyzing BTC / USDT`

and Backtests should automatically prefill:

`BTC / USDT`.

Do NOT make the user choose the same market repeatedly.

---

# PART B — REDESIGN THE STRATEGIES SCREEN

The current Strategies screen is too difficult for beginners because:

* `Configure` and `Composite` are not obvious;
* Strategy Library appears before users understand why they need it;
* technical names dominate;
* versions and parameter values compete with the main task;
* selecting a strategy and combining strategies are visually separated;
* the user cannot immediately understand the required workflow.

Redesign the screen around a clear guided sequence.

---

# 6. NEW STRATEGIES PAGE HIERARCHY

The page should follow this mental model:

```text
1. What market am I analyzing?
2. How do I want to start?
3. Which analysis methods do I want to use?
4. How should they work together?
5. What signal does this configuration produce?
6. Test it.
```

Use these sections:

```text
Strategies

Market Context

Start with a preset
OR
Build your own

Selected Strategies

Combination Method

Decision Preview

Run Backtest
```

Do not overwhelm the user with the parameter editor immediately.

---

# 7. ADD A MARKET CONTEXT BAR TO STRATEGIES

Directly below the Strategies title, show:

```text
ANALYZING

BTC / USDT
Bitcoin priced in USDT

Current timeframe
15m

[ Change Market ]
```

If `Change Market` is clicked, open the same Global Market Selector.

This reinforces:

> “The strategy I am building will be tested on this market.”

Do not make coin selection part of the strategy definition itself.

---

# 8. REPLACE `CONFIGURE / COMPOSITE` WITH CLEARER MODES

The current:

`Configure | Composite`

is too abstract.

Replace it with:

```text
Strategy Type

[ Single Strategy ] [ Combine Strategies ]
```

Use beginner-friendly descriptions underneath.

### Single Strategy

`Use one analysis method at a time.`

### Combine Strategies

`Combine signals from two or more methods.`

Default for first-time users:

`Single Strategy`

If a starter preset with multiple strategies is selected, automatically switch to:

`Combine Strategies`.

---

# 9. KEEP STARTER PRESETS, BUT MAKE THEM CLICKABLE AND ACTIONABLE

Current preset cards are useful but need stronger UX.

Use:

### Trend Starter

`1 strategy`

`Moving Average`

Description:

`A simple way to learn how trend-following signals work.`

Action:

`Use this preset`

---

### Balanced Starter

Badge:

`Recommended`

Strategies:

`Moving Average + RSI`

Description:

`Combines market direction with momentum.`

Action:

`Use this preset`

---

### Multi-Signal Starter

Strategies:

`Moving Average + RSI + Support/Resistance`

Description:

`Combines trend, momentum and market structure.`

Action:

`Use this preset`

When a user clicks a preset:

* populate Selected Strategies;
* choose the correct combination method;
* use recommended parameters;
* scroll/focus to the Selected Strategies section.

Do not require users to manually recreate the preset.

---

# 10. ADD A CLEAR `BUILD YOUR OWN` ENTRY POINT

Next to Starter Presets add:

`Build your own`

Description:

`Choose the analysis methods you want to combine.`

Button:

`Choose Strategies`

This should be visually equal to the presets, not hidden.

---

# 11. REDESIGN STRATEGY LIBRARY

Do not show the Strategy Library as a technical sidebar by default.

Instead use an **Add Strategy drawer / picker**.

Main screen should show selected strategies.

Click:

`+ Add Strategy`

opens:

```text
CHOOSE STRATEGIES

Search strategies...
[ Search by name or purpose ]

Recommended for beginners
────────────────────────────

Moving Average
Trend
Helps identify the overall direction of price.

[ + Add ]

RSI
Momentum
Shows whether recent buying or selling has been unusually strong.

[ + Add ]

Bollinger Bands
Volatility
Shows when price moves unusually far from its recent average.

[ + Add ]

Support / Resistance
Market Structure
Highlights price areas where the market reacted before.

[ + Add ]
```

Show technical names secondary.

For example:

Primary:

`Moving Average`

Secondary:

`MA Cross v3`

Do NOT make `MA Cross v3` the first thing beginners see.

---

# 12. GROUP STRATEGIES BY WHAT THEY HELP ANSWER

Instead of only:

Trend
Momentum
Volatility
Structure

also explain each category.

### Trend

`Which direction is price generally moving?`

### Momentum

`How strong is the recent move?`

### Volatility

`How unusually far is price moving?`

### Market Structure

`Where has price reacted before?`

This helps users understand why they might combine different strategies.

---

# 13. ADD STRATEGY DIRECTLY FROM THE PICKER

Users should be able to add strategies using one click.

Button:

`+ Add`

After selected:

`✓ Added`

Allow removing without closing the drawer.

Footer:

```text
3 strategies selected

[ Cancel ] [ Use Selected Strategies ]
```

Minimum for Composite:

`2 strategies`

If only one selected:

`Choose at least one more strategy to create a composite strategy.`

---

# 14. MAIN SCREEN SHOULD SHOW `SELECTED STRATEGIES`

After selection, show a clear workspace:

```text
SELECTED STRATEGIES                         + Add Strategy

3 methods selected

┌─────────────────────────────────────────────────────────────┐
│ Moving Average                                             │
│ Trend · Detects general market direction                   │
│ MA Cross v3                                      [Remove]   │
├─────────────────────────────────────────────────────────────┤
│ RSI                                                        │
│ Momentum · Measures recent buying/selling strength         │
│ RSI Reversal v2                                  [Remove]   │
├─────────────────────────────────────────────────────────────┤
│ Support / Resistance                                       │
│ Structure · Finds important price areas                    │
│ Support Resistance v4                            [Remove]   │
└─────────────────────────────────────────────────────────────┘
```

Do not expose every parameter yet.

Add:

`Customize parameters`

as a secondary action per strategy.

---

# 15. MOVE PARAMETERS INTO PROGRESSIVE DISCLOSURE

Currently Fast MA and Slow MA dominate the center of the screen.

For beginners, default to recommended values.

Example selected row:

```text
Moving Average

Fast MA 20
Slow MA 50

Recommended setup

[ Customize parameters ]
```

Click `Customize parameters` expands:

```text
Fast MA
[ 20 ]

Slow MA
[ 50 ]

ⓘ Fast MA reacts faster to recent price changes.
ⓘ Slow MA represents the broader trend.

[ Reset to recommended ]
```

Keep technical control available without forcing it initially.

---

# 16. MAKE VERSIONS SECONDARY

Do not remove versioning.

But visually de-emphasize it.

Instead of:

`MA Cross v3`

as the primary title, use:

```text
Moving Average
MA Cross · v3
```

Version should be important in Inspector / Provenance, not the first decision a beginner makes.

---

# 17. COMBINATION METHOD SECTION

Only show this section when 2+ strategies are selected.

Title:

`How should these strategies work together?`

Options:

```text
○ Majority Vote
  Every strategy gets one vote.
  The most common signal becomes the final signal.

○ Weighted
  Give some strategies more influence than others.
```

Default:

`Majority Vote`

Badge:

`Recommended for beginners`

Do not default beginners to Weighted.

---

# 18. MAJORITY VOTE UI

If Majority Vote is selected:

Do NOT show weight sliders.

Show:

```text
MA        BUY
RSI       SELL
Support   BUY

Votes

BUY       2
SELL      1
HOLD      0

Final Signal
BUY

Because 2 of 3 strategies agree on BUY.
```

Add:

```text
Tie behavior
[ HOLD ▼ ]
```

Tooltip:

`What should happen when BUY and SELL receive the same number of votes?`

Default:

`HOLD`

---

# 19. WEIGHTED UI

If Weighted is selected:

Show:

```text
How much influence should each strategy have?

Moving Average
20%
[──────────]

RSI
30%
[──────────────]

Support / Resistance
50%
[────────────────────]
```

Show:

`Total: 100%`

Do not expose raw values such as `0.20` as the primary representation.

Use percentages for beginners.

Technical value may appear underneath:

`0.20`

If total is not 100%:

`Weights must total 100%.`

Provide:

`Balance automatically`

---

# 20. THRESHOLD UI

Do not show only:

`BUY threshold 0.3`

Explain it.

Use:

```text
Signal Thresholds

BUY when score is above
0.30

SELL when score is below
-0.30

Values between these thresholds produce HOLD.
```

Badge:

`Recommended`

Button:

`Reset to recommended`

Add:

`Advanced`

to collapse/hide this section for beginners.

---

# 21. DECISION PREVIEW MUST EXPLAIN THE RESULT

Create a strong teaching component.

Example:

```text
DECISION PREVIEW

What each strategy says

Moving Average       BUY
RSI                  SELL
Support/Resistance   BUY

──────────────────────────

How they combine

Majority Vote
2 BUY · 1 SELL

──────────────────────────

Final Signal

BUY

Two of the three selected strategies currently agree on BUY.
```

For Weighted:

```text
Weighted Score
+0.35

BUY threshold
+0.30

Final Signal
BUY

The score is above the BUY threshold.
```

Users should understand the result without opening documentation.

---

# 22. ADD A SIMPLE PROGRESS INDICATOR

At the top of the main Strategies workspace, use a subtle step indicator:

```text
1 Choose methods  →  2 Configure  →  3 Combine  →  4 Test
```

Current step highlights automatically.

Do not turn this into a wizard that prevents free navigation.

It is only a visual orientation aid.

---

# 23. PRIMARY CTA SHOULD CHANGE WITH USER STATE

Do not always show `Run Backtest`.

Use contextual actions.

No strategy selected:

`Choose a Strategy`

Single selected:

`Test This Strategy`

Multiple selected but no combination configured:

`Choose Combination Method`

Composite ready:

`Run Backtest`

When ready, add summary above CTA:

```text
Ready to test

BTC / USDT
15m

Moving Average + RSI + Support/Resistance
Majority Vote

[ Run Backtest ]
```

---

# 24. `RUN BACKTEST` SHOULD PRESERVE CONTEXT

Clicking Run Backtest should open Backtests with prefilled:

Market:

`BTC / USDT`

Timeframe:

`15m`

Strategy:

`MA + RSI + Support/Resistance`

Combination:

`Majority Vote`

Parameters:
preserved.

Do not ask users to reconfigure everything.

---

# 25. EMPTY STATE

If no strategy selected, the large blank workspace currently feels confusing.

Replace it with:

```text
Build your first strategy

Start with a recommended setup or choose your own analysis methods.

[ Use Balanced Starter ]

or

[ + Choose Strategies ]
```

Include small illustration only if it uses real UI fragments.

Do NOT use decorative AI/crypto art.

---

# 26. INSPECTOR UPDATE

Keep Inspector.

But rename or add helper:

`Strategy Details`

Inside include:

* technical strategy ID;
* version;
* parameters;
* valid ranges;
* signal rules;
* decision trace;
* provenance metadata.

This is where advanced details belong.

The main workspace should focus on building the strategy.

---

# 27. SHOW EXPLANATIONS TOGGLE

Keep the existing:

`Show explanations`

When ON:

* category explanations appear;
* helper text appears;
* recommended values appear;
* beginner explanations appear.

When OFF:

* descriptions collapse;
* strategy rows become denser;
* parameters show technical labels;
* UI becomes closer to professional terminal density.

Do not change functionality.

---

# 28. PROPOSED FINAL STRATEGY SCREEN LAYOUT

Use this general structure:

```text
┌──────────────────────────────────────────────────────────────┐
│ Strategies                                                   │
│ Analyze BTC / USDT · 15m                    [Change Market]  │
│                                                              │
│ 1 Choose methods → 2 Configure → 3 Combine → 4 Test         │
├──────────────────────────────────────────────────────────────┤
│ START QUICKLY                                                │
│                                                              │
│ Trend Starter │ Balanced Starter ✓ │ Multi-Signal │ Custom  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ SELECTED STRATEGIES                      [+ Add Strategy]     │
│                                                              │
│ Moving Average                                              │
│ Trend · Detects market direction                            │
│ Recommended: 20 / 50              [Customize] [Remove]      │
│                                                              │
│ RSI                                                         │
│ Momentum · Detects strong movement                          │
│ Recommended: 14 · 30 / 70         [Customize] [Remove]      │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ HOW SHOULD THEY WORK TOGETHER?                              │
│                                                              │
│ [ Majority Vote · Recommended ] [ Weighted ]                │
│                                                              │
├───────────────────────────────────┬──────────────────────────┤
│ Combination settings              │ Decision Preview         │
│                                   │                          │
│ Tie behavior: HOLD                │ MA       BUY             │
│                                   │ RSI      SELL            │
│                                   │                          │
│                                   │ Final    BUY             │
├───────────────────────────────────┴──────────────────────────┤
│ Ready to test                                               │
│ BTC/USDT · 15m · MA + RSI · Majority Vote                  │
│                                             [Run Backtest]   │
└──────────────────────────────────────────────────────────────┘
```

Avoid a permanent technical Strategy Library sidebar if it makes the workflow harder to understand.

Prefer an `Add Strategy` drawer.

---

# 29. BEGINNER DEMO FLOW

Ensure this flow works smoothly:

### 1

User sees:

`Analyzing BTC / USDT`

### 2

User selects:

`Balanced Starter`

### 3

The system automatically adds:

* Moving Average
* RSI

### 4

Combination defaults to:

`Majority Vote`

### 5

User sees Decision Preview.

### 6

User optionally clicks:

`+ Add Strategy`

and adds:

`Support / Resistance`

### 7

Decision Preview updates.

### 8

User clicks:

`Run Backtest`

### 9

Backtest screen opens with all relevant context already filled.

A beginner should be able to complete this flow without understanding versioning, seeds, indicator mathematics, or architecture.

---

# 30. FINAL UX TEST

Before finishing, test whether a first-time user can answer these questions within 5 seconds:

1. Which coin am I analyzing?
2. How do I change the coin?
3. Which strategies am I using?
4. How do I add another strategy?
5. Why are these strategies being combined?
6. What is the current final signal?
7. Where do I click to test it?

If any answer is unclear, improve the layout.

---

# 31. REQUIRED IMPLEMENTATION CHECKLIST

Confirm:

* BTC/USDT top-bar control is clickable.
* Global Market Selector exists.
* Market selector explains asset names.
* Watchlist exists without adding a new route.
* Unsupported coins are not falsely presented as operational.
* Market selection persists across screens.
* Strategies page shows current market clearly.
* `Configure / Composite` is replaced by `Single Strategy / Combine Strategies`.
* Starter Presets are actionable.
* `Build your own` exists.
* Strategy picker supports search.
* Strategy picker explains purpose in plain language.
* Strategies can be added and removed freely.
* At least 2 strategies are required for Composite.
* Parameters use progressive disclosure.
* Versions are visually secondary.
* Majority Vote is recommended for beginners.
* Majority Vote has configurable Tie Behavior.
* Weighted supports editable influence.
* Weighted total validates to 100%.
* Thresholds are explained.
* Decision Preview explains why a signal was produced.
* CTA changes based on configuration state.
* Run Backtest preserves market + timeframe + strategy configuration.
* Show Explanations toggle still works.
* No unnecessary new route is introduced.
* No real-money trading controls are added.
