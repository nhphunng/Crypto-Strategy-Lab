import {
  parseCandlePage, parseDataset, parseDefinition, parseEquityPage, parseEvaluation,
  parsePolicies, parseResult, parseRun, parseStrategies, parseTradePage,
} from '../schemas'
import type {
  BacktestStrategy, DatasetCandle, EquityPoint, PolicyBundle, SingleBacktestInput,
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
    const result = await this.request(`/api/v1/backtest-runs/${run.id}/start`, parseResult, { method: 'POST', signal: input.signal })
    const evaluation = await this.request('/api/v1/evaluation-results', parseEvaluation, {
      method: 'POST', signal: input.signal, body: JSON.stringify({ backtestResultId: result.id,
        evaluationPolicyId: input.policies.evaluationPolicy.id, evaluationPolicyVersion: input.policies.evaluationPolicy.version,
        scoringPolicyId: input.policies.scoringPolicy.id, scoringPolicyVersion: input.policies.scoringPolicy.version }),
    })
    const [trades, equity, candles] = await Promise.all([
      this.loadAllTrades(result.id, input.signal), this.loadAllEquity(result.id, input.signal), this.loadAllCandles(completeDataset.datasetId, input.signal),
    ])
    return { dataset: completeDataset, definition, run, result, evaluation, trades, equity, candles }
  }

  private async waitForDataset(datasetId: string, signal?: AbortSignal) {
    for (let attempt = 0; attempt < 60; attempt += 1) {
      if (attempt > 0) await new Promise<void>((resolve, reject) => {
        const timer = globalThis.setTimeout(resolve, 1000)
        signal?.addEventListener('abort', () => { globalThis.clearTimeout(timer); reject(signal.reason) }, { once: true })
      })
      const dataset = await this.request(`/api/v1/market-data/datasets/${datasetId}`, parseDataset, { signal })
      if (dataset.status === 'COMPLETE') return dataset
      if (dataset.status === 'FAILED' || dataset.status === 'INCOMPLETE') throw new Error(`Dataset materialization failed: ${dataset.failureCode ?? dataset.status}`)
    }
    throw new Error('Dataset materialization timed out.')
  }

  private async loadAllTrades(resultId: string, signal?: AbortSignal): Promise<BacktestTrade[]> {
    const items: BacktestTrade[] = []
    for (let page = 1; ; page += 1) {
      const value = await this.request(`/api/v1/backtest-results/${resultId}/trades?page=${page}&pageSize=200`, parseTradePage, { signal })
      items.push(...value.items)
      if (value.nextCursor === null) return items
    }
  }

  private async loadAllEquity(resultId: string, signal?: AbortSignal): Promise<EquityPoint[]> {
    const items: EquityPoint[] = []
    for (let page = 1; ; page += 1) {
      const value = await this.request(`/api/v1/backtest-results/${resultId}/equity-curve?page=${page}&pageSize=200`, parseEquityPage, { signal })
      items.push(...value.items)
      if (value.nextCursor === null) return items
    }
  }

  private async loadAllCandles(datasetId: string, signal?: AbortSignal): Promise<DatasetCandle[]> {
    const items: DatasetCandle[] = []
    let cursor: string | null = null
    do {
      const params = new URLSearchParams({ pageSize: '500' })
      if (cursor) params.set('cursor', cursor)
      const value = await this.request(`/api/v1/market-data/datasets/${datasetId}/candles?${params}`, parseCandlePage, { signal })
      items.push(...value.items); cursor = value.hasMore ? value.nextCursor : null
    } while (cursor !== null)
    return items
  }
}

export function createBacktestApi(options: { baseUrl?: string; fetcher?: FetchLike } = {}) {
  return new BacktestApi(options)
}
