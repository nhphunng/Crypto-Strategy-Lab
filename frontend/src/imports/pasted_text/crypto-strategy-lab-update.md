You are updating the existing **Crypto Strategy Lab** prototype.

Do NOT rebuild the product from scratch.

Read and preserve the existing:

* UI kit
* design tokens
* routes
* dark visual system
* 7-screen information architecture
* current prototype interactions

The goal of this update is:

> Make Crypto Strategy Lab understandable and usable for people who are new to crypto, technical analysis, strategies, and backtesting — without turning the product into a simplified consumer app.

Keep the professional research-terminal visual identity.

Use **progressive disclosure**:

* simple and understandable by default;
* advanced controls remain available;
* explain unfamiliar concepts close to where users use them;
* avoid forcing beginners to understand technical terminology before taking an action.

Do not remove professional features.

---

# 1. CORE BEGINNER UX PRINCIPLE

Every important workflow should answer four questions:

1. **What is this?**
2. **Why would I use it?**
3. **What should I choose as a beginner?**
4. **What happens after I click this?**

Use:

* short helper text;
* contextual tooltips;
* examples;
* recommended defaults;
* inline explanations;
* preview states.

Do NOT use:

* long textbook paragraphs;
* modal tutorials every few seconds;
* patronizing language;
* excessive hand-holding.

---

# 2. LANDING PAGE — ADD “HOW TO USE” AS A CORE SECTION

The Landing Page must now teach users how the product works before they enter the lab.

The page structure should become:

1. Hero
2. Quick product preview
3. **How to Use Crypto Strategy Lab**
4. Workflow
5. Core capabilities
6. Beginner glossary
7. Architecture / credibility
8. Final CTA

---

# 3. LANDING HERO UPDATE

Keep:

Eyebrow:
`Crypto Strategy Research & Simulation`

Headline:
`Research crypto strategies with reproducible evidence.`

Supporting copy:

`Build, backtest and compare crypto strategies using market data — without placing real trades.`

Add beginner-oriented secondary line:

`New to crypto analysis? Start with guided presets and learn each step as you go.`

Primary CTA:

`Open Strategy Lab`

Secondary CTA:

`Learn How It Works`

Clicking `Learn How It Works` scrolls to the How to Use section.

Do not add Login/Register.

---

# 4. NEW LANDING SECTION — HOW TO USE CRYPTO STRATEGY LAB

Create a visually important section titled:

`How to use Crypto Strategy Lab`

Supporting text:

`You do not need to build a strategy from scratch. Start with a market, choose a few analysis methods, test them on historical data, then compare the results.`

Present the workflow in **5 connected steps**.

Do not use five giant cards.

Prefer:

* connected timeline;
* horizontal stepper;
* editorial split layout;
* screenshot + explanation pairing.

---

## STEP 1 — CHOOSE A MARKET

Title:

`1. Choose what you want to analyze`

Example:

`BTC / USDT`

Explanation:

`A trading pair compares the price of one asset with another. BTC/USDT shows the price of Bitcoin in USDT.`

Beginner hint:

`For the MVP, start with BTC/USDT.`

Preview:

* Pair selector
* Binance provider
* current price
* Live status

CTA:

`View Market`

---

## STEP 2 — OBSERVE DIFFERENT TIMEFRAMES

Title:

`2. Look at the market from different timeframes`

Show:

`5m · 15m · 1h · 4h`

Explanation:

`A timeframe tells you how much time each candle represents. Short timeframes show more detail; longer timeframes show broader trends.`

Beginner hint:

`Not sure where to start? Use 15m and 1h.`

Preview:

* two candlestick charts;
* timeframe controls.

---

## STEP 3 — CHOOSE STRATEGIES

Title:

`3. Choose how the market should be analyzed`

Show beginner-friendly strategy descriptions:

### Moving Average

`Helps identify the general direction of price.`

### RSI

`Helps identify unusually strong buying or selling.`

### Bollinger Bands

