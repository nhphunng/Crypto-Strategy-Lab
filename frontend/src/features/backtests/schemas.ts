import type {
  BacktestResult, BacktestRun, BacktestStrategy, BacktestTrade, CandleDataset,
  DatasetCandlePage, EquityPoint, EvaluationResult, ParameterValue, PolicyBundle,
  StrategyDefinition,
} from './types'

export class BacktestContractError extends Error {
  constructor(readonly path: string, message: string) {
    super(`${path}: ${message}`)
    this.name = 'BacktestContractError'
  }
}

const DECIMAL = /^-?[0-9]+(?:\.[0-9]+)?$/
// OpenAPI `format: uuid` accepts the canonical 8-4-4-4-12 representation.
// Persisted deterministic fixture IDs may use version/variant nibble zero.
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

function record(value: unknown, path: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) throw new BacktestContractError(path, 'expected an object')
  return value as Record<string, unknown>
}
function str(value: unknown, path: string): string {
  if (typeof value !== 'string') throw new BacktestContractError(path, 'expected a string')
  return value
}
function instant(value: unknown, path: string): string {
  const result = str(value, path)
  if (!/(?:Z|[+-][0-9]{2}:[0-9]{2})$/.test(result) || Number.isNaN(Date.parse(result))) {
    throw new BacktestContractError(path, 'expected an ISO 8601 instant with an explicit timezone')
  }
  return result
}
function schemaVersion(value: unknown, path: string): '1' {
  const result = str(value, path)
  if (result !== '1') throw new BacktestContractError(path, 'expected schema version 1')
  return result
}
function nullableStr(value: unknown, path: string): string | null {
  return value === null ? null : str(value, path)
}
function uuid(value: unknown, path: string): string {
  const result = str(value, path)
  if (!UUID.test(result)) throw new BacktestContractError(path, 'expected a UUID')
  return result
}
function decimal(value: unknown, path: string): string {
  const result = str(value, path)
  if (!DECIMAL.test(result)) throw new BacktestContractError(path, 'expected a decimal string')
  return result
}
function int(value: unknown, path: string): number {
  if (typeof value !== 'number' || !Number.isInteger(value)) throw new BacktestContractError(path, 'expected an integer')
  return value
}
function bool(value: unknown, path: string): boolean {
  if (typeof value !== 'boolean') throw new BacktestContractError(path, 'expected a boolean')
  return value
}
function strings(value: unknown, path: string): string[] {
  if (!Array.isArray(value)) throw new BacktestContractError(path, 'expected an array')
  return value.map((item, index) => str(item, `${path}[${index}]`))
}
function parameter(value: unknown, path: string): ParameterValue {
  if (typeof value !== 'string' && (typeof value !== 'number' || !Number.isInteger(value))) throw new BacktestContractError(path, 'expected an exact string or integer')
  return value
}
function parameters(value: unknown, path: string): Record<string, ParameterValue> {
  const raw = record(value, path)
  return Object.fromEntries(Object.entries(raw).map(([key, item]) => [key, parameter(item, `${path}.${key}`)]))
}
function policy(value: unknown, path: string) {
  const raw = record(value, path)
  return { id: uuid(raw.id, `${path}.id`), policyId: str(raw.policyId, `${path}.policyId`), version: str(raw.version, `${path}.version`) }
}

export function parseStrategies(value: unknown): BacktestStrategy[] {
  const root = record(value, 'strategies')
  if (!Array.isArray(root.strategies)) throw new BacktestContractError('strategies.strategies', 'expected an array')
  return root.strategies.map((item, index) => {
    const path = `strategies.strategies[${index}]`; const raw = record(item, path)
    if (!Array.isArray(raw.parameters)) throw new BacktestContractError(`${path}.parameters`, 'expected an array')
    return {
      strategyId: str(raw.strategyId, `${path}.strategyId`), strategyType: str(raw.strategyType, `${path}.strategyType`),
      displayName: str(raw.displayName, `${path}.displayName`), strategyVersion: str(raw.strategyVersion, `${path}.strategyVersion`),
      contractVersion: str(raw.contractVersion, `${path}.contractVersion`), status: str(raw.status, `${path}.status`), origin: str(raw.origin, `${path}.origin`),
      parameters: raw.parameters.map((entry, parameterIndex) => { const p = `${path}.parameters[${parameterIndex}]`; const field = record(entry, p); return {
        name: str(field.name, `${p}.name`), description: str(field.description, `${p}.description`),
        valueType: str(field.valueType, `${p}.valueType`) as 'INTEGER' | 'DECIMAL',
        defaultValue: field.defaultValue === null ? null : parameter(field.defaultValue, `${p}.defaultValue`),
        minimum: field.minimum === null ? null : parameter(field.minimum, `${p}.minimum`), maximum: field.maximum === null ? null : parameter(field.maximum, `${p}.maximum`),
        required: bool(field.required, `${p}.required`),
      } }),
    }
  })
}

