export type Candle = {
  t: number
  o: number
  h: number
  l: number
  c: number
  v: number
}

export type Marker = {
  index: number
  kind: 'buy' | 'sell' | 'entry' | 'exit'
}

const round2 = (value: number) => Math.round(value * 100) / 100

export function simpleMovingAverage(candles: Candle[], period: number): (number | null)[] {
  const values: (number | null)[] = []
  let sum = 0
  for (let index = 0; index < candles.length; index += 1) {
    sum += candles[index].c
    if (index >= period) sum -= candles[index - period].c
    values.push(index >= period - 1 ? round2(sum / period) : null)
  }
  return values
}

export function supportResistance(candles: Candle[]) {
  const highs = candles.map((candle) => candle.h)
  const lows = candles.map((candle) => candle.l)
  const maximum = Math.max(...highs)
  const minimum = Math.min(...lows)
  const span = maximum - minimum
  return {
    resistance: [round2(maximum - span * 0.08), round2(maximum - span * 0.02)] as [number, number],
    support: [round2(minimum + span * 0.03), round2(minimum + span * 0.1)] as [number, number],
  }
}

export const formatChartPrice = (value: number) =>
  value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