`Shows how far price moves from its recent average.`

### Support / Resistance

`Finds price areas where the market has reacted before.`

Explain:

`You can use one strategy or combine several strategies.`

CTA:

`Explore Strategies`

---

## STEP 4 — BACKTEST

Title:

`4. Test the strategy on historical data`

Explanation:

`A backtest simulates how the strategy would have behaved in the past.`

Clarification:

`Backtest results are simulations. They do not guarantee future performance.`

Show result preview:

Return
`+24.2%`

Win Rate
`62%`

Max Drawdown
`-7.1%`

Trades
`81`

Add one-sentence interpretation:

`This example produced a positive historical return, but it also experienced a 7.1% maximum drawdown.`

CTA:

`See Backtesting`

---

## STEP 5 — COMPARE AND IMPROVE

Title:

`5. Compare strategies and find stronger combinations`

Explanation:

`Crypto Strategy Lab ranks tested strategies using multiple metrics instead of looking only at profit.`

Show:

Top 1
`MA20 + RSI14 + SR`

Score
`84.1`

Explain:

`A higher rank does not mean a guaranteed winner. It means the strategy performed better under the selected historical test conditions.`

CTA:

`View Leaderboard`

---

# 5. ADD BEGINNER GLOSSARY TO LANDING

Create a compact section:

`New to these terms?`

Do not make this a long dictionary.

Use an expandable glossary with 6–8 terms.

Include:

### Trading Pair

`Two assets whose relative price is being analyzed, such as BTC/USDT.`

### Candle

`A summary of price movement during one period of time.`

### Timeframe

`The duration represented by one candle, such as 15 minutes or 1 hour.`

### Strategy

`A set of rules that converts market information into BUY, SELL or HOLD signals.`

### Backtest

`A simulation that applies a strategy to historical data.`

### Win Rate

`The percentage of simulated trades that ended profitably.`

### Maximum Drawdown

`The largest decline from a previous portfolio peak during a simulation.`

### Composite Strategy

`A strategy that combines signals from several other strategies.`

Use:

* accordion;
* tooltip;
* compact expandable rows.

---

# 6. GLOBAL COMPONENT UPDATE — BEGINNER MODE WITHOUT CREATING A NEW APP MODE

Do NOT create a completely separate “Beginner Mode” route.

Instead, improve components globally.

Add a small toggle where useful:

`Show explanations`

Default:

ON for the prototype.

When ON:

* helper descriptions appear;
* unfamiliar metrics show explanations;
* recommended defaults are marked.

When OFF:

* interface becomes more compact.

Store this preference across screens.

---

# 7. TOOLTIP SYSTEM

Create one reusable `LearnTooltip` component.

Use a subtle `?` or info icon.

Example:

`Max Drawdown ⓘ`

Tooltip:

`The largest decline from a previous peak during the backtest. Smaller drawdowns generally indicate lower historical downside risk.`

Tooltip rules:

* maximum about 2–3 sentences;
* plain language first;
* technical detail second if needed;
* no financial advice;
* no guaranteed performance language.

Use this component for:

* pair;
* candle;
* timeframe;
* MA;
* RSI;
* Bollinger;
* Support/Resistance;
* BUY/SELL/HOLD;
* weight;
* threshold;
* Return;
* Win Rate;
* MDD;
* Sharpe;
* seed;
* candidate;
* Random Search;
* sentiment score.

---

# 8. MARKET SCREEN — MAKE PAIR AND TIMEFRAME EASIER TO UNDERSTAND

Keep the professional chart-first layout.

Update the pair selector.

Instead of only:

`BTC / USDT`

Show dropdown item:

`BTC / USDT`

Secondary:
`Bitcoin priced in USDT`

Provider:
`Binance`

For unsupported pairs, do not fake working data.

If MVP currently supports BTCUSDT only, communicate:

`BTC/USDT is currently available in this prototype.`

---

## TIMEFRAME SELECTOR UPDATE

