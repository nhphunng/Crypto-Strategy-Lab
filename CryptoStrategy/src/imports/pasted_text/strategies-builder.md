Update the existing **Strategies screen** of Crypto Strategy Lab.

Do NOT rebuild the entire application.

Preserve:

* current app shell;
* dark design system;
* design tokens;
* global market selector;
* 7 top-level screens;
* strategy definitions and logic;
* Backtests integration;
* `Show explanations` behavior.

The current Strategies page has too many decisions visible at the same time.

The user currently sees:

* starter presets;
* strategy type;
* selected strategies;
* configuration;
* combination logic;
* testing CTA

inside one long screen.

This increases cognitive load and makes the required sequence unclear.

Redesign `/strategies` as a **guided multi-step strategy builder**.

The key UX principle is:

> One phase, one primary decision, one clear next action.

Use progressive disclosure strictly.

A user should finish the current phase before the next phase becomes available.

---

# 1. DO NOT CREATE NEW TOP-LEVEL ROUTES

Keep:

`/strategies`

as one product screen.

Inside this screen maintain internal builder state:

```text
Step 1 — Choose
Step 2 — Configure
Step 3 — Combine
Step 4 — Review & Test
```

These may use:

* internal state;
* query state;
* nested UI state;

but should not become additional items in the main navigation.

Do not add new sidebar navigation items.

---

# 2. UX PRINCIPLES

Apply these principles strictly.

## Progressive disclosure

Only show controls required for the current step.

Do not show configuration, weights, thresholds, decision previews, or Run Backtest before they are needed.

## Recognition over recall

Use plain-language strategy names and descriptions.

Do not force users to remember what MA, RSI, or other abbreviations mean.

## One primary action

Each phase should have one obvious primary CTA.

Examples:

Step 1:
`Continue to Configure`

Step 2:
`Continue`

Step 3:
`Review Strategy`

Step 4:
`Run Backtest`

Avoid multiple competing blue buttons.

## Keep context visible

The user should always know:

* which market is selected;
* which timeframe is selected;
* which step they are on;
* what they have already selected.

## Do not show future complexity

For example:

* do not show weights during strategy selection;
* do not show backtest metrics before running;
* do not show composite logic if only one strategy is selected.

---

# 3. GLOBAL STRATEGY BUILDER HEADER

Keep a compact persistent header inside `/strategies`.

Example:

```text
Strategies

BTC / USDT
Bitcoin priced in USDT

Timeframe
15m

[ Change Market ]
```

Below it show the builder stepper:

```text
1 Choose methods ─── 2 Configure ─── 3 Combine ─── 4 Review & Test
```

States:

* Current
* Completed
* Upcoming

Example:

```text
● 1 Choose methods
○ 2 Configure
○ 3 Combine
○ 4 Review & Test
```

After step 1:

```text
✓ 1 Choose methods
● 2 Configure
○ 3 Combine
○ 4 Review & Test
```

Users may go BACK to a completed step.

Users should NOT jump forward into an incomplete step.

---

# 4. STEP 1 — CHOOSE METHODS

This page should answer only:

> Which analysis methods do I want to use?

Do NOT show parameters yet.

Do NOT show Majority Vote or Weighted yet.

Do NOT show Run Backtest.

---

## Step 1 layout

Use:

```text
Choose how you want to analyze BTC / USDT

Start with a recommended setup or build your own.
```

Then provide two ways to begin.

### Recommended presets

Keep only three:

#### Trend Starter

`Moving Average`

Helper:

`A simple way to understand market direction.`

Button:

`Select`

---

#### Balanced Starter

Badge:

`Recommended`

`Moving Average + RSI`

Helper:

`Combines market direction with momentum.`

Button:

`Select`

---

#### Multi-Signal Starter

`Moving Average + RSI + Support / Resistance`

Helper:

`Combines trend, momentum and market structure.`

Button:

`Select`

---

## Build your own

Below presets:

```text
Or build your own

Choose one or more analysis methods.
```

Display strategy options as beginner-friendly selectable rows/cards.

### Moving Average

Technical name:
`MA Cross`

Category:
`Trend`

Question it helps answer:

`Which direction is price generally moving?`

Description:

`Compares short-term and long-term average prices to detect changes in trend.`

Selectable checkbox/card.

---

### RSI

Category:
`Momentum`

Question:

`How strong is the recent price move?`

Description:

`Measures recent buying and selling strength.`

---

### Bollinger Bands

Category:
`Volatility`

Question:

`Is price moving unusually far from its recent average?`

---

### Support / Resistance

Category:
`Market Structure`

Question:

`Where has price reacted repeatedly before?`

---

# 5. STEP 1 SELECTION SUMMARY

After a method is selected, show a compact sticky summary near the bottom:

```text
Selected

Moving Average
RSI

2 methods selected
```

Allow remove.

Primary CTA:

`Continue to Configure`

Disable the CTA when zero strategies are selected.

Do not show anything related to configuration below this CTA.

End the phase here.

---

# 6. REMOVE THE CURRENT LONG PAGE BEHAVIOR

Do NOT display all sections vertically like:

```text
Starter presets
↓
Strategy type
↓
Selected strategies
↓
Combination
↓
Run Backtest
```

at the same time.

The screen should NOT require the user to scroll through future phases.

Each phase owns the main workspace.

---

# 7. STEP 2 — CONFIGURE

When Step 1 is complete, replace the main content with Step 2.

The purpose of this phase is:

> Configure the selected methods.

Header:

```text
Configure your methods

Recommended values are already filled in.
You can keep them or customize them.
```

---

# 8. CONFIGURE ONE STRATEGY AT A TIME

Do not show four giant configuration forms simultaneously.

Use a left method list and one configuration panel.

Example:

```text
Selected methods

✓ Moving Average
  RSI
  Support / Resistance
```

Clicking one method loads its configuration in the main panel.

---

## Moving Average configuration

Primary title:

`Moving Average`

Secondary:

`MA Cross · v3`

Purpose:

`Detect changes in market direction.`

Recommended preset:

```text
Fast MA      20
Slow MA      50
```

Badge:

`Recommended`

Helper:

`The fast average reacts more quickly to recent price changes than the slow average.`

Show signal logic:

```text
Fast MA crosses above Slow MA
→ BUY

Fast MA crosses below Slow MA
→ SELL
```

Actions:

`Reset to recommended`

Do not show version-management actions prominently.

Version information belongs in `Strategy Details`.

---

# 9. CONFIGURATION COMPLETION STATE

The method list should make progress obvious.

Example:

```text
✓ Moving Average
✓ RSI
• Support / Resistance
```

When parameters remain valid, mark method completed automatically.

Do not require an unnecessary Save button for every method.

If invalid:

```text
! Moving Average
```

and prevent Continue until fixed.

---

# 10. STEP 2 FOOTER

Persistent bottom action bar:

```text
← Back

2 of 3 methods configured

[ Continue ]
```

If all methods are valid:

```text
3 of 3 methods ready

[ Continue ]
```

---

# 11. CONDITIONAL STEP LOGIC

After configuration:

If user selected exactly ONE strategy:

skip Step 3 Combine.

Stepper should become:

```text
✓ Choose
✓ Configure
— Combine not needed
● Review & Test
```

Automatically move to Review & Test.

If user selected TWO OR MORE:

go to Step 3 Combine.

This removes unnecessary complexity for single-strategy users.

---

# 12. STEP 3 — COMBINE

Only appear when 2+ methods exist.

Purpose:

> Decide how signals from the selected methods become one final signal.

Header:

```text
Combine strategy signals

You selected 3 analysis methods.
Choose how their signals should work together.
```

Do NOT show all mathematical controls immediately.

