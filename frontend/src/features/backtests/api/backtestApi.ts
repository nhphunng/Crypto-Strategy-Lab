import {
  BacktestContractError, parseCandlePage, parseDataset, parseDefinition, parseEquityPage, parseEvaluation,
  parsePolicies, parseResult, parseRun, parseStrategies, parseTradePage,
} from '../schemas'
import type {
  BacktestStrategy, CandleDataset, DatasetCandle, EquityPoint, PolicyBundle, SingleBacktestInput,
  SingleBacktestOutput, BacktestTrade,
} from '../types'

export class BacktestApiError extends Error {
  constructor(readonly status: number, readonly code: string, message: string, readonly requestId: string) {
    super(message)
    this.name = 'BacktestApiError'
  }
}

type FetchLike = typeof globalThis.fetch
type Parser<T> = (value: unknown) => T

function expectIdentity(path: string, actual: string, expected: string): void {
  if (actual !== expected) {
    throw new BacktestContractError(path, `expected ${expected}, received ${actual}`)
  }
}

function expectCount(path: string, actual: number, expected: number): void {
  if (actual !== expected) {
    throw new BacktestContractError(path, `expected ${expected} items, received ${actual}`)
  }
}

function abortableDelay(milliseconds: number, signal?: AbortSignal): Promise<void> {
  if (signal?.aborted) return Promise.reject(signal.reason ?? new DOMException('Aborted', 'AbortError'))
  return new Promise<void>((resolve, reject) => {
    const onAbort = () => {
      globalThis.clearTimeout(timer)
      reject(signal?.reason ?? new DOMException('Aborted', 'AbortError'))
    }
    const timer = globalThis.setTimeout(() => {
      signal?.removeEventListener('abort', onAbort)
      resolve()
    }, milliseconds)
    signal?.addEventListener('abort', onAbort, { once: true })
  })
}

function validateDatasetCandles(dataset: CandleDataset, candles: DatasetCandle[]): void {
  if (dataset.candleCount === null) {
    throw new BacktestContractError('dataset.candleCount', 'expected a completed Dataset count')
  }
  expectCount('candles.items', candles.length, dataset.candleCount)

  const rangeStart = Date.parse(dataset.range.startTime)
  const rangeEnd = Date.parse(dataset.range.endTime)
  let previousOpen = -Infinity
  candles.forEach((candle, index) => {
    const path = `candles.items[${index}]`
    expectIdentity(`${path}.provider`, candle.provider, dataset.selection.provider)
    expectIdentity(`${path}.pair`, candle.pair, dataset.selection.pair)
    expectIdentity(`${path}.timeframe`, candle.timeframe, dataset.selection.timeframe)
    if (!candle.closed) throw new BacktestContractError(`${path}.closed`, 'expected a closed Candle')

    const openTime = Date.parse(candle.openTime)
    const closeTime = Date.parse(candle.closeTime)
    if (openTime < rangeStart || closeTime >= rangeEnd || openTime > closeTime) {
      throw new BacktestContractError(`${path}.openTime`, 'Candle interval falls outside the Dataset range')
    }
    if (openTime <= previousOpen) {
      throw new BacktestContractError(`${path}.openTime`, 'Candles must be strictly ordered and unique')
    }
    previousOpen = openTime

    const open = Number(candle.open)
    const high = Number(candle.high)
    const low = Number(candle.low)
    const close = Number(candle.close)
    const volume = Number(candle.volume)
    if (![open, high, low, close, volume].every(Number.isFinite)) {
      throw new BacktestContractError(path, 'Candle values must be finite')
    }
    if (low > Math.min(open, close) || high < Math.max(open, close) || low > high) {
      throw new BacktestContractError(path, 'Candle OHLC values are inconsistent')
    }
    if (volume < 0) throw new BacktestContractError(`${path}.volume`, 'Candle volume cannot be negative')
  })
}

export class BacktestApi {
  private readonly baseUrl: string
  private readonly fetcher: FetchLike

  constructor(options: { baseUrl?: string; fetcher?: FetchLike } = {}) {
    this.baseUrl = options.baseUrl ?? globalThis.location?.origin ?? 'http://localhost:8000'
    this.fetcher = options.fetcher ?? globalThis.fetch.bind(globalThis)
  }

  private async request<T>(path: string, parser: Parser<T>, options: RequestInit = {}): Promise<T> {
    const response = await this.fetcher(new URL(path, this.baseUrl), {
      ...options,
      headers: { Accept: 'application/json', ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers },
    })
    const body: unknown = await response.json().catch(() => null)
    const envelope = typeof body === 'object' && body !== null ? body as Record<string, unknown> : {}
    if (!response.ok) {
      const detail = typeof envelope.error === 'object' && envelope.error !== null ? envelope.error as Record<string, unknown> : {}
      throw new BacktestApiError(
        response.status,
        typeof detail.code === 'string' ? detail.code : 'BACKTEST_REQUEST_FAILED',
        typeof envelope.message === 'string' ? envelope.message : 'The backtest request failed.',
        typeof envelope.requestId === 'string' ? envelope.requestId : 'unknown',
      )
    }
    return parser(envelope.data)
  }

