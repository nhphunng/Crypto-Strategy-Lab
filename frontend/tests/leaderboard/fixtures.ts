import type {
  LeaderboardSnapshot,
  LeaderboardUpdatedEvent,
  RankedResultDetail,
  TradePage,
  VisualizationData,
} from '../../src/features/leaderboard/types'

const DISCLAIMER =
  'Simulated historical analysis only. Past simulated performance is not investment advice and does not guarantee future results.'

export function snapshotFixture(): LeaderboardSnapshot {
  return {
    leaderboardId: 'board-1',
    scopeKey: 'pair:BTCUSDT|timeframe:15m|run:*',
    scoringPolicyId: 'balanced',
    scoringPolicyVersion: '2',
    rankBy: 'OVERALL_SCORE',
    k: 10,
    projectionVersion: 41,
    updatedAt: '2026-08-13T03:30:00.000Z',
    runState: 'RUNNING',
    metricMetadata: [
      { metric: 'OVERALL_SCORE', direction: 'DESC', unit: 'SCORE' },
      { metric: 'TOTAL_RETURN', direction: 'DESC', unit: 'PERCENT' },
      { metric: 'WIN_RATE', direction: 'DESC', unit: 'PERCENT' },
      { metric: 'MAX_DRAWDOWN', direction: 'ASC', unit: 'PERCENT' },
      { metric: 'NUMBER_OF_TRADES', direction: 'DESC', unit: 'COUNT' },
      { metric: 'SHARPE_RATIO', direction: 'DESC', unit: 'RATIO' },
    ],
    entries: [
      entryFixture('eval-1', 1, '92.5', '38.4', '11.2', 4, '2.1'),
      entryFixture('eval-2', 2, '88', '31.7', '13.4', 3, '1.84'),
      entryFixture('eval-3', 3, '64', '0', '0', 0, null),
    ],
    pagination: { page: 1, pageSize: 25, total: 3 },
    disclaimer: DISCLAIMER,
  }
}

export function entryFixture(
  id: string,
  rank: number,
  score: string,
  totalReturn: string,
  maxDrawdown: string,
  numberOfTrades: number,
  sharpeRatio: string | null,
) {
  return {
    evaluationResultId: id,
    rank,
    projectionVersion: 41,
    score,
    strategy: {
      strategyId: `strategy-${rank}`,
      strategyVersion: '3',
      displayName: `Strategy ${rank}`,
      members: [{ strategyId: `member-${rank}`, strategyVersion: '3', displayName: 'Member' }],
    },
    pair: 'BTCUSDT',
    timeframe: '15m',
    datasetId: 'dataset-1',
    startTime: '2026-07-01T00:00:00.000Z',
    endTime: '2026-07-03T00:00:00.000Z',
    metrics: {
      totalReturn,
      winRate: '55',
      maxDrawdown,
      numberOfTrades,
      sharpeRatio,
    },
    scoringPolicyId: 'balanced',
    scoringPolicyVersion: '2',
    updatedAt: '2026-08-13T03:30:00.000Z',
  }
}

export function eventFixture(
  projectionVersion: number,
  overrides: Partial<LeaderboardUpdatedEvent['payload']> = {},
  eventId = `event-${projectionVersion}`,
): LeaderboardUpdatedEvent {
  return {
    eventType: 'LEADERBOARD_UPDATED',
    version: 1,
    eventId,
    occurredAt: '2026-08-13T03:31:00.000Z',
    requestId: 'req-1',
    runId: 'run-1',
    jobId: 'job-1',
    payload: {
      leaderboardId: 'board-1',
      scopeKey: 'pair:BTCUSDT|timeframe:15m|run:*',
      scoringPolicyId: 'balanced',
      scoringPolicyVersion: '2',
      rankBy: 'OVERALL_SCORE',
      k: 10,
      projectionVersion,
      updatedAt: '2026-08-13T03:31:00.000Z',
      entryCount: 3,
      changed: {
        addedEvaluationResultIds: ['eval-4'],
        removedEvaluationResultIds: [],
        movedEvaluationResultIds: ['eval-2'],
      },
      topOne: {
        evaluationResultId: 'eval-1',
        strategyId: 'strategy-1',
        strategyVersion: '3',
        rank: 1,
        score: '92.5',
      },
      runState: 'RUNNING',
      ...overrides,
    },
  }
}

export function detailFixture(): RankedResultDetail {
  return {
    entry: entryFixture('eval-1', 1, '92.5', '38.4', '11.2', 3, '2.1'),
    provenance: {
      evaluationResultId: 'eval-1',
      backtestResultId: 'result-1',
      runId: 'run-1',
      jobId: 'job-1',
      strategyId: 'strategy-1',
      strategyVersion: '3',
      datasetId: 'dataset-1',
      executionConfig: { initialCapital: '10000', feeRate: '0.0004' },
      resultChecksum: 'checksum-1',
      scoringPolicyId: 'balanced',
      scoringPolicyVersion: '2',
    },
    candles: { state: 'AVAILABLE', count: 192, reason: null },
    overlays: { state: 'UNAVAILABLE', count: 0, reason: 'No overlay descriptor is published.' },
    signals: { state: 'AVAILABLE', count: 7, reason: null },
    trades: { state: 'AVAILABLE', count: 3, reason: null },
    disclaimer: DISCLAIMER,
  }
}

