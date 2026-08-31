import type {
  LeaderRow,
  MarketInfo,
  OperationsSnapshot,
  RunRow,
  SearchRun,
  Strategy,
  Timeframe,
  Trade,
} from '../domain'
import type { Candle, Marker } from '../lib/mock'

export type MarketGateway = {
  timeframes: readonly Timeframe[]
  listMarkets: (query?: string) => MarketInfo[]
  getMarket: (pair: string) => MarketInfo | undefined
  getCandles: (timeframe: Timeframe, count?: number) => Candle[]
  getSignalMarkers: (candles: Candle[], seed?: number) => Marker[]
}

export type StrategyGateway = {
  listMethods: () => Strategy[]
  getMethod: (id: string) => Strategy | undefined
}

export type BacktestGateway = {
  candidateNames: readonly string[]
  searchRun: SearchRun
  listRuns: () => RunRow[]
  makeTrades: (seed?: number, count?: number) => Trade[]
}

export type LeaderboardGateway = {
  listEntries: () => LeaderRow[]
}

export type OperationsGateway = {
  now: () => string
  getSnapshot: () => OperationsSnapshot
}

export type AppServices = {
  market: MarketGateway
  strategies: StrategyGateway
  backtests: BacktestGateway
  leaderboard: LeaderboardGateway
  operations: OperationsGateway
}
