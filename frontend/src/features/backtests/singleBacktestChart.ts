import type { Candle } from '../../components/candleChartModel'
import type { DatasetCandle } from './types'

export type SingleBacktestCandleTimeline = {
  candles: Candle[]
  findIndex: (timestamp: string) => number
}

export function createSingleBacktestCandleTimeline(items: DatasetCandle[]): SingleBacktestCandleTimeline {
  const ranges = items.map((item) => ({
    openTime: Date.parse(item.openTime),
    closeTime: Date.parse(item.closeTime),
  }))
  const candles = items.map((item, index) => ({
    t: ranges[index].openTime,
    o: Number(item.open),
    h: Number(item.high),
    l: Number(item.low),
    c: Number(item.close),
    v: Number(item.volume),
  }))

  return {
    candles,
    findIndex(timestamp: string) {
      const target = Date.parse(timestamp)
      if (!Number.isFinite(target)) return -1

      let lower = 0
      let upper = ranges.length - 1
      let candidate = -1
      while (lower <= upper) {
        const middle = Math.floor((lower + upper) / 2)
        if (ranges[middle].openTime <= target) {
          candidate = middle
          lower = middle + 1
        } else {
          upper = middle - 1
        }
      }

      if (candidate < 0 || target > ranges[candidate].closeTime) return -1
      return candidate
    },
  }
}