---

# 13. FIRST DECISION — COMBINATION METHOD

Show two large selectable options.

## Majority Vote

Badge:

`Recommended for beginners`

Description:

`Every strategy gets one vote. The most common signal becomes the final signal.`

Example:

```text
MA       BUY
RSI      SELL
Support  BUY

→ BUY
```

---

## Weighted

Description:

`Give some methods more influence over the final decision.`

Example:

```text
MA        20%
RSI       30%
Support   50%
```

Only after a method is selected should its settings appear.

---

# 14. MAJORITY VOTE SETTINGS

If Majority Vote is selected:

Show only:

```text
Tie behavior

What should happen when BUY and SELL receive the same number of votes?

[ HOLD ▼ ]
```

Default:

`HOLD`

Below, show a Decision Preview.

Do NOT show weight controls.

---

# 15. WEIGHTED SETTINGS

If Weighted is selected:

Show:

```text
Influence

Moving Average             20%
RSI                        30%
Support / Resistance       50%

Total                     100%
```

Use percentages as the main representation.

Provide sliders or numeric controls.

Add:

`Balance automatically`

If total != 100%:

show inline validation.

---

# 16. MOVE THRESHOLDS UNDER ADVANCED SETTINGS

Do NOT expose BUY/SELL thresholds immediately to beginners.

Use:

```text
Advanced combination settings
```

collapsed by default.

Inside:

```text
BUY threshold      +0.30
SELL threshold     -0.30
```

Explain:

`Scores above +0.30 produce BUY.`

`Scores below -0.30 produce SELL.`

`Scores in between produce HOLD.`

---

# 17. DECISION PREVIEW

This should visually teach how the configuration works.

Example:

```text
Decision Preview

Moving Average        BUY
RSI                   SELL
Support / Resistance  BUY

──────────────────────

Combination
Majority Vote

BUY        2
SELL       1

──────────────────────

Final Signal

BUY

2 of 3 methods currently agree on BUY.
```

For Weighted:

```text
Weighted score
+0.35

BUY threshold
+0.30

Final Signal
BUY

The weighted score is above the BUY threshold.
```

---

# 18. STEP 3 FOOTER

Use:

```text
← Back

Combination ready

[ Review Strategy ]
```

No Run Backtest yet.

---

# 19. STEP 4 — REVIEW & TEST

This is the only phase that should show the full strategy summary and Run Backtest.

Goal:

> Let users verify what they built before testing it.

Use a clean review screen.

---

# 20. REVIEW SUMMARY

Header:

```text
Review your strategy

Everything looks ready.
Check the setup before running a historical simulation.
```

---

## Market

```text
BTC / USDT
Bitcoin priced in USDT

15m
```

---

## Analysis methods

```text
Moving Average
20 / 50

RSI
14 · 30 / 70

Support / Resistance
120 · 0.7%
```

Allow:

`Edit`

which takes the user back to Step 2.

---

## Combination

```text
Majority Vote

Tie behavior
HOLD
```

or Weighted configuration.

Allow:

`Edit`

which returns to Step 3.

---

# 21. PLAIN-LANGUAGE TEST SUMMARY

Before the CTA display:

```text
What will happen?

Crypto Strategy Lab will apply this strategy to historical BTC / USDT 15-minute market data and simulate its BUY, SELL and HOLD decisions.

No real trades will be placed.
```

This is important for beginners.

---

# 22. PRIMARY ACTION

Only now show:

`Run Backtest`

Large but not full-width across the entire screen.

Secondary:

`Save Strategy`

if saving is supported.

Back:

`← Back`

---

# 23. BACKTEST HANDOFF

Clicking `Run Backtest` must route to Backtests and prefill:

```text
Market
BTC / USDT

Timeframe
15m

Strategy
MA + RSI + Support / Resistance

Combination
Majority Vote

Parameters
Preserved
```

