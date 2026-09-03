/**
 * Contract-derived leaderboard types.
 *
 * These mirror `specs/005-leaderboard-visualization/contracts/openapi.yaml`.
 * Decimals stay strings so exact backend precision survives in the browser,
 * and no ranking or scoring rule is ever re-implemented here.
 */

export const RANK_METRICS = [
  'OVERALL_SCORE',
  'TOTAL_RETURN',
  'WIN_RATE',
  'MAX_DRAWDOWN',
  'SHARPE_RATIO',
] as const
export type RankMetric = (typeof RANK_METRICS)[number]

export const METRIC_NAMES = [
  'OVERALL_SCORE',
  'TOTAL_RETURN',
  'WIN_RATE',
  'MAX_DRAWDOWN',
  'NUMBER_OF_TRADES',
  'SHARPE_RATIO',
] as const
export type MetricName = (typeof METRIC_NAMES)[number]

export const LEADERBOARD_SORT_FIELDS = ['RANK', ...RANK_METRICS] as const
export type LeaderboardSortField = (typeof LEADERBOARD_SORT_FIELDS)[number]

export type SortDirection = 'ASC' | 'DESC'
export type MetricUnit = 'PERCENT' | 'RATIO' | 'COUNT' | 'SCORE'
export type RunState = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'
export type AvailabilityState = 'AVAILABLE' | 'EMPTY' | 'PARTIAL' | 'UNAVAILABLE'
export type MarkerType = 'BUY' | 'SELL' | 'HOLD' | 'ENTRY' | 'EXIT'
export type MarkerShape =
  | 'ARROW_UP'
  | 'ARROW_DOWN'
  | 'TRIANGLE_UP'
  | 'TRIANGLE_DOWN'
  | 'DIAMOND'
  | 'DOT'
  | 'ENTRY_OUTLINED'
  | 'EXIT_OUTLINED'
export type MarkerTone = 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL' | 'INFO'
export type OverlayKind = 'LINE' | 'BAND' | 'ZONE'

export type MetricDescriptor = {
  metric: MetricName
  direction: SortDirection
  unit: MetricUnit
}

export type MetricSet = {
  totalReturn: string
  winRate: string
  maxDrawdown: string
  numberOfTrades: number
  sharpeRatio: string | null
}

export type StrategyMember = {
  strategyId: string
  strategyVersion: string
  displayName: string
}

export type StrategySummary = {
  strategyId: string
  strategyVersion: string
  displayName: string
  members: StrategyMember[]
}

export type LeaderboardEntry = {
  evaluationResultId: string
  rank: number
  projectionVersion: number
  score: string
  strategy: StrategySummary
  pair: string
  timeframe: string
  datasetId: string
  startTime: string
  endTime: string
  metrics: MetricSet
  scoringPolicyId: string
  scoringPolicyVersion: string
  updatedAt: string
}

export type PageMeta = {
  page: number
  pageSize: number
  total: number
}

export type ScoringPolicySummary = {
  scoringPolicyId: string
  scoringPolicyVersion: string
  name: string
  defaultRankMetric: RankMetric
  evaluationCount: number
}

export type LeaderboardSnapshot = {
  leaderboardId: string
  scopeKey: string
  scoringPolicyId: string
  scoringPolicyVersion: string
  rankBy: RankMetric
  k: number
  projectionVersion: number
  updatedAt: string
  runState: RunState | null
  metricMetadata: MetricDescriptor[]
  entries: LeaderboardEntry[]
  pagination: PageMeta
  disclaimer: string
}

export type Availability = {
  state: AvailabilityState
  count: number
  reason: string | null
}

export type Provenance = {
  evaluationResultId: string
  backtestResultId: string
  runId: string
  jobId: string
  strategyId: string
  strategyVersion: string
  datasetId: string
  executionConfig: Record<string, unknown>
  resultChecksum: string
  scoringPolicyId: string
  scoringPolicyVersion: string
}

export type RankedResultDetail = {
  entry: LeaderboardEntry
  provenance: Provenance
  candles: Availability
  overlays: Availability
  signals: Availability
  trades: Availability
  disclaimer: string
}

export type Candle = {
  openTime: string
  open: string
  high: string
  low: string
  close: string
  volume: string
}

export type OverlayPoint = {
  time?: string | null
  value?: string | null
  upper?: string | null
  middle?: string | null
  lower?: string | null
  startTime?: string | null
  endTime?: string | null
}

export type Overlay = {
  id: string
  kind: OverlayKind
  label: string
  styleToken: string
  sourceStrategyId: string
  sourceStrategyVersion: string
  points: OverlayPoint[]
}

export type Marker = {
  id: string
  type: MarkerType
  time: string
  /** Candle opening time for placement; time remains the recorded execution instant. */
  candleTime?: string | null
  price: string | null
  label: string
  shape: MarkerShape
  tone: MarkerTone | null
  sourceStrategyId: string
  sourceStrategyVersion: string
  signalId: string | null
  tradeId: string | null
}

export type UnalignedMarker = {
  marker: Marker
  reason: string
}

export type VisualizationData = {
  pair: string
  timeframe: string
  startTime: string
  endTime: string
  availability: {
    candles: Availability
    overlays: Availability
    signals: Availability
    trades: Availability
  }
  candles: Candle[]
  overlays: Overlay[]
  markers: Marker[]
  unalignedMarkers: UnalignedMarker[]
}

export type Trade = {
  tradeId: string
  entrySignalId: string | null
  exitSignalId: string | null
  entryTime: string
  entryPrice: string
  exitTime: string
  exitPrice: string
  side: string
  quantity: string
  profitLoss: string
  returnPercent: string
}

export type TradePage = {
  items: Trade[]
  pagination: PageMeta
}

export type LeaderboardChangedSet = {
  addedEvaluationResultIds: string[]
  removedEvaluationResultIds: string[]
  movedEvaluationResultIds: string[]
}

export type LeaderboardUpdatedEvent = {
  eventType: 'LEADERBOARD_UPDATED'
  version: 1
  eventId: string
  occurredAt: string
  requestId: string | null
  runId: string | null
  jobId: string | null
  payload: {
    leaderboardId: string
    scopeKey: string
    scoringPolicyId: string
    scoringPolicyVersion: string
    rankBy: RankMetric
    k: number
    projectionVersion: number
    updatedAt: string
    entryCount: number
    changed: LeaderboardChangedSet
    topOne: {
      evaluationResultId: string
      strategyId: string
      strategyVersion: string
      rank: number
      score: string
    } | null
    runState: RunState | null
  }
}

/** Projection identity. A different K or ranking metric is a different board. */
export type LeaderboardIdentity = {
  scoringPolicyId: string
  scoringPolicyVersion: string
  rankBy: RankMetric
  k: number
  pair?: string
  timeframe?: string
  runId?: string
}

/** Presentation-only view state; it never changes Top-K membership. */
export type LeaderboardViewState = {
  sortBy: LeaderboardSortField
  sortDirection?: SortDirection
  page: number
  pageSize: number
  minScore?: string
  minTotalReturn?: string
  minWinRate?: string
  maxDrawdown?: string
  minSharpeRatio?: string
}

export type ConnectionStatus = 'CONNECTING' | 'LIVE' | 'RECONNECTING' | 'STALE'

export type LeaderboardApiError = {
  code: string
  message: string
  details?: Record<string, unknown>
}