When users open the timeframe selector, group options:

### Short-term

* 1m
* 5m
* 15m

### Medium-term

* 30m
* 1h
* 2h

### Long-term

* 4h
* 1d

Add recommendation:

`New to charts? Start with 15m or 1h.`

Tooltip:

`A 15m candle summarizes 15 minutes of price movement.`

Do not hide other timeframes.

---

# 9. MARKET CHART EMPTY / INITIAL STATE

If no indicator is active, add subtle contextual text above the chart toolbar:

`Add an indicator to understand trend, momentum, volatility or market structure.`

Button:

`Add indicator`

Click opens the existing indicator selector.

---

# 10. INDICATOR SELECTOR UPDATE

Do not show only technical names.

Each item should have:

Name
Category
Plain-language purpose

Example:

### MA — Moving Average

Category:
`Trend`

Description:
`Shows the average price over time to help identify market direction.`

Beginner badge:

`Good starting point`

---

### RSI

Category:
`Momentum`

Description:
`Measures how strongly price has recently moved up or down.`

---

### Bollinger Bands

Category:
`Volatility`

Description:
`Shows when price moves unusually far from its recent average.`

---

### Support / Resistance

Category:
`Market Structure`

Description:
`Highlights areas where price has reacted repeatedly.`

Allow:

`Add`

not:

`Trade`

---

# 11. STRATEGIES SCREEN — ADD BEGINNER GUIDANCE

Keep the three-pane structure.

Add top helper:

`Strategies turn market data into BUY, SELL or HOLD signals.`

Small link:

`How strategies work`

Click opens a compact explanatory popover, not a new page.

---

# 12. STRATEGY LIBRARY COMPONENT UPDATE

Each strategy row should include a one-line purpose.

Example:

`MA Cross v3`

`Trend · Finds changes in market direction`

Parameters:
`20 / 50`

Similarly:

`RSI Reversal v2`

`Momentum · Detects unusually strong price movement`

---

# 13. ADD RECOMMENDED STARTER PRESETS

Do not force beginners to configure every parameter manually.

Add section:

`Starter presets`

Preset A:

### Trend Starter

Strategies:
`MA`

Use case:
`Learn how trend-following signals work.`

Preset B:

### Balanced Starter

Strategies:
`MA + RSI`

Combination:
`Majority Vote`

Use case:
`Combine trend and momentum.`

Preset C:

### Multi-Signal Starter

Strategies:
`MA + RSI + Support/Resistance`

Combination:
`Weighted`

Use case:
`Combine trend, momentum and market structure.`

Mark:

`Recommended for demo`

Preset selection should fill the existing builder.

Users can still edit everything afterward.

---

# 14. COMPOSITE STRATEGY BUILDER UPDATE

Current member strategies must no longer be hard-coded.

Add:

`+ Add Strategy`

Click opens strategy selection popover/drawer.

Example:

`Add Member Strategy`

Search...

Trend
☑ MA Cross v3

Momentum
☑ RSI Reversal v2

Volatility
☐ Bollinger Mean Reversion v1

Structure
☑ Support Resistance v4

Footer:

`3 selected`

`Add Selected`

Each member row must support remove.

---

# 15. EXPLAIN WEIGHTED VS MAJORITY VOTE

The toggle:

`Weighted | Majority Vote`

must include contextual explanation.

When selecting `Majority Vote`, show:

`Each strategy gets one vote. The most common signal becomes the final signal.`

Example:

MA → BUY
RSI → SELL
Support → BUY

Result:

`BUY — 2 of 3 strategies agree`

Add:

`Tie behavior`

Default:
`HOLD`

Options:

* HOLD
* BUY
* SELL

---

When selecting `Weighted`, show:

`Give more influence to strategies you consider more important.`

Each weight field should include:

`Influence`

instead of displaying only a raw number.

Example:

Support Resistance
Weight `0.50`

Helper:

`50% of the weighted decision score`

Display total:

`Total weight: 1.00`