Do not make users configure the same information again.

---

# 24. PERSISTENT BUILDER SUMMARY

During Steps 2–4, optionally use a compact right-side summary panel.

Example:

```text
YOUR STRATEGY

BTC / USDT · 15m

Methods
3

MA
RSI
Support / Resistance

Status
In progress
```

Keep this compact.

Do not turn it into another configuration panel.

Its purpose is orientation only.

---

# 25. BACK / NEXT BEHAVIOR

Every step must support:

`Back`

without losing selections.

If user goes from Configure back to Choose:

* previous selections remain selected.

If they remove one strategy:

* its configuration is removed;
* dependent composite state updates.

If they move forward again:

* valid configurations remain preserved.

---

# 26. SHOW EXPLANATIONS

Keep the global:

`Show explanations`

toggle.

When ON:

* helper descriptions;
* beginner hints;
* category questions;
* recommended labels;
* explanations

remain visible.

When OFF:

* reduce descriptions;
* keep the exact same workflow;
* make panels denser.

Do NOT create two separate layouts.

---

# 27. STRATEGY DETAILS

Keep the existing `Strategy Details` drawer.

Move advanced information there:

* strategy ID;
* plugin type;
* version;
* exact parameter schema;
* valid ranges;
* registration metadata;
* provenance;
* decision rules.

Do not display these prominently in the beginner builder unless needed.

---

# 28. VISUAL HIERARCHY

At any moment the user should visually see:

1. Current phase title
2. Main decision/content
3. Current selections
4. Primary next action

Do not put several equally strong sections on one screen.

Use whitespace to separate choices inside a phase, but avoid excessive dashboard card grids.

---

# 29. REMOVE DUPLICATE CTAs

The current screen contains several ways to start the same task:

* Balanced Starter
* Choose Strategies
* preset links
* Add Strategy
* giant Choose a Strategy CTA.

Reduce duplicates.

In Step 1:

Use only:

* preset `Select` actions;
* selectable strategy methods;
* one `Continue to Configure` button.

Do not show another full-width `Choose a Strategy` CTA.

---

# 30. STEP 1 REFERENCE LAYOUT

```text
┌─────────────────────────────────────────────────────────────┐
│ Strategies                                                  │
│ BTC/USDT · 15m                         [Change Market]       │
│                                                             │
│ ● Choose ─── ○ Configure ─── ○ Combine ─── ○ Review        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Choose analysis methods                                     │
│ Start with a preset or create your own setup.              │
│                                                             │
│ [ Trend Starter ] [ Balanced Starter ] [ Multi-Signal ]    │
│                                                             │
│ ─────────────── or choose manually ───────────────          │
│                                                             │
│ □ Moving Average                                            │
│   Trend · Which direction is price moving?                 │
│                                                             │
│ □ RSI                                                       │
│   Momentum · How strong is the move?                       │
│                                                             │
│ □ Bollinger Bands                                           │
│   Volatility · Is price unusually stretched?              │
│                                                             │
│ □ Support / Resistance                                      │
│   Structure · Where has price reacted before?             │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ 2 methods selected               [ Continue to Configure ] │
└─────────────────────────────────────────────────────────────┘
```

---

# 31. STEP 2 REFERENCE LAYOUT

```text
● Choose ─── ● Configure ─── ○ Combine ─── ○ Review

Configure methods

┌──────────────────┬──────────────────────────────────────────┐
│ SELECTED         │ Moving Average                           │
│                  │                                          │
│ ✓ Moving Average │ Detect market direction.                 │
│ ✓ RSI            │                                          │
│ • Support        │ Fast MA                                  │
│                  │ [20]                                     │
│                  │                                          │
│                  │ Slow MA                                  │
│                  │ [50]                                     │
│                  │                                          │
│                  │ Recommended setup                        │
│                  │                                          │
│                  │ Signal rules                             │
│                  │ MA20 > MA50 → BUY                        │
│                  │ MA20 < MA50 → SELL                       │
└──────────────────┴──────────────────────────────────────────┘

← Back                     3 of 3 ready      [ Continue ]
```