export function parsePolicies(value: unknown): PolicyBundle {
  const raw = record(value, 'policies'); const scoring = record(raw.scoringPolicy, 'policies.scoringPolicy')
  return { executionPolicy: policy(raw.executionPolicy, 'policies.executionPolicy'), evaluationPolicy: policy(raw.evaluationPolicy, 'policies.evaluationPolicy'), scoringPolicy: { ...policy(scoring, 'policies.scoringPolicy'), name: str(scoring.name, 'policies.scoringPolicy.name') } }
}

export function parseDataset(value: unknown): CandleDataset {
  const r = record(value, 'dataset'); const selection = record(r.selection, 'dataset.selection'); const range = record(r.range, 'dataset.range')
  return { schemaVersion: schemaVersion(r.schemaVersion, 'dataset.schemaVersion'), datasetId: uuid(r.datasetId, 'dataset.datasetId'),
    selection: { provider: str(selection.provider, 'dataset.selection.provider'), pair: str(selection.pair, 'dataset.selection.pair'), timeframe: str(selection.timeframe, 'dataset.selection.timeframe') },
    range: { startTime: instant(range.startTime, 'dataset.range.startTime'), endTime: instant(range.endTime, 'dataset.range.endTime') }, status: str(r.status, 'dataset.status'),
    candleCount: r.candleCount === null ? null : int(r.candleCount, 'dataset.candleCount'), checksum: nullableStr(r.checksum, 'dataset.checksum'), failureCode: nullableStr(r.failureCode, 'dataset.failureCode'),
    createdAt: str(r.createdAt, 'dataset.createdAt'), updatedAt: str(r.updatedAt, 'dataset.updatedAt'), completedAt: nullableStr(r.completedAt, 'dataset.completedAt') }
}

export function parseDefinition(value: unknown): StrategyDefinition {
  const r = record(value, 'definition'); return { definitionId: uuid(r.definitionId, 'definition.definitionId'), strategyId: str(r.strategyId, 'definition.strategyId'),
    strategyType: str(r.strategyType, 'definition.strategyType'), strategyVersion: str(r.strategyVersion, 'definition.strategyVersion'), contractVersion: str(r.contractVersion, 'definition.contractVersion'),
    parameters: parameters(r.parameters, 'definition.parameters'), parameterSchemaFingerprint: str(r.parameterSchemaFingerprint, 'definition.parameterSchemaFingerprint'),
    contentFingerprint: str(r.contentFingerprint, 'definition.contentFingerprint'), createdAt: str(r.createdAt, 'definition.createdAt'), origin: str(r.origin, 'definition.origin') }
}

export function parseRun(value: unknown): BacktestRun {
  const r = record(value, 'run'); const status = str(r.status, 'run.status') as BacktestRun['status']; return { id: uuid(r.id, 'run.id'), jobId: uuid(r.jobId, 'run.jobId'), status,
    datasetId: uuid(r.datasetId, 'run.datasetId'), strategyDefinitionId: uuid(r.strategyDefinitionId, 'run.strategyDefinitionId'), executionPolicyId: uuid(r.executionPolicyId, 'run.executionPolicyId'),
    executionPolicyVersion: str(r.executionPolicyVersion, 'run.executionPolicyVersion'), initialCapital: decimal(r.initialCapital, 'run.initialCapital'), feeRate: decimal(r.feeRate, 'run.feeRate'),
    slippageRate: decimal(r.slippageRate, 'run.slippageRate'), randomSeed: int(r.randomSeed, 'run.randomSeed'), requestedAt: str(r.requestedAt, 'run.requestedAt'),
    completedAt: nullableStr(r.completedAt, 'run.completedAt'), failureCode: nullableStr(r.failureCode, 'run.failureCode') }
}