If invalid:

`Weights must total 1.00`

Do not require beginners to understand the equation before editing.

An expandable:

`See calculation`

can reveal:

BUY = +1
HOLD = 0
SELL = -1

and the weighted score equation.

---

# 16. THRESHOLD COMPONENT UPDATE

Current labels:

`BUY threshold`
`SELL threshold`

are too abstract for beginners.

Keep the technical labels but add helper text:

BUY threshold
`Final score required to issue a BUY signal`

SELL threshold
`Final score required to issue a SELL signal`

Recommended defaults:

BUY:
`0.30`

SELL:
`-0.30`

Badge:

`Recommended`

Add:

`Reset to recommended`

---

# 17. DECISION PREVIEW UPDATE

Make Decision Preview one of the strongest teaching components.

Show:

### Signals from members

MA Cross
`BUY`

RSI
`SELL`

Support Resistance
`BUY`

Then:

### How they combine

Weighted Score
`+0.35`

Helper:

`Positive scores lean toward BUY. Negative scores lean toward SELL.`

Then:

### Final signal

`BUY`

Reason:

`The weighted score +0.35 is above the BUY threshold +0.30.`

This teaches the user without requiring documentation.

---

# 18. BACKTEST SCREEN — ADD “WHAT AM I TESTING?” SUMMARY

Before Run Backtest, show a compact plain-language summary.

Example:

`You are testing MA + RSI + Support Resistance on BTC/USDT using 15-minute candles from Jan 1 to Jul 1, 2026.`

Then:

`No real trades will be placed.`

Primary action:

`Run Backtest`

---

# 19. BACKTEST CONFIGURATION — BEGINNER DEFAULTS

Mark recommended fields.

Pair:
`BTC / USDT`

Timeframe:
`15m`
Badge:
`Recommended`

Initial Capital:
`$10,000`

Fees:
use preset/default.

Slippage:
use preset/default.

Add collapsed:

`Advanced execution settings`

Move:

* fees;
* slippage;
* sizing;
* seed

into this section when `Show explanations` is ON.

Keep values accessible.

---

# 20. BACKTEST RESULT METRICS — ADD HUMAN INTERPRETATION

Each metric should include tooltip.

Return:

`+24.2%`

Helper:
`Historical change in simulated portfolio value.`

Win Rate:

`62%`

Helper:
`62 of every 100 simulated trades would have been profitable at this rate.`

Maximum Drawdown:

`-7.1%`

Helper:
`Largest decline from a previous portfolio peak.`

Trades:

`81`

Helper:
`Number of simulated completed trades.`

Sharpe:

`1.56`

Helper:
`Risk-adjusted performance measure. Compare it with other strategies tested under similar conditions.`

Do not label values as:

`Good`
`Bad`
`Safe`
`Best investment`

unless they are explicitly relative to the current comparison.

---

# 21. ADD RESULT SUMMARY COMPONENT

Above the detailed chart, create:

`What happened?`

Example:

`This strategy produced +24.2% simulated return across 81 trades. It won 62% of trades and experienced a maximum drawdown of -7.1%.`

Next line:

`Use the chart and trade history below to understand where these results came from.`

This is descriptive, not investment advice.

---

# 22. LEADERBOARD — ADD METRIC EXPLANATION

Add a small:

`How ranking works`

popover.

Explain:

`Strategies are ranked using the selected scoring policy. The rank combines multiple historical performance metrics rather than profit alone.`

Make column headers tooltips:

Score ⓘ
Return ⓘ
Win Rate ⓘ
MDD ⓘ
Sharpe ⓘ

---

# 23. LEADERBOARD BEGINNER COMPARISON HELP

When a user selects two strategies, optionally provide:

`Compare`

Comparison panel:

Strategy A:
`MA + RSI + SR`

Strategy B:
`MA + Bollinger`

Display:

Return
Win Rate
MDD
Trades
Sharpe

Then a neutral interpretation:

