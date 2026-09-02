import { describe, expect, it } from 'vitest'

import { createSingleBacktestCandleTimeline } from '../../src/features/backtests'
import type { DatasetCandle } from '../../src/features/backtests'

const candle = (openTime: string, closeTime: string, open: string): DatasetCandle => ({
  provider: 'BINANCE',
  pair: 'BTCUSDT',
  timeframe: '15m',
  openTime,
  closeTime,
  open,
  high: String(Number(open) + 2),
  low: String(Number(open) - 2),
  close: String(Number(open) + 1),
  volume: '10',
  closed: true,
  receivedAt: closeTime,
})

describe('Single Backtest persisted Dataset chart', () => {
  const timeline = createSingleBacktestCandleTimeline([
    candle('2026-08-01T00:00:00.000Z', '2026-08-01T00:14:59.999Z', '100'),
    candle('2026-08-01T00:15:00.000Z', '2026-08-01T00:29:59.999Z', '101'),
  ])

  it('maps the API Candle values without generating preview data', () => {
    expect(timeline.candles).toEqual([
      { t: Date.parse('2026-08-01T00:00:00.000Z'), o: 100, h: 102, l: 98, c: 101, v: 10 },
      { t: Date.parse('2026-08-01T00:15:00.000Z'), o: 101, h: 103, l: 99, c: 102, v: 10 },
    ])
  })

  it('aligns persisted fills to the Candle interval that contains their timestamp', () => {
    expect(timeline.findIndex('2026-08-01T00:00:00.000Z')).toBe(0)
    expect(timeline.findIndex('2026-08-01T00:14:59.999Z')).toBe(0)
    expect(timeline.findIndex('2026-08-01T00:22:00.000Z')).toBe(1)
  })

  it('does not pin out-of-range or invalid fills to the first or last Candle', () => {
    expect(timeline.findIndex('2026-07-31T23:59:59.999Z')).toBe(-1)
    expect(timeline.findIndex('2026-08-01T00:30:00.000Z')).toBe(-1)
    expect(timeline.findIndex('not-a-timestamp')).toBe(-1)
  })
})
