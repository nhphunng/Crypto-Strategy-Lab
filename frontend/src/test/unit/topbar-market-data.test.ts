import { describe, expect, it, vi } from 'vitest'

import {
  summarizeCandles,
  topBarHistoryRange,
} from '../../features/market-chart/hooks/useTopBarMarketData'
import type { Candle } from '../../features/market-chart/types'

function candle(openTime: string, open: string, close: string): Candle {
  return {
    provider: 'BINANCE',
    pair: 'BTCUSDT',
    timeframe: '5m',
    openTime,
    closeTime: new Date(Date.parse(openTime) + 299_999).toISOString(),
    open,
    high: close,
    low: open,
    close,
    volume: '1',
    closed: true,
    receivedAt: new Date(Date.parse(openTime) + 300_000).toISOString(),
  }
}

describe('topbar market data', () => {
  it('derives the latest price and 24-hour change from real Candle values', () => {
    const values = summarizeCandles([
      candle('2026-09-02T12:00:00.000Z', '100', '101'),
      candle('2026-09-03T11:55:00.000Z', '101', '110'),
    ])

    expect(values).toEqual({ price: 110, change24h: 10 })
  })

  it('returns unavailable values until history arrives', () => {
    expect(summarizeCandles([])).toEqual({ price: null, change24h: null })
  })

  it('requests an aligned 24-hour window', () => {
    vi.useFakeTimers()
    vi.setSystemTime('2026-09-03T12:02:34.000Z')

    expect(topBarHistoryRange({ provider: 'BINANCE', pair: 'BTCUSDT', timeframe: '5m' })).toEqual({
      startTime: '2026-09-02T12:00:00.000Z',
      endTime: '2026-09-03T12:00:00.000Z',
    })

    vi.useRealTimers()
  })
})