`Strategy A had higher historical return, while Strategy B had a different drawdown profile.`

Do not automatically tell the user which one to invest in.

---

# 24. STRATEGY SEARCH — SIMPLE FIRST

The current Search screen is advanced.

Add two configuration levels:

`Basic`
`Advanced`

Default:

`Basic`

---

## BASIC SEARCH

Show only:

Market:
`BTC / USDT`

Timeframe:
`15m`

Strategies:
☑ MA
☑ RSI
☑ Bollinger
☑ Support/Resistance

Combination size:
`2–4`

Candidates:
`100`

Button:
`Find Strategy Combinations`

Helper:

`The system will generate different combinations, backtest them and rank their results.`

---

## ADVANCED SEARCH

Contains:

* parameter ranges;
* candidate limit;
* Random Search generator;
* seed;
* dataset;
* worker count;
* stop condition.

Do not remove them.

---

# 25. SEARCH PROGRESS UPDATE

Instead of only showing technical queue metrics, split information into:

## Experiment Progress

`36 / 100 combinations tested`

Current best:

`MA + RSI + SR`

Score:

`84.1`

Then smaller advanced system details:

Workers:
`4/4`

Queue:
`18`

Failed:
`1`

Throughput:
`6.8 jobs/s`

Technical infrastructure metrics should remain available, but not dominate the beginner workflow.

---

# 26. NEWS & SENTIMENT — EXPLAIN SENTIMENT

Add helper text:

`Sentiment summarizes whether collected news is generally positive, neutral or negative toward the selected asset.`

Add tooltip:

`Sentiment does not predict price by itself. It is an additional information source that can be combined with technical strategies.`

Display:

Positive
Neutral
Negative

with:

* labels;
* values;
* icons;
* colors.

Never use only color.

---

# 27. OPERATIONS SCREEN — KEEP PROFESSIONAL, DE-EMPHASIZE FOR BEGINNERS

Do not remove Operations.

But visually mark:

`Advanced`

Navigation item can remain:

`Operations`

with subtle subtitle/tooltips:

`System health and continuous strategy search`

At the top add:

`This screen shows how Crypto Strategy Lab processes experiments behind the scenes.`

Keep:

* workers;
* queue;
* retries;
* dependency health;
* event log;
* continuous loop.

Do not simplify architecture away.

---

# 28. EMPTY STATE COMPONENTS

Rewrite empty states so they teach the next action.

Instead of:

`No strategies`

use:

`No strategy selected`

`Choose a strategy from the library or start with a recommended preset.`

Button:

`Use Balanced Starter`

---

Instead of:

`No backtests`

use:

`No backtests yet`

`Run a strategy on historical BTC/USDT data to see simulated performance.`

Button:

`Run First Backtest`

---

Instead of:

`No search runs`

use:

`No strategy searches yet`

`Let the system test multiple strategy combinations automatically.`

Button:

`Start Guided Search`

---

# 29. ERROR STATE COMPONENTS

Errors must explain what happened and what the user can do.

Example:

Bad:

`Invalid configuration`

Better:

`The fast MA must be shorter than the slow MA.`

`Try Fast MA 20 and Slow MA 50.`

Action:

`Use recommended values`

---

Example:

Bad:

`Dataset unavailable`

Better:

`Historical BTC/USDT 15m data could not be loaded.`

Action:

`Retry`

Secondary:

`Choose another timeframe`

---

# 30. ADD BEGINNER “WHY?” PATTERN

Use a small optional link:

`Why?`

Example:

Timeframe:

`15m Recommended   Why?`

Popover:

`15-minute candles provide enough detail to observe signals without being as noisy as very short timeframes.`

Use sparingly.

Recommended places:

* default timeframe;
* starter strategy;
* candidate limit;
* combination method;
* backtest range.

---

# 31. ADD CONTEXT PRESERVATION

When moving through:

Market → Strategies → Backtests → Leaderboard

preserve:

* selected pair;
* timeframe;
* strategy;
* backtest/search run.

