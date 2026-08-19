import {
  CandlestickChart,
  History,
  Newspaper,
  ServerCog,
  Trophy,
  Workflow,
  type LucideIcon,
} from 'lucide-react'
import type { Page } from '../lib/store'
import type { Timeframe } from '../domain'

export const NAV_ITEMS: { page: Exclude<Page, 'landing'>; label: string; icon: LucideIcon }[] = [
  { page: 'market', label: 'Market', icon: CandlestickChart },
  { page: 'strategies', label: 'Strategies', icon: Workflow },
  { page: 'backtests', label: 'Backtests', icon: History },
  { page: 'leaderboard', label: 'Leaderboard', icon: Trophy },
  { page: 'news', label: 'News & Sentiment', icon: Newspaper },
  { page: 'operations', label: 'Operations', icon: ServerCog },
]

export const PAGE_PATHS: Record<Page, string> = {
  landing: '/',
  market: '/market',
  strategies: '/strategies',
  backtests: '/backtests',
  leaderboard: '/leaderboard',
  news: '/news',
  operations: '/operations',
}

export const PATH_PAGES = Object.fromEntries(
  Object.entries(PAGE_PATHS).map(([page, path]) => [path, page]),
) as Record<string, Page>

export const DEFAULT_TIMEFRAMES: Timeframe[] = ['5m', '15m', '1h', '4h']
export const CHART_LAYOUTS = ['1', '2', '4'] as const

export const WORKSPACE_DEFAULTS = {
  marketPair: 'BTCUSDT',
  watchlist: ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
  timeframe: '15m' as Timeframe,
  activeStrategy: 'MA + RSI + SR v2',
  loopTested: 1842,
  loopElapsedSeconds: 5263,
}

export const BACKTEST_DEFAULTS = {
  timeframe: '15m' as Timeframe,
  rangeLabel: '2026-01-01 → 2026-07-01',
  datasetId: 'BINANCE-BTCUSDT-15M-2026H1',
  capital: 10_000,
  feeRate: 0.0004,
  slippageRate: 0.0002,
  positionSizing: '100% equity',
  seed: 424_242,
}

export const NEWS_RANGE_HOURS: Record<string, number> = {
  '24H': 24,
  '7D': 24 * 7,
  '30D': 24 * 30,
}

export const PRODUCT_DISCLAIMER =
  'Research and simulation only. No real trades, custody, or financial advice.'

export * from './strategies'
