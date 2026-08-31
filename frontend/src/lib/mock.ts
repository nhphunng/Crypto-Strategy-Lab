// Deterministic mock data for Crypto Strategy Lab.
// Everything is seeded so screens feel like parts of the same live experiment.

export type Candle = {
  t: number // epoch ms
  o: number
  h: number
  l: number
  c: number
  v: number
}

export type Timeframe = '1m' | '5m' | '15m' | '30m' | '1h' | '2h' | '4h' | '1d'

export const TIMEFRAMES: Timeframe[] = ['1m', '5m', '15m', '30m', '1h', '2h', '4h', '1d']

const TF_MINUTES: Record<Timeframe, number> = {
  '1m': 1,
  '5m': 5,
  '15m': 15,
  '30m': 30,
  '1h': 60,
  '2h': 120,
  '4h': 240,
  '1d': 1440,
}

// mulberry32 — small deterministic PRNG
function rng(seed: number) {
  let a = seed >>> 0
  return () => {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const BASE_PRICE = 63008.57
const ANCHOR = Date.UTC(2026, 7, 16, 18, 24, 0) // deterministic "now"

// Build a candle series ending at the anchor time. Seeded per timeframe so
// changing one chart's timeframe never disturbs another.
export function makeCandles(tf: Timeframe, count = 120): Candle[] {
  const rand = rng(0x51a3 ^ (TF_MINUTES[tf] * 2654435761))
  const stepMs = TF_MINUTES[tf] * 60_000
  const vol = BASE_PRICE * (0.0012 + TF_MINUTES[tf] / 24000)
  const out: Candle[] = []

  // Walk backwards from BASE_PRICE, then reverse — guarantees last close == BASE_PRICE-ish.
  let price = BASE_PRICE
  const drift = -0.00016 // gentle upward bias when reversed
  for (let i = 0; i < count; i++) {
    const t = ANCHOR - i * stepMs
    const shock = (rand() - 0.5) * 2
    const wave = Math.sin(i / (6 + TF_MINUTES[tf] / 12)) * vol * 0.7
    const c = price
    const o = price - (shock * vol + wave * 0.15 + price * drift)
    const hi = Math.max(o, c) + rand() * vol * 0.9
    const lo = Math.min(o, c) - rand() * vol * 0.9
    const v = 40 + rand() * 160 + Math.abs(shock) * 90
    out.push({ t, o: round2(o), h: round2(hi), l: round2(lo), c: round2(c), v: Math.round(v) })
    price = o
  }
  out.reverse()
  return out
}

function round2(n: number) {
  return Math.round(n * 100) / 100
}

// Simple moving average of closes; null until enough samples.
export function sma(candles: Candle[], period: number): (number | null)[] {
  const out: (number | null)[] = []
  let sum = 0
  for (let i = 0; i < candles.length; i++) {
    sum += candles[i].c
    if (i >= period) sum -= candles[i - period].c
    out.push(i >= period - 1 ? round2(sum / period) : null)
  }
  return out
}

// Support / resistance bands derived from the series range (deterministic).
export function supportResistance(candles: Candle[]) {
  const highs = candles.map((c) => c.h)
  const lows = candles.map((c) => c.l)
  const max = Math.max(...highs)
  const min = Math.min(...lows)
  const span = max - min
  return {
    resistance: [round2(max - span * 0.08), round2(max - span * 0.02)] as [number, number],
    support: [round2(min + span * 0.03), round2(min + span * 0.1)] as [number, number],
  }
}

export type Marker = {
  index: number
  kind: 'buy' | 'sell' | 'entry' | 'exit'
}

// Deterministic sample signal markers for a series.
export function signalMarkers(candles: Candle[], seed = 7): Marker[] {
  const rand = rng(seed * 99991)
  const markers: Marker[] = []
  const n = candles.length
  for (let i = 12; i < n - 4; i += Math.floor(9 + rand() * 8)) {
    const buy = rand() > 0.5
    markers.push({ index: i, kind: buy ? 'buy' : 'sell' })
    const exit = Math.min(n - 2, i + 3 + Math.floor(rand() * 5))
    markers.push({ index: i, kind: 'entry' })
    markers.push({ index: exit, kind: 'exit' })
  }
  return markers
}

export const fmtPrice = (n: number) =>
  n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export const fmtInt = (n: number) => n.toLocaleString('en-US')

// ---------------------------------------------------------------------------
// Global experiment constants
// ---------------------------------------------------------------------------

export const MARKET = {
  pair: 'BTCUSDT',
  base: 'BTC',
  quote: 'USDT',
  provider: 'Binance',
  price: 63008.57,
  change24h: 1.82,
  high24h: 63840.12,
  low24h: 61402.9,
  volume24h: '1.42B',
}

// Selectable markets. BTC/USDT, ETH/USDT, and SOL/USDT are the supported
// prototype market contexts; other entries remain visible but unavailable.
export type MarketInfo = {
  pair: string // 'BTCUSDT'
  display: string // 'BTC / USDT'
  base: string
  quote: string
  name: string // 'Bitcoin'
  price: number
  change24h: number
  symbol: string // glyph shown in the coin chip
  color: string // chip background
  available: boolean
}

export const MARKETS: MarketInfo[] = [
  {
    pair: 'BTCUSDT',
    display: 'BTC / USDT',
    base: 'BTC',
    quote: 'USDT',
    name: 'Bitcoin',
    price: 63008.57,
    change24h: 1.82,
    symbol: '₿',
    color: '#f7931a',
    available: true,
  },
  {
    pair: 'ETHUSDT',
    display: 'ETH / USDT',
    base: 'ETH',
    quote: 'USDT',
    name: 'Ethereum',
    price: 3482.14,
    change24h: 2.14,
    symbol: 'Ξ',
    color: '#627eea',
    available: true,
  },
  {
    pair: 'SOLUSDT',
    display: 'SOL / USDT',
    base: 'SOL',
    quote: 'USDT',
    name: 'Solana',
    price: 147.62,
    change24h: -0.61,
    symbol: '◎',
    color: '#14f195',
    available: true,
  },
  {
    pair: 'BNBUSDT',
    display: 'BNB / USDT',
    base: 'BNB',
    quote: 'USDT',
    name: 'BNB',
    price: 592.18,
    change24h: 0.94,
    symbol: 'B',
    color: '#f0b90b',
    available: false,
  },
]

export const SEARCH_RUN = {
  id: 'SR-0184',
  generator: 'Random Search v1',
  seed: 424242,
  candidateLimit: 2000,
  tested: 364,
  workers: 4,
  failed: 3,
  retried: 2,
  queue: 218,
  throughput: 6.8,
  top1: 84.1,
}

export type Strategy = {
  id: string
  strategyId?: string
  strategyType?: string
  name: string
  category: string
  version: string
  contractVersion?: string
  origin?: 'BUILT_IN' | 'LLM_GENERATED'
  capabilities?: string[]
  generationProvenanceId?: string | null
  generatedArtifactFingerprint?: string | null
  summary: string
  status: string
  params: { key: string; label: string; value: number; min: number; max: number; step: number }[]
  rules: { text: string; side: 'buy' | 'sell' }[]
}

export const STRATEGIES: Strategy[] = [
  {
    id: 'ma-cross-v3',
    name: 'MA Cross',
    category: 'Trend',
    version: 'v3',
    summary: '20 / 50',
    status: 'Tested',
    params: [
      { key: 'fast', label: 'Fast MA', value: 20, min: 2, max: 100, step: 1 },
      { key: 'slow', label: 'Slow MA', value: 50, min: 5, max: 400, step: 1 },
    ],
    rules: [
      { text: 'MA20 crosses above MA50', side: 'buy' },
      { text: 'MA20 crosses below MA50', side: 'sell' },
    ],
  },
  {
    id: 'rsi-reversal-v2',
    name: 'RSI Reversal',
    category: 'Momentum',
    version: 'v2',
    summary: '14 · 30 / 70',
    status: 'Tested',
    params: [
      { key: 'period', label: 'Period', value: 14, min: 2, max: 60, step: 1 },
      { key: 'buy', label: 'Oversold', value: 30, min: 5, max: 45, step: 1 },
      { key: 'sell', label: 'Overbought', value: 70, min: 55, max: 95, step: 1 },
    ],
    rules: [
      { text: 'RSI crosses above oversold (30)', side: 'buy' },
      { text: 'RSI crosses below overbought (70)', side: 'sell' },
    ],
  },
  {
    id: 'bb-mean-rev-v1',
    name: 'Bollinger Mean Reversion',
    category: 'Volatility',
    version: 'v1',
    summary: '20 · σ2',
    status: 'Valid',
    params: [
      { key: 'period', label: 'Period', value: 20, min: 5, max: 60, step: 1 },
      { key: 'std', label: 'Std Dev', value: 2, min: 1, max: 4, step: 0.5 },
    ],
    rules: [
      { text: 'Close pierces lower band', side: 'buy' },
      { text: 'Close pierces upper band', side: 'sell' },
    ],
  },
  {
    id: 'sr-v4',
    name: 'Support Resistance',
    category: 'Structure',
    version: 'v4',
    summary: '120 · 0.7%',
    status: 'Tested',
    params: [
      { key: 'lookback', label: 'Lookback', value: 120, min: 20, max: 400, step: 5 },
      { key: 'tolerance', label: 'Tolerance %', value: 0.7, min: 0.1, max: 3, step: 0.1 },
    ],
    rules: [
      { text: 'Bounce off support zone', side: 'buy' },
      { text: 'Rejection at resistance zone', side: 'sell' },
    ],
  },
]

export type LeaderRow = {
  rank: number
  strategy: string
  score: number
  ret: number
  winRate: number
  mdd: number
  trades: number
  sharpe: number
  updated: string
  members: string[]
}

export const LEADERBOARD: LeaderRow[] = [
  {
    rank: 1,
    strategy: 'MA20 + RSI14 + SR',
    score: 84.1,
    ret: 24.2,
    winRate: 62,
    mdd: -7.1,
    trades: 81,
    sharpe: 1.56,
    updated: '2m ago',
    members: ['MA Cross v3', 'RSI Reversal v2', 'Support Resistance v4'],
  },
  {
    rank: 2,
    strategy: 'MA20 + BB20',
    score: 81.4,
    ret: 21.7,
    winRate: 55,
    mdd: -8.4,
    trades: 105,
    sharpe: 1.42,
    updated: '4m ago',
    members: ['MA Cross v3', 'Bollinger Mean Reversion v1'],
  },
  {
    rank: 3,
    strategy: 'RSI14 + SR',
    score: 79.8,
    ret: 18.4,
    winRate: 64,
    mdd: -6.7,
    trades: 52,
    sharpe: 1.39,
    updated: '9m ago',
    members: ['RSI Reversal v2', 'Support Resistance v4'],
  },
  {
    rank: 4,
    strategy: 'MA50',
    score: 63.5,
    ret: 9.1,
    winRate: 48,
    mdd: -14.2,
    trades: 140,
    sharpe: 0.82,
    updated: '21m ago',
    members: ['MA Cross v3'],
  },
]

export type Trade = {
  n: number
  entryTime: string
  side: 'BUY' | 'SELL'
  entryPrice: number
  exitTime: string
  exitPrice: number
  pl: number
  result: 'WIN' | 'LOSS'
  entryIndex: number
  exitIndex: number
}

export function makeTrades(seed = 3, count = 24): Trade[] {
  const rand = rng(seed * 1013904223)
  const trades: Trade[] = []
  let day = 2
  let idx = 10
  for (let i = 0; i < count; i++) {
    const side: 'BUY' | 'SELL' = rand() > 0.42 ? 'BUY' : 'SELL'
    const entryPrice = round2(61500 + rand() * 2400)
    const move = (rand() - 0.4) * 1200
    const exitPrice = round2(entryPrice + (side === 'BUY' ? move : -move))
    const pl = round2(((exitPrice - entryPrice) / entryPrice) * 100 * (side === 'BUY' ? 1 : -1))
    const eIdx = idx
    const xIdx = idx + 2 + Math.floor(rand() * 4)
    idx = xIdx + 1 + Math.floor(rand() * 3)
    trades.push({
      n: i + 1,
      entryTime: `2026-0${1 + (day % 6)}-${String(2 + (i % 26)).padStart(2, '0')} ${String(9 + (i % 12)).padStart(2, '0')}:15`,
      side,
      entryPrice,
      exitTime: `2026-0${1 + (day % 6)}-${String(2 + (i % 26)).padStart(2, '0')} ${String(11 + (i % 10)).padStart(2, '0')}:45`,
      exitPrice,
      pl,
      result: pl >= 0 ? 'WIN' : 'LOSS',
      entryIndex: eIdx,
      exitIndex: xIdx,
    })
    day++
  }
  return trades
}

export type NewsItem = {
  id: string
  published: string
  source: string
  headline: string
  coin: string
  sentiment: 'POSITIVE' | 'NEUTRAL' | 'NEGATIVE'
  score: number
  excerpt: string
  model: string
  analyzed: string
}

export const NEWS: NewsItem[] = [
  {
    id: 'n1',
    published: '12 min ago',
    source: 'CoinDesk',
    headline: 'Bitcoin gains as institutional inflows accelerate',
    coin: 'BTC',
    sentiment: 'POSITIVE',
    score: 0.84,
    excerpt:
      'Spot ETF inflows extended a fourth consecutive session as desks reported steady allocation demand, pushing BTC back above the 63k handle.',
    model: 'FinSent-v2.3',
    analyzed: '18:24:12',
  },
  {
    id: 'n2',
    published: '38 min ago',
    source: 'The Block',
    headline: 'Derivatives open interest steadies after weekend unwind',
    coin: 'BTC',
    sentiment: 'NEUTRAL',
    score: 0.51,
    excerpt:
      'Funding rates normalized across major venues, suggesting positioning has reset without a directional lean into the US session.',
    model: 'FinSent-v2.3',
    analyzed: '18:02:44',
  },
  {
    id: 'n3',
    published: '1h ago',
    source: 'Reuters',
    headline: 'Crypto markets face renewed macro volatility',
    coin: 'BTC',
    sentiment: 'NEGATIVE',
    score: 0.71,
    excerpt:
      'Stronger-than-expected inflation data revived rate-cut uncertainty, pressuring risk assets and dragging major tokens off intraday highs.',
    model: 'FinSent-v2.3',
    analyzed: '17:31:09',
  },
  {
    id: 'n4',
    published: '2h ago',
    source: 'Bloomberg',
    headline: 'Exchange reserves fall to multi-month lows',
    coin: 'BTC',
    sentiment: 'POSITIVE',
    score: 0.68,
    excerpt:
      'On-chain data shows continued withdrawal of BTC from centralized venues, a pattern analysts associate with reduced near-term sell pressure.',
    model: 'FinSent-v2.3',
    analyzed: '16:48:20',
  },
  {
    id: 'n5',
    published: '3h ago',
    source: 'CoinTelegraph',
    headline: 'Layer-2 activity cools as fees normalize',
    coin: 'ETH',
    sentiment: 'NEUTRAL',
    score: 0.47,
    excerpt:
      'Transaction throughput reverted to baseline after a brief spike, with no material change in settlement assurances.',
    model: 'FinSent-v2.3',
    analyzed: '15:59:03',
  },
  {
    id: 'n6',
    published: '5h ago',
    source: 'Reuters',
    headline: 'Regulatory clarity bill advances in committee',
    coin: 'BTC',
    sentiment: 'POSITIVE',
    score: 0.77,
    excerpt:
      'A market-structure proposal cleared an initial vote, offering firms a clearer path on custody and disclosure requirements.',
    model: 'FinSent-v2.3',
    analyzed: '13:22:51',
  },
]

export type RunRow = {
  id: string
  type: 'Search' | 'Backtest'
  space: string
  status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'
  started: string
  duration: string
  tested: number | null
  failed: number
  top1: number | null
  generator: string
  seed: number
  reason?: string
}

export const RUNS: RunRow[] = [
  { id: 'SR-0184', type: 'Search', space: 'MA·RSI·BB·SR (2–4)', status: 'RUNNING', started: '18:12:04', duration: '00:12:19', tested: 364, failed: 3, top1: 84.1, generator: 'Random Search v1', seed: 424242 },
  { id: 'BT-1841', type: 'Backtest', space: 'MA + RSI + SR v2', status: 'COMPLETED', started: '17:58:41', duration: '00:00:22', tested: 1, failed: 0, top1: 81.7, generator: '—', seed: 424242 },
  { id: 'SR-0183', type: 'Search', space: 'RSI·SR (2–3)', status: 'COMPLETED', started: '16:40:10', duration: '00:41:52', tested: 2000, failed: 11, top1: 82.9, generator: 'Random Search v1', seed: 90210 },
  { id: 'BT-1839', type: 'Backtest', space: 'MA50', status: 'COMPLETED', started: '16:20:33', duration: '00:00:18', tested: 1, failed: 0, top1: 63.5, generator: '—', seed: 11111 },
  { id: 'SR-0182', type: 'Search', space: 'MA·BB (2)', status: 'FAILED', started: '15:02:11', duration: '00:03:40', tested: 96, failed: 96, top1: null, generator: 'Random Search v1', seed: 7, reason: 'Dataset checksum mismatch on shard 3' },
  { id: 'SR-0181', type: 'Search', space: 'MA·RSI·SR (2–4)', status: 'CANCELLED', started: '14:11:48', duration: '00:19:05', tested: 512, failed: 4, top1: 80.2, generator: 'Random Search v1', seed: 31337 },
  { id: 'BT-1838', type: 'Backtest', space: 'BB20', status: 'QUEUED', started: '—', duration: '—', tested: null, failed: 0, top1: null, generator: '—', seed: 55 },
]

export const CANDIDATE_NAMES = [
  'MA20 + RSI14',
  'RSI14 + SR',
  'MA50 + BB20',
  'MA20 + BB20',
  'RSI21 + SR',
  'MA20 + RSI14 + SR',
  'BB20 + SR',
  'MA50 + RSI14',
]
