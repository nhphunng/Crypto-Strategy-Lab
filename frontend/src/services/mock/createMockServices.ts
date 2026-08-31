import {
  LEADERBOARD,
  MARKETS,
  RUNS,
  SEARCH_RUN,
  STRATEGIES,
  TIMEFRAMES,
  CANDIDATE_NAMES,
  makeCandles,
  makeTrades,
  signalMarkers,
} from '../../lib/mock'
import type { AppServices } from '../ports'

const normalize = (value: string) => value.trim().toLowerCase()

const OPERATIONS_SNAPSHOT = {
  pipeline: ['Generate', 'Backtest', 'Evaluate', 'Rank', 'Improve'],
  dependencies: [
    { name: 'Market Data Provider', status: 'HEALTHY', required: true, lag: '84ms', last: 'now' },
    { name: 'Realtime Stream', status: 'CONNECTED', required: true, lag: '2s', last: 'now' },
    { name: 'Database', status: 'HEALTHY', required: true, lag: '11ms', last: 'now' },
    { name: 'Queue', status: 'HEALTHY', required: true, lag: '—', last: 'now' },
    { name: 'Backtest Service', status: 'HEALTHY', required: true, lag: '6.8/s', last: 'now' },
    { name: 'News Provider', status: 'DEGRADED', required: false, lag: 'timeout', last: '4m ago' },
    { name: 'Sentiment Service', status: 'HEALTHY', required: false, lag: '120ms', last: 'now' },
  ],
  workers: [
    { id: 'Worker 01', status: 'RUNNING', job: 'BT-1842', util: 82 },
    { id: 'Worker 02', status: 'RUNNING', job: 'BT-1843', util: 78 },
    { id: 'Worker 03', status: 'IDLE', job: null, util: 0 },
    { id: 'Worker 04', status: 'RUNNING', job: 'BT-1844', util: 91 },
  ],
  events: [
    { t: '18:22:14', kind: 'BacktestCompleted', ref: 'BT-1841', detail: 'Score 81.7', cat: 'Backtest' },
    { t: '18:22:16', kind: 'StrategyEvaluated', ref: 'CS-0844', detail: 'Score 86.4', cat: 'Search' },
    { t: '18:22:16', kind: 'LeaderboardUpdated', ref: 'Rank #1', detail: 'MA20 + RSI14 + SR', cat: 'Ranking' },
    { t: '18:22:19', kind: 'NewsProvider', ref: 'DEGRADED', detail: 'retrying', cat: 'News' },
    { t: '18:22:22', kind: 'BacktestStarted', ref: 'BT-1844', detail: 'Worker-04', cat: 'Backtest' },
    { t: '18:22:25', kind: 'CandidateGenerated', ref: '#1843', detail: 'RSI14 + SR', cat: 'Search' },
    { t: '18:22:27', kind: 'RetryScheduled', ref: 'BT-1836', detail: 'attempt 2/3', cat: 'Backtest' },
    { t: '18:22:31', kind: 'MarketSync', ref: 'BTCUSDT', detail: 'candle 15m', cat: 'Market' },
  ],
  eventCategories: ['All', 'Market', 'Search', 'Backtest', 'Ranking', 'News', 'Sentiment'],
} as const

export function createMockServices(): AppServices {
  return {
    market: {
      timeframes: TIMEFRAMES,
      listMarkets(query = '') {
        const needle = normalize(query)
        if (!needle) return MARKETS
        return MARKETS.filter((market) =>
          [market.pair, market.base, market.name, market.display].some((value) =>
            normalize(value).includes(needle),
          ),
        )
      },
      getMarket(pair) {
        return MARKETS.find((market) => market.pair === pair)
      },
      getCandles: makeCandles,
      getSignalMarkers: signalMarkers,
    },
    strategies: {
      listMethods: () => STRATEGIES,
      getMethod: (id) => STRATEGIES.find((strategy) => strategy.id === id),
    },
    backtests: {
      candidateNames: CANDIDATE_NAMES,
      searchRun: SEARCH_RUN,
      listRuns: () => RUNS,
      makeTrades,
    },
    leaderboard: {
      listEntries: () => LEADERBOARD,
    },
    operations: {
      now: () => '18:24:12',
      getSnapshot: () => OPERATIONS_SNAPSHOT,
    },
  }
}
