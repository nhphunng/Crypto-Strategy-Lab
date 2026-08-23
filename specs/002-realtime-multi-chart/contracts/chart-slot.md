# Contract: Base Chart Slot and Grid

**Status**: Accepted
**Version**: `1`
**Accepted**: 2026-08-19 by the Crypto Strategy Lab Team.

## Purpose and ownership

TV2 owns the base Candle chart, slot controls, connection presentation, and generic extension inputs. Strategy computation belongs to TV3. Signal/trade overlay meaning and ranked-result detail belong to TV5.

## Grid rules

- The dashboard contains one to four stable `slotId` values.
- One slot uses the available row width. Two to four slots use a two-column grid when space permits.
- Below the documented narrow-screen breakpoint, all slots use one column; controls wrap without horizontal-page scrolling.
- Adding, removing, loading, or reconfiguring one slot does not recreate another slot's chart instance or reset its viewport.
- The dashboard pair is shared in MVP. Each slot controls its timeframe independently.

## Required slot inputs

```text
slotId
pair
timeframe
candles[]              bounded, ordered, provider-neutral
connectionState        LOADING | LIVE | STALE | RECONNECTING | ERROR
error?                 sanitized code and user message
onTimeframeChange
onRemove
onRetry
```

Generic optional extension inputs may include bounded overlay series and markers. The base component interprets only generic primitive types. It must not branch on Strategy, Trade, Backtest, Evaluation, or Leaderboard identities.

## Stable element IDs

| Element | Pattern | Example |
|---|---|---|
| Dashboard pair selector | `select-pair` | `select-pair` |
| Timeframe selector | `select-timeframe-{slotId}` | `select-timeframe-slot-1` |
| Chart section/container | `chart-{pair}-{timeframe}-{slotId}` | `chart-btcusdt-5m-slot-1` |
| Remove chart action | `btn-remove-chart-{slotId}` | `btn-remove-chart-slot-1` |
| Retry action | `btn-retry-chart-{slotId}` | `btn-retry-chart-slot-1` |
| Add chart action | `btn-add-chart` | `btn-add-chart` |
| Connection status | `status-chart-{slotId}` | `status-chart-slot-1` |

Changing these IDs is a test-selector contract change.

## Accessibility

- Every slot is a labelled section whose accessible name includes pair and timeframe.
- Add, remove, timeframe, and retry controls use native keyboard-operable elements with visible focus.
- Status uses text and an icon/shape in addition to color.
- Meaningful state changes use a polite status announcement; individual Candle ticks are not announced.
- Canvas output has a semantic latest-Candle summary with UTC time and OHLCV values.
- Pointer and touch interaction must not be the only way to operate required controls.
- Touch targets should be at least 44 by 44 CSS pixels where practical.

## State presentation

| State | Required presentation |
|---|---|
| `LOADING` | Loading label; old selection not described as live |
| `LIVE` | Live label plus last-update UTC time |
| `STALE` | Old data remains visible with a clear stale warning |
| `RECONNECTING` | Recovery label and attempt feedback without blocking healthy slots |
| `ERROR` | Sanitized reason and retry action when retryable |
| Empty/partial history | Explicit empty/partial message and missing-range context |

## Slot isolation

- Every asynchronous history request and event dispatch is associated with a slot generation.
- Changing a timeframe advances that generation, releases the old selection, clears/replaces only that slot's series, and ignores late old-generation work.
- Unaffected slots retain data, status, selected timeframe, zoom, scroll position, and chart instance.
- Two slots sharing a selection may share validated Candle data but never share viewport or focus state.

## Performance boundary

- The displayed series contains at most 1,000 Candles; initial target is at most 500.
- A same-identity live update uses the chart library's incremental update path rather than rebuilding all series.
- Rendering telemetry records when an `eventId` is applied so ingestion-to-visible p95 can be measured without production UI text.

## TV5 composition seam

TV5 may pass generic overlay and marker descriptors defined by its own contract. TV2 guarantees stable Candle coordinates and a composition point. TV2 does not define BUY/SELL, Entry/Exit, trade selection, score, rank, or provenance behavior.

### Cross-check with `specs/005-leaderboard-visualization/contracts/chart-overlays.md` (2026-08-20)

The base renderer (`frontend/src/features/market-chart/components/CandlestickChart.tsx`) is verified to contain no import or branch on Strategy, Trade, Backtest, Evaluation, or Leaderboard identities. Its generic seam is:

```text
ChartOverlaySeries { id, points: { openTime, value }[], color?, dashed? }
ChartMarker        { id, openTime, value, label, color? }
```

Compatibility mapping for TV5 composition:

- TV5 `LINE` overlays map 1:1 onto `ChartOverlaySeries`; decimal-string `value` is converted to a number and `time` maps to `openTime` at the TV5 composition point.
- TV5 `BAND` and `ZONE` kinds are not interpreted by the base component; they must be decomposed into generic LINE series (or a dedicated TV5 renderer) at the composition point, because the base interprets only generic primitives.
- TV5 `styleToken`, `label`, `sourceStrategyId`, `sourceStrategyVersion`, `signalId`, and `tradeId` are presentation/provenance fields outside the base seam; TV5 maps `styleToken`/`label` onto the base `color`/`label` fields and keeps provenance in its own descriptors.
- TV5 marker `type`/`shape` semantics (BUY/SELL/HOLD/ENTRY/EXIT with grayscale-safe shape cues) are TV5-layer behavior; the base renders every generic marker with the same circle-and-label presentation and does not branch on type.
- TV5 alignment rules are enforced at the TV5 layer; the base only filters markers/overlays to Candle times present in the loaded range, which TV5 surfaces as its partial-data notice.
- TV5 availability states (`AVAILABLE`, `EMPTY`, `PARTIAL`, `UNAVAILABLE`) are TV5 domain data and never enter the base seam.
