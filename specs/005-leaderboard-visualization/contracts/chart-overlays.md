# Contract: Ranked Result Chart Overlays

## Purpose

Describe chart primitives independently of Strategy implementation and the chart library. The renderer recognizes primitive `kind`/marker `type`, never concrete Strategy names.

## Overlay Descriptor

```json
{
  "id": "ma20",
  "kind": "LINE",
  "label": "MA20",
  "styleToken": "PRIMARY_INDICATOR",
  "sourceStrategyId": "ma-rsi-sr",
  "sourceStrategyVersion": "3",
  "points": [
    { "time": "2026-07-01T08:00:00Z", "value": "108123.45" }
  ]
}
```

Kinds:

- `LINE`: one ordered value per point.
- `BAND`: ordered `upper`, `middle` (optional), and `lower` values per point.
- `ZONE`: ordered time range and upper/lower price boundaries, for Support/Resistance areas.

All values are finite decimal strings. Points are chronological, bounded to the requested range, and carry no HTML/script or chart-library options.

## Marker Descriptor

```json
{
  "id": "trade-3-entry",
  "type": "ENTRY",
  "time": "2026-07-04T07:00:00Z",
  "price": "109000",
  "label": "ENTRY #3",
  "shape": "ARROW_UP",
  "tone": "POSITIVE",
  "sourceStrategyId": "ma-rsi-sr",
  "sourceStrategyVersion": "3",
  "signalId": "signal-17",
  "tradeId": "trade-3"
}
```

| Type | Required label | Required shape cue |
|------|----------------|--------------------|
| `BUY` | BUY | upward triangle/arrow |
| `SELL` | SELL | downward triangle/arrow |
| `HOLD` | HOLD | neutral diamond/dot |
| `ENTRY` | ENTRY plus trade number | entry-specific outlined/up marker |
| `EXIT` | EXIT plus trade number | exit-specific outlined/down marker |

Color/tone is supplementary. Label and shape must distinguish types in grayscale and for common color-vision deficiencies. HOLD markers are available through an explicit visibility control and may default to hidden.

`shape` uses `ARROW_UP`, `ARROW_DOWN`, `TRIANGLE_UP`, `TRIANGLE_DOWN`, `DIAMOND`, `DOT`, `ENTRY_OUTLINED`, or `EXIT_OUTLINED`. Optional `tone` uses `POSITIVE`, `NEGATIVE`, `NEUTRAL`, or `INFO`. Every marker carries the source Strategy identity/version. `price` is a decimal string for aligned markers; it may be `null` only when the marker is returned as unaligned with a reason.

## Alignment Rules

- `time` and `price` are recorded source coordinates; the frontend MUST NOT snap them silently to a different Candle.
- If a source timestamp has no Candle in the loaded range, return it in `unalignedMarkers` with a reason and show a partial-data notice.
- Overlapping markers retain separate IDs/details and may be offset or clustered visually.
- Selecting a Trade highlights both matching `ENTRY` and `EXIT`; keyboard focus provides the same detail as pointer selection.

## Availability States

The visualization response reports Candle, overlay, Signal, and Trade availability as `AVAILABLE`, `EMPTY`, `PARTIAL`, or `UNAVAILABLE`, with a bounded human-readable reason. Missing optional overlays never fabricate data or prevent Candle/trade provenance from being viewed.
