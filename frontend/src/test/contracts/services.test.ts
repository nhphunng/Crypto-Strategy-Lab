import { describe, expect, it } from 'vitest'
import { createMockServices } from '../../services/mock/createMockServices'

describe('mock service contracts', () => {
  const services = createMockServices()

  it('returns deterministic candles and keeps timeframe queries independent', () => {
    expect(services.market.getCandles('15m', 12)).toEqual(services.market.getCandles('15m', 12))
    expect(services.market.getCandles('15m', 12)).not.toEqual(services.market.getCandles('30m', 12))
  })

  it('searches markets case-insensitively and preserves availability metadata', () => {
    expect(services.market.listMarkets('bitcoin').map((market) => market.pair)).toContain('BTCUSDT')
    expect(services.market.getMarket('ETHUSDT')?.available).toBe(true)
    expect(services.market.getMarket('SOLUSDT')?.available).toBe(true)
    expect(services.market.getMarket('BNBUSDT')?.available).toBe(false)
    expect(services.market.listMarkets('not-a-market')).toEqual([])
  })

  it('exposes provenance-bearing evaluation data behind gateways', () => {
    expect(services.backtests.listRuns()).not.toHaveLength(0)
    expect(services.leaderboard.listEntries()).not.toHaveLength(0)
    expect(services.strategies.listMethods().every((method) => Boolean(method.version))).toBe(true)
  })
})