export function visualizationFixture(): VisualizationData {
  return {
    pair: 'BTCUSDT',
    timeframe: '15m',
    startTime: '2026-07-01T00:00:00.000Z',
    endTime: '2026-07-01T06:00:00.000Z',
    availability: {
      candles: { state: 'AVAILABLE', count: 3, reason: null },
      overlays: { state: 'AVAILABLE', count: 1, reason: null },
      signals: { state: 'AVAILABLE', count: 2, reason: null },
      trades: { state: 'AVAILABLE', count: 1, reason: null },
    },
    candles: [
      {
        openTime: '2026-07-01T00:00:00.000Z',
        open: '100000',
        high: '100120',
        low: '99880',
        close: '100040',
        volume: '12.5',
      },
      {
        openTime: '2026-07-01T00:15:00.000Z',
        open: '100040',
        high: '100200',
        low: '99900',
        close: '100150',
        volume: '13.5',
      },
      {
        openTime: '2026-07-01T00:30:00.000Z',
        open: '100150',
        high: '100300',
        low: '100000',
        close: '100260',
        volume: '11.5',
      },
    ],
    overlays: [
      {
        id: 'overlay-1',
        kind: 'LINE',
        label: 'Trend line',
        styleToken: 'PRIMARY_INDICATOR',
        sourceStrategyId: 'unknown-future-strategy',
        sourceStrategyVersion: '9',
        points: [
          { time: '2026-07-01T00:00:00.000Z', value: '100010' },
          { time: '2026-07-01T00:15:00.000Z', value: '100120' },
        ],
      },
    ],
    markers: [
      {
        id: 'signal-1',
        type: 'BUY',
        time: '2026-07-01T00:00:00.000Z',
        price: '100040',
        label: 'BUY',
        shape: 'TRIANGLE_UP',
        tone: 'POSITIVE',
        sourceStrategyId: 'strategy-1',
        sourceStrategyVersion: '3',
        signalId: 'signal-1',
        tradeId: null,
      },
      {
        id: 'trade-1-entry',
        type: 'ENTRY',
        time: '2026-07-01T00:00:00.000Z',
        price: '100040',
        label: 'ENTRY #1',
        shape: 'ENTRY_OUTLINED',
        tone: 'INFO',
        sourceStrategyId: 'strategy-1',
        sourceStrategyVersion: '3',
        signalId: null,
        tradeId: 'trade-1',
      },
      {
        id: 'trade-1-exit',
        type: 'EXIT',
        time: '2026-07-01T00:30:00.000Z',
        price: '100260',
        label: 'EXIT #1',
        shape: 'EXIT_OUTLINED',
        tone: 'INFO',
        sourceStrategyId: 'strategy-1',
        sourceStrategyVersion: '3',
        signalId: null,
        tradeId: 'trade-1',
      },
      {
        id: 'signal-hold',
        type: 'HOLD',
        time: '2026-07-01T00:15:00.000Z',
        price: '100150',
        label: 'HOLD',
        shape: 'DIAMOND',
        tone: 'NEUTRAL',
        sourceStrategyId: 'strategy-1',
        sourceStrategyVersion: '3',
        signalId: 'signal-hold',
        tradeId: null,
      },
    ],
    unalignedMarkers: [
      {
        marker: {
          id: 'signal-unaligned',
          type: 'BUY',
          time: '2026-07-01T00:07:00.000Z',
          price: null,
          label: 'BUY',
          shape: 'TRIANGLE_UP',
          tone: 'POSITIVE',
          sourceStrategyId: 'strategy-1',
          sourceStrategyVersion: '3',
          signalId: 'signal-unaligned',
          tradeId: null,
        },
        reason: 'No Candle in the loaded range matches this Signal timestamp.',
      },
    ],
  }
}

export function tradePageFixture(): TradePage {
  return {
    items: [
      tradeFixture('trade-1', '2026-07-01T00:00:00.000Z', '2026-07-01T00:30:00.000Z', '11'),
      tradeFixture('trade-2', '2026-07-01T01:00:00.000Z', '2026-07-01T01:30:00.000Z', '-4'),
      tradeFixture('trade-3', '2026-07-01T02:00:00.000Z', '2026-07-01T02:30:00.000Z', '7.5'),
    ],
    pagination: { page: 1, pageSize: 25, total: 3 },
  }
}

function tradeFixture(id: string, entryTime: string, exitTime: string, returnPercent: string) {
  return {
    tradeId: id,
    entrySignalId: `${id}-entry-signal`,
    exitSignalId: `${id}-exit-signal`,
    entryTime,
    entryPrice: '100040',
    exitTime,
    exitPrice: '100260',
    side: 'LONG',
    quantity: '0.05',
    profitLoss: '11',
    returnPercent,
  }
}
