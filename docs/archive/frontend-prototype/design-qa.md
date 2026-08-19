# Design QA: Crypto Strategy Lab

**Final result: passed**

## Scope

- Source: `E:/HCMUS/Sem9/Software architecture/Project/UI_ref`
- Implementation: `E:/HCMUS/Sem9/Software architecture/Project/Crypto-Strategy-Lab/CryptoStrategy`
- Source-of-truth viewport: 1440 × 900, dense desktop lab
- Responsive acceptance viewport: 1024 × 768, collapsed navigation rail
- Density: compact research workstation; 28–36 px controls, 11–15 px interface type, tabular monospace data
- Assets: Lucide icon set and locally bundled Inter/JetBrains Mono fonts; the source contains no raster imagery

## Captured states

Reference and implementation captures are stored in `reference-captures/`.

- Landing at 1440 × 900
- Market four-chart live workspace at 1440 × 900 and 1024 × 768
- Strategies choose step at 1440 × 900
- Backtests single result at 1440 × 900 and Strategy Search at 1024 × 768
- Leaderboard at 1440 × 900
- News healthy at 1440 × 900
- Operations running at 1440 × 900 and 1024 × 768
- Focused interactive states checked live: market unmatched search, strategy validation error, search stop dialog, leaderboard inspector, News degraded/empty, Operations stop/resume

## Comparison history

### Pass 1 — source capture

Captured all seven source destinations before refactoring. The source established exact tokens, 48 px top bar, 184/52 px navigation, dense grid alignment, typography, icon weight, and surface hierarchy.

### Pass 2 — 1440 × 900 implementation comparison

Placed every source screenshot and its implementation screenshot into the same visual comparison pass.

- Landing, Strategies, Backtests, and Operations match the source layout, typography, spacing, color, borders, radii, and content hierarchy.
- Market is visually equivalent; the explanatory sentence now states that availability comes from the market service instead of describing a page-owned prototype constant.
- Leaderboard retains the source question icons and sort direction while replacing clickable headers with semantic buttons and `aria-sort`.
- News preserves the source visual hierarchy. Distribution values are calculated from the visible filtered rows, so the values intentionally differ from the source's disconnected constant.
- Dynamic loop/search counters may differ from the source capture; layout and formatting remain fixed and deterministic at initial load.
- No substitute imagery, custom SVG illustration, CSS artwork, or placeholder asset was introduced.

Result: no high- or medium-severity fidelity mismatch remained.

### Pass 3 — accessibility correction

- Added named segmented groups, `aria-pressed`, and arrow-key movement.
- Added programmatic field labels, invalid state, and described validation errors.
- Added dialog names, modal semantics, initial focus, focus containment, Escape close, and trigger focus restoration.
- Added switch semantics, polite toast live regions, named icon actions, keyboard-operable table rows, real sortable header buttons, and non-color status text/icons.
- Retained a global visible `:focus-visible` treatment and reduced-motion handling.

Result: accessibility changes preserved the source's dense visual grammar.

### Pass 4 — responsive comparison

- 1024 × 768 Market: four panes remain usable; navigation collapses to 52 px; document width remains exactly 1024 px.
- 1024 × 768 Backtests Search: fixed three-column layout reflows to two columns with Top-K below; grid width equals client width (972 px) with no document overflow.
- 1024 × 768 Operations: pipeline, metrics, dependency table, and workers remain reachable with no document overflow.
- Drawers are capped to the viewport and dense tables scroll within their owning panel.

Result: no overlap, clipping, or document-level horizontal overflow at acceptance widths.

## Interaction verification

- Landing `Open Strategy Lab` navigates to `/market`.
- Market pane timeframes remained `[5m, 30m, 1h, 4h]` after changing only chart 2; an unmatched watchlist query renders `No markets match your search.`
- Balanced Starter advances to Configure; setting Fast MA 50 and Slow MA 20 renders the inline relationship error, sets `aria-invalid`, and disables Continue.
- Backtests Strategy Search opens a named stop dialog; Escape closes it and restores focus to `Stop Search`.
- Leaderboard Score toggles `aria-sort`; Single filtering reduces the table to one row; the inspector opens and closes while preserving the filter.
- News degraded mode leaves shell navigation operational; ETH + Negative renders the explicit empty state.
- Operations Stop Loop supports cancel and confirm; counters remain unchanged while stopped and resume advancing after Start Loop.

## Runtime verification

- Clean browser session: 0 console errors, 0 console warnings.
- All inspected routes: document width equals viewport width.
- TypeScript: passed.
- Vitest: 3 files, 10 tests passed.
- Production Vite build: passed.
- Sites worker/packaging: 4 tests passed; required client, server, and hosting artifacts emitted.