  async loadCatalog(signal?: AbortSignal): Promise<{ strategies: BacktestStrategy[]; policies: PolicyBundle }> {
    const [strategies, policies] = await Promise.all([
      this.request('/api/v1/strategies', parseStrategies, { signal }),
      this.request('/api/v1/backtest-evaluation/policies', parsePolicies, { signal }),
    ])
    return { strategies: strategies.filter((item) => item.status === 'AVAILABLE'), policies }
  }

  async runSingleBacktest(input: SingleBacktestInput): Promise<SingleBacktestOutput> {
    const dataset = await this.request('/api/v1/market-data/datasets', parseDataset, {
      method: 'POST', signal: input.signal, body: JSON.stringify({ schemaVersion: '1', selection: input.selection, range: input.range }),
    })
    const completeDataset = dataset.status === 'COMPLETE' ? dataset : await this.waitForDataset(dataset.datasetId, input.signal)
    if (!completeDataset.checksum || (completeDataset.candleCount ?? 0) < 1) throw new Error('Dataset completed without a usable checksum or Candles.')

    const definition = input.definition ?? await this.request('/api/v1/strategy-definitions', parseDefinition, {
      method: 'POST', signal: input.signal, body: JSON.stringify({ strategyId: input.strategy.strategyId, strategyVersion: input.strategy.strategyVersion, parameters: input.parameters }),
    })
    const run = await this.request('/api/v1/backtest-runs', parseRun, {
      method: 'POST', signal: input.signal, body: JSON.stringify({
        jobId: input.jobId, datasetId: completeDataset.datasetId, datasetSchemaVersion: completeDataset.schemaVersion,
        datasetChecksum: completeDataset.checksum, strategyDefinitionId: definition.definitionId,
        strategyVersion: definition.strategyVersion, contractVersion: definition.contractVersion,
        executionPolicyId: input.policies.executionPolicy.id, executionPolicyVersion: input.policies.executionPolicy.version,
        initialCapital: input.initialCapital, feeRate: input.feeRate, slippageRate: input.slippageRate, randomSeed: input.randomSeed,
      }),
    })
    expectIdentity('run.datasetId', run.datasetId, completeDataset.datasetId)
    expectIdentity('run.strategyDefinitionId', run.strategyDefinitionId, definition.definitionId)
    expectIdentity('run.executionPolicyId', run.executionPolicyId, input.policies.executionPolicy.id)
    expectIdentity('run.executionPolicyVersion', run.executionPolicyVersion, input.policies.executionPolicy.version)
    const result = await this.request(`/api/v1/backtest-runs/${run.id}/start`, parseResult, { method: 'POST', signal: input.signal })
    // An identical input is idempotent: the backend may return the original
    // immutable result, whose runId/jobId predate this request run.
    expectIdentity('result.provenance.datasetId', result.provenance.datasetId, completeDataset.datasetId)
    expectIdentity('result.provenance.datasetSchemaVersion', result.provenance.datasetSchemaVersion, completeDataset.schemaVersion)
    expectIdentity('result.provenance.datasetChecksum', result.provenance.datasetChecksum, completeDataset.checksum)
    expectIdentity('result.provenance.strategyDefinitionId', result.provenance.strategyDefinitionId, definition.definitionId)
    expectIdentity('result.provenance.strategyId', result.provenance.strategyId, definition.strategyId)
    expectIdentity('result.provenance.strategyVersion', result.provenance.strategyVersion, definition.strategyVersion)
    const evaluation = await this.request('/api/v1/evaluation-results', parseEvaluation, {
      method: 'POST', signal: input.signal, body: JSON.stringify({ backtestResultId: result.id,
        evaluationPolicyId: input.policies.evaluationPolicy.id, evaluationPolicyVersion: input.policies.evaluationPolicy.version,
      scoringPolicyId: input.policies.scoringPolicy.id, scoringPolicyVersion: input.policies.scoringPolicy.version }),
    })
    expectIdentity('evaluation.backtestResultId', evaluation.backtestResultId, result.id)
    expectIdentity('evaluation.runId', evaluation.runId, result.runId)
    expectIdentity('evaluation.jobId', evaluation.jobId, result.jobId)
    expectIdentity('evaluation.datasetId', evaluation.datasetId, completeDataset.datasetId)
    expectIdentity('evaluation.strategyId', evaluation.strategyId, definition.strategyId)
    expectIdentity('evaluation.strategyVersion', evaluation.strategyVersion, definition.strategyVersion)
    expectIdentity('evaluation.pair', evaluation.pair, completeDataset.selection.pair)
    expectIdentity('evaluation.timeframe', evaluation.timeframe, completeDataset.selection.timeframe)
    expectIdentity('evaluation.evaluationPolicyId', evaluation.evaluationPolicyId, input.policies.evaluationPolicy.id)
    expectIdentity('evaluation.evaluationPolicyVersion', evaluation.evaluationPolicyVersion, input.policies.evaluationPolicy.version)
    expectIdentity('evaluation.scoringPolicyId', evaluation.scoringPolicyId, input.policies.scoringPolicy.id)
    expectIdentity('evaluation.scoringPolicyVersion', evaluation.scoringPolicyVersion, input.policies.scoringPolicy.version)
    const [trades, equity, candles] = await Promise.all([
      this.loadAllTrades(result.id, result.tradeCount, input.signal),
      this.loadAllEquity(result.id, result.equityPointCount, input.signal),
      this.loadDatasetCandles(completeDataset, input.signal),
    ])
    return { dataset: completeDataset, definition, run, result, evaluation, trades, equity, candles }
  }