---

# 32. STEP 3 REFERENCE LAYOUT

```text
✓ Choose ─── ✓ Configure ─── ● Combine ─── ○ Review

How should these methods work together?

[ Majority Vote ]
Recommended
Every method gets one vote.

[ Weighted ]
Give some methods more influence.

────────────────────────────────────────────

Decision Preview

MA          BUY
RSI         SELL
Support     BUY

BUY         2
SELL        1

Final       BUY

← Back                                  [ Review Strategy ]
```

---

# 33. STEP 4 REFERENCE LAYOUT

```text
✓ Choose ─── ✓ Configure ─── ✓ Combine ─── ● Review

Review your strategy

MARKET
BTC / USDT · 15m

METHODS
Moving Average        20 / 50
RSI                   14 · 30 / 70
Support / Resistance  120 · 0.7%

COMBINATION
Majority Vote
Tie → HOLD

────────────────────────────────────────────

What will happen?

This setup will be tested against historical BTC/USDT
15-minute data.

No real trades will be placed.

← Back                              [ Run Backtest ]
```

---

# 34. MICRO-INTERACTIONS

Use subtle transitions when moving between phases.

When Next is clicked:

* current content fades/offsets left slightly;
* next phase fades/offsets in from right;
* duration approximately 180–260ms.

When Back:

* reverse direction.

Do not animate like a mobile onboarding carousel.

Keep the professional desktop feel.

When a step completes:

* step dot changes to checkmark;
* connector line fills subtly.

Respect reduced-motion preferences.

---

# 35. COMPLETION FEEDBACK

After selecting a preset:

Do not immediately jump through multiple steps.

Show:

`Balanced Starter selected`

Then enable:

`Continue to Configure`

This keeps users in control.

After valid configuration:

`All methods ready`

After combination:

`Combination ready`

---

# 36. ERROR HANDLING

Do not show vague messages.

Examples:

Bad:
`Invalid parameter`

Use:
`Fast MA must be shorter than Slow MA.`

Provide:
`Use recommended values`

---

Bad:
`Invalid weights`

Use:
`Strategy influence currently totals 90%. Adjust the weights to reach 100%.`

Provide:
`Balance automatically`

---

# 37. FINAL USABILITY TEST

A new user should never need to ask:

`What am I supposed to do first?`

At every phase they should see exactly:

* what they are choosing;
* why;
* current progress;
* how to continue.

Test this flow:

1. Open Strategies.
2. Select Balanced Starter.
3. Continue.
4. Review MA and RSI parameters.
5. Continue.
6. Select Majority Vote.
7. Review Decision Preview.
8. Continue.
9. Review full configuration.
10. Run Backtest.

The flow should be achievable without scrolling through unrelated future settings.

---

# 38. REQUIRED CHECKLIST

Before completing the patch, verify:

* Strategies remains one top-level route.
* Builder has four internal phases.
* Only current phase content is visible.
* Upcoming phases are not rendered below current content.
* Completed phases can be revisited.
* Future incomplete phases cannot be opened directly.
* Step 3 is skipped for a single strategy.
* No duplicate Choose Strategy CTA exists.
* Presets only select methods; they do not unexpectedly run anything.
* Step 1 contains no parameters.
* Step 2 contains no combination controls.
* Step 3 contains no backtest controls.
* Run Backtest appears only in Step 4.
* Selections persist when navigating Back.
* Market and timeframe remain visible throughout.
* Majority Vote defaults for multi-strategy beginner flow.
* Advanced Weighted thresholds remain progressively disclosed.
* Strategy Details contains advanced/version metadata.
* Backtest receives the completed builder context.
* Show Explanations still works.
* No new product navigation route was introduced.
