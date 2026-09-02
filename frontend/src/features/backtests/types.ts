export type ParameterValue = string | number

export type StrategyParameter = {
  name: string
  description: string
  valueType: 'INTEGER' | 'DECIMAL'
  defaultValue: ParameterValue | null
  minimum: ParameterValue | null
  maximum: ParameterValue | null
  required: boolean
}

export type BacktestStrategy = {
  strategyId: string
  strategyType: string
  displayName: string
  strategyVersion: string
  contractVersion: string
  status: string
  origin: string
  parameters: StrategyParameter[]
}

export type PolicyIdentity = { id: string; policyId: string; version: string }
export type PolicyBundle = {
  executionPolicy: PolicyIdentity
  evaluationPolicy: PolicyIdentity
  scoringPolicy: PolicyIdentity & { name: string }
}

export type MarketSelection = { provider: string; pair: string; timeframe: string }
export type TimeRange = { startTime: string; endTime: string }

export type CandleDataset = {
  schemaVersion: '1'
  datasetId: string
  selection: MarketSelection
  range: TimeRange
  status: string
  candleCount: number | null
  checksum: string | null
  failureCode: string | null
  createdAt: string
  updatedAt: string
  completedAt: string | null
}

export type StrategyDefinition = {
  definitionId: string
  strategyId: string
  strategyType: string
  strategyVersion: string
  contractVersion: string
  parameters: Record<string, ParameterValue>
  parameterSchemaFingerprint: string
  contentFingerprint: string
  createdAt: string
  origin: string
}

export type BacktestRun = {
  id: string
  jobId: string
  status: 'REQUESTED' | 'RUNNING' | 'COMPLETED' | 'FAILED'
  datasetId: string
  strategyDefinitionId: string
  executionPolicyId: string
  executionPolicyVersion: string
  initialCapital: string
  feeRate: string
  slippageRate: string
  randomSeed: number
  requestedAt: string
  completedAt: string | null
  failureCode: string | null
}

export type BacktestResult = {
  id: string
  runId: string
  jobId: string
  resultChecksum: string
  historyState: string
  tradeState: string
  initialCapital: string
  finalEquity: string
  signalCount: number
  tradeCount: number
  equityPointCount: number
  provenance: {
    datasetId: string
    datasetSchemaVersion: string
    datasetChecksum: string
    strategyDefinitionId: string
    strategyId: string
    strategyVersion: string
    contractVersion: string
    executionPolicyId: string
    executionPolicyVersion: string
    executionConfigFingerprint: string
  }
  analysisType: 'HISTORICAL_SIMULATION'
  disclaimer: string
}

export type EvaluationResult = {
  id: string
  backtestResultId: string
  jobId: string
  runId: string
  strategyId: string
  strategyVersion: string
  datasetId: string
  pair: string
  timeframe: string
  startTime: string
  endTime: string
  executionConfig: Record<string, unknown>
  metrics: {
    totalReturn: string
    winRate: string
    maxDrawdown: string
    numberOfTrades: number
    profitFactor: string | null
    sharpeRatio: string | null
  }
  score: string
  eligible: boolean
  exclusionReasons: string[]
  evaluationPolicyId: string
  evaluationPolicyVersion: string
  scoringPolicyId: string
  scoringPolicyVersion: string
  evaluatedAt: string
  contentFingerprint: string
  analysisType: 'HISTORICAL_SIMULATION'
  disclaimer: string
}

export type BacktestTrade = {
  id: string
  sequence: number
  entrySignalId: string
  exitSignalId: string | null
  entryTime: string
  exitTime: string
  entryReferencePrice: string
  exitReferencePrice: string
  entryPrice: string
  exitPrice: string
  side: string
  quantity: string
  entryFee: string
  exitFee: string
  profitLoss: string
  returnPercent: string
  closeReason: string
}

export type EquityPoint = {
  position: number
  candleOpenTime: string
  valuedAt: string
  closePrice: string
  cash: string
  quantity: string
  positionValue: string
  equity: string
}

export type DatasetCandle = {
  provider: string
  pair: string
  timeframe: string
  openTime: string
  closeTime: string
  open: string
  high: string
  low: string
  close: string
  volume: string
  closed: boolean
  receivedAt: string
}

export type DatasetCandlePage = {
  schemaVersion: '1'
  datasetId: string
  items: DatasetCandle[]
  nextCursor: string | null
  hasMore: boolean
}

export type SingleBacktestInput = {
  strategy: BacktestStrategy
  parameters: Record<string, ParameterValue>
  definition?: StrategyDefinition
  policies: PolicyBundle
  selection: MarketSelection
  range: TimeRange
  initialCapital: string
  feeRate: string
  slippageRate: string
  randomSeed: number
  jobId: string
  signal?: AbortSignal
}

export type SingleBacktestOutput = {
  dataset: CandleDataset
  definition: StrategyDefinition
  run: BacktestRun
  result: BacktestResult
  evaluation: EvaluationResult
  trades: BacktestTrade[]
  equity: EquityPoint[]
  candles: DatasetCandle[]
}