Example:

If user selects:

`BTC/USDT · 15m`

then creates:

`MA + RSI + SR`

and clicks:

`Run Backtest`

Backtests should already show:

Market:
`BTC/USDT`

Timeframe:
`15m`

Strategy:
`MA + RSI + SR`

Do not make beginners re-enter context repeatedly.

---

# 32. BEGINNER DEMO FLOW

Create a smooth demo path.

## Landing

User reads How to Use.

Click:

`Open Strategy Lab`

---

## Market

Default:

BTC/USDT

Charts:
15m and 1h prominent.

Show hint:

`Start by observing how BTC behaves across different timeframes.`

---

## Strategies

Highlight:

`Balanced Starter`

MA + RSI

User can add Support/Resistance.

---

## Composite

Default:

Majority Vote

Why?

Because it is easier to understand initially.

Allow changing to:

Weighted

When Weighted is selected, reveal weights and thresholds.

---

## Backtest

Prefill everything.

Show:

`Ready to test`

User clicks:

`Run Backtest`

---

## Result

Show:

`What happened?`

then metrics and chart.

---

## Leaderboard

Show how the result compares with other tested strategies.

---

## Search

Offer:

`Want the system to test combinations automatically?`

Button:

`Start Guided Search`

---

# 33. LANDING “TRY THE FLOW” INTERACTION

Make the How to Use section partially interactive.

When users click steps:

1. Market
2. Timeframes
3. Strategies
4. Backtest
5. Compare

the product preview beside the steps should change.

Example:

Click Step 1:
show pair selector.

Click Step 2:
show multi-chart.

Click Step 3:
show strategy builder.

Click Step 4:
show backtest chart.

Click Step 5:
show leaderboard.

This provides a lightweight walkthrough before entering the app.

---

# 34. SAFETY / PRODUCT WORDING

Always describe the system as:

* analysis;
* research;
* historical simulation;
* strategy experimentation.

Avoid:

* predict guaranteed price;
* guaranteed strategy;
* winning strategy;
* best coin to buy;
* guaranteed profit;
* safe investment.

Use:

`historical performance`

not:

`future performance`

Use:

`signal`

not:

`trade recommendation`

where appropriate.

Use:

`simulated trade`

not:

`trade`

when ambiguity exists.

---

# 35. FINAL DESIGN CHECK

The result should feel:

### For a beginner

“I understand what I am looking at and know what to click next.”

### For an experienced user

“The interface still gives me access to parameters, datasets, weights, thresholds, search settings, metrics, provenance and operations.”

Do not achieve beginner usability by deleting capabilities.

Achieve it through:

* contextual explanation;
* better labels;
* recommended defaults;
* starter presets;
* progressive disclosure;
* connected workflows.

---

# 36. REQUIRED CHANGES CHECKLIST

Before finishing, confirm:

* Landing contains a complete How to Use section.
* How to Use contains 5 connected steps.
* Landing preview changes by selected workflow step.
* Beginner glossary exists.
* Pair selector explains BTC/USDT.
* Timeframes have plain-language explanations.
* Indicators have descriptions.
* Starter strategy presets exist.
* Composite members can be added/removed.
* Majority Vote explains votes.
* Majority Vote supports Tie behavior.
* Weighted explains weights.
* Thresholds have plain-language helper text.
* Decision Preview explains why the final signal was produced.
* Backtest shows a plain-language test summary.
* Advanced execution settings are progressively disclosed.
* Result metrics include explanations.
* Backtest contains a “What happened?” summary.
* Leaderboard metrics have tooltips.
* Strategy Search has Basic and Advanced configuration.
* Search progress prioritizes experiment progress over infrastructure metrics.
* Sentiment is explained.
* Operations remains available as an advanced screen.
* Empty states teach the next action.
* Error states suggest recovery.
* Selected pair/timeframe/strategy context persists across screens.
* No real-money trading controls were added.
* Existing 7-screen route structure remains unchanged.