export function parseResult(value: unknown): BacktestResult {
  const r = record(value, 'result'); const p = record(r.provenance, 'result.provenance'); return { id: uuid(r.id, 'result.id'), runId: uuid(r.runId, 'result.runId'), jobId: uuid(r.jobId, 'result.jobId'),
    resultChecksum: str(r.resultChecksum, 'result.resultChecksum'), historyState: str(r.historyState, 'result.historyState'), tradeState: str(r.tradeState, 'result.tradeState'),
    initialCapital: decimal(r.initialCapital, 'result.initialCapital'), finalEquity: decimal(r.finalEquity, 'result.finalEquity'), signalCount: int(r.signalCount, 'result.signalCount'), tradeCount: int(r.tradeCount, 'result.tradeCount'), equityPointCount: int(r.equityPointCount, 'result.equityPointCount'),
    provenance: { datasetId: uuid(p.datasetId, 'result.provenance.datasetId'), datasetSchemaVersion: str(p.datasetSchemaVersion, 'result.provenance.datasetSchemaVersion'), datasetChecksum: str(p.datasetChecksum, 'result.provenance.datasetChecksum'),
      strategyDefinitionId: uuid(p.strategyDefinitionId, 'result.provenance.strategyDefinitionId'), strategyId: str(p.strategyId, 'result.provenance.strategyId'), strategyVersion: str(p.strategyVersion, 'result.provenance.strategyVersion'),
      contractVersion: str(p.contractVersion, 'result.provenance.contractVersion'), executionPolicyId: uuid(p.executionPolicyId, 'result.provenance.executionPolicyId'), executionPolicyVersion: str(p.executionPolicyVersion, 'result.provenance.executionPolicyVersion'), executionConfigFingerprint: str(p.executionConfigFingerprint, 'result.provenance.executionConfigFingerprint') },
    analysisType: str(r.analysisType, 'result.analysisType') as 'HISTORICAL_SIMULATION', disclaimer: str(r.disclaimer, 'result.disclaimer') }
}

export function parseEvaluation(value: unknown): EvaluationResult {
  const r = record(value, 'evaluation'); const m = record(r.metrics, 'evaluation.metrics'); return { id: uuid(r.id, 'evaluation.id'), backtestResultId: uuid(r.backtestResultId, 'evaluation.backtestResultId'),
    jobId: uuid(r.jobId, 'evaluation.jobId'), runId: uuid(r.runId, 'evaluation.runId'), strategyId: str(r.strategyId, 'evaluation.strategyId'), strategyVersion: str(r.strategyVersion, 'evaluation.strategyVersion'),
    datasetId: uuid(r.datasetId, 'evaluation.datasetId'), pair: str(r.pair, 'evaluation.pair'), timeframe: str(r.timeframe, 'evaluation.timeframe'), startTime: str(r.startTime, 'evaluation.startTime'), endTime: str(r.endTime, 'evaluation.endTime'),
    executionConfig: record(r.executionConfig, 'evaluation.executionConfig'), metrics: { totalReturn: decimal(m.totalReturn, 'evaluation.metrics.totalReturn'), winRate: decimal(m.winRate, 'evaluation.metrics.winRate'), maxDrawdown: decimal(m.maxDrawdown, 'evaluation.metrics.maxDrawdown'), numberOfTrades: int(m.numberOfTrades, 'evaluation.metrics.numberOfTrades'), profitFactor: m.profitFactor === null ? null : decimal(m.profitFactor, 'evaluation.metrics.profitFactor'), sharpeRatio: m.sharpeRatio === null ? null : decimal(m.sharpeRatio, 'evaluation.metrics.sharpeRatio') },
    score: decimal(r.score, 'evaluation.score'), eligible: bool(r.eligible, 'evaluation.eligible'), exclusionReasons: strings(r.exclusionReasons, 'evaluation.exclusionReasons'),
    evaluationPolicyId: uuid(r.evaluationPolicyId, 'evaluation.evaluationPolicyId'), evaluationPolicyVersion: str(r.evaluationPolicyVersion, 'evaluation.evaluationPolicyVersion'), scoringPolicyId: uuid(r.scoringPolicyId, 'evaluation.scoringPolicyId'), scoringPolicyVersion: str(r.scoringPolicyVersion, 'evaluation.scoringPolicyVersion'),
    evaluatedAt: str(r.evaluatedAt, 'evaluation.evaluatedAt'), contentFingerprint: str(r.contentFingerprint, 'evaluation.contentFingerprint'), analysisType: str(r.analysisType, 'evaluation.analysisType') as 'HISTORICAL_SIMULATION', disclaimer: str(r.disclaimer, 'evaluation.disclaimer') }
}