  private async waitForDataset(datasetId: string, signal?: AbortSignal) {
    for (let attempt = 0; attempt < 60; attempt += 1) {
      if (attempt > 0) await abortableDelay(1000, signal)
      const dataset = await this.request(`/api/v1/market-data/datasets/${datasetId}`, parseDataset, { signal })
      if (dataset.status === 'COMPLETE') return dataset
      if (dataset.status === 'FAILED' || dataset.status === 'INCOMPLETE') throw new Error(`Dataset materialization failed: ${dataset.failureCode ?? dataset.status}`)
    }
    throw new Error('Dataset materialization timed out.')
  }

  private async loadAllTrades(resultId: string, expectedCount: number, signal?: AbortSignal): Promise<BacktestTrade[]> {
    const items: BacktestTrade[] = []
    for (let page = 1; ; page += 1) {
      const value = await this.request(`/api/v1/backtest-results/${resultId}/trades?page=${page}&pageSize=200`, parseTradePage, { signal })
      items.push(...value.items)
      if (items.length > expectedCount) throw new BacktestContractError('trades.items', 'received more Trades than the result declares')
      if (value.nextCursor === null) {
        expectCount('trades.items', items.length, expectedCount)
        return items
      }
      if (value.items.length === 0) throw new BacktestContractError('trades.nextCursor', 'received an empty page with a continuation cursor')
    }
  }

  private async loadAllEquity(resultId: string, expectedCount: number, signal?: AbortSignal): Promise<EquityPoint[]> {
    const items: EquityPoint[] = []
    for (let page = 1; ; page += 1) {
      const value = await this.request(`/api/v1/backtest-results/${resultId}/equity-curve?page=${page}&pageSize=200`, parseEquityPage, { signal })
      items.push(...value.items)
      if (items.length > expectedCount) throw new BacktestContractError('equity.items', 'received more Equity Points than the result declares')
      if (value.nextCursor === null) {
        expectCount('equity.items', items.length, expectedCount)
        return items
      }
      if (value.items.length === 0) throw new BacktestContractError('equity.nextCursor', 'received an empty page with a continuation cursor')
    }
  }

  async loadDatasetCandles(dataset: CandleDataset, signal?: AbortSignal): Promise<DatasetCandle[]> {
    const items: DatasetCandle[] = []
    let cursor: string | null = null
    const seenCursors = new Set<string>()
    do {
      const params = new URLSearchParams({ pageSize: '500' })
      if (cursor) params.set('cursor', cursor)
      const value = await this.request(`/api/v1/market-data/datasets/${dataset.datasetId}/candles?${params}`, parseCandlePage, { signal })
      expectIdentity('candles.schemaVersion', value.schemaVersion, dataset.schemaVersion)
      expectIdentity('candles.datasetId', value.datasetId, dataset.datasetId)
      items.push(...value.items)
      if (value.hasMore && value.nextCursor === null) {
        throw new Error('Dataset Candle page declared more data without a continuation cursor.')
      }
      if (value.hasMore && value.items.length === 0) {
        throw new BacktestContractError('candles.nextCursor', 'received an empty page with a continuation cursor')
      }
      if (value.nextCursor !== null && seenCursors.has(value.nextCursor)) {
        throw new BacktestContractError('candles.nextCursor', 'received a repeated continuation cursor')
      }
      if (value.nextCursor !== null) seenCursors.add(value.nextCursor)
      cursor = value.hasMore ? value.nextCursor : null
    } while (cursor !== null)
    validateDatasetCandles(dataset, items)
    return items
  }
}

export function createBacktestApi(options: { baseUrl?: string; fetcher?: FetchLike } = {}) {
  return new BacktestApi(options)
}