export function parseTradePage(value: unknown): { items: BacktestTrade[]; nextCursor: string | null } {
  const r = record(value, 'trades'); if (!Array.isArray(r.items)) throw new BacktestContractError('trades.items', 'expected an array')
  return { items: r.items.map((item, index) => { const p = `trades.items[${index}]`; const t = record(item, p); return { id: uuid(t.id, `${p}.id`), sequence: int(t.sequence, `${p}.sequence`), entrySignalId: uuid(t.entrySignalId, `${p}.entrySignalId`), exitSignalId: t.exitSignalId === null ? null : uuid(t.exitSignalId, `${p}.exitSignalId`), entryTime: str(t.entryTime, `${p}.entryTime`), exitTime: str(t.exitTime, `${p}.exitTime`), entryReferencePrice: decimal(t.entryReferencePrice, `${p}.entryReferencePrice`), exitReferencePrice: decimal(t.exitReferencePrice, `${p}.exitReferencePrice`), entryPrice: decimal(t.entryPrice, `${p}.entryPrice`), exitPrice: decimal(t.exitPrice, `${p}.exitPrice`), side: str(t.side, `${p}.side`), quantity: decimal(t.quantity, `${p}.quantity`), entryFee: decimal(t.entryFee, `${p}.entryFee`), exitFee: decimal(t.exitFee, `${p}.exitFee`), profitLoss: decimal(t.profitLoss, `${p}.profitLoss`), returnPercent: decimal(t.returnPercent, `${p}.returnPercent`), closeReason: str(t.closeReason, `${p}.closeReason`) } }), nextCursor: nullableStr(r.nextCursor, 'trades.nextCursor') }
}

export function parseEquityPage(value: unknown): { items: EquityPoint[]; nextCursor: string | null } {
  const r = record(value, 'equity'); if (!Array.isArray(r.items)) throw new BacktestContractError('equity.items', 'expected an array')
  return { items: r.items.map((item, index) => { const p = `equity.items[${index}]`; const e = record(item, p); return { position: int(e.position, `${p}.position`), candleOpenTime: str(e.candleOpenTime, `${p}.candleOpenTime`), valuedAt: str(e.valuedAt, `${p}.valuedAt`), closePrice: decimal(e.closePrice, `${p}.closePrice`), cash: decimal(e.cash, `${p}.cash`), quantity: decimal(e.quantity, `${p}.quantity`), positionValue: decimal(e.positionValue, `${p}.positionValue`), equity: decimal(e.equity, `${p}.equity`) } }), nextCursor: nullableStr(r.nextCursor, 'equity.nextCursor') }
}

export function parseCandlePage(value: unknown): DatasetCandlePage {
  const r = record(value, 'candles'); if (!Array.isArray(r.candles)) throw new BacktestContractError('candles.candles', 'expected an array')
  return { schemaVersion: schemaVersion(r.schemaVersion, 'candles.schemaVersion'), datasetId: uuid(r.datasetId, 'candles.datasetId'), items: r.candles.map((item, index) => { const p = `candles.candles[${index}]`; const c = record(item, p); return { provider: str(c.provider, `${p}.provider`), pair: str(c.pair, `${p}.pair`), timeframe: str(c.timeframe, `${p}.timeframe`), openTime: instant(c.openTime, `${p}.openTime`), closeTime: instant(c.closeTime, `${p}.closeTime`), open: decimal(c.open, `${p}.open`), high: decimal(c.high, `${p}.high`), low: decimal(c.low, `${p}.low`), close: decimal(c.close, `${p}.close`), volume: decimal(c.volume, `${p}.volume`), closed: bool(c.closed, `${p}.closed`), receivedAt: instant(c.receivedAt, `${p}.receivedAt`) } }), nextCursor: nullableStr(r.nextCursor, 'candles.nextCursor'), hasMore: bool(r.hasMore, 'candles.hasMore') }
}
