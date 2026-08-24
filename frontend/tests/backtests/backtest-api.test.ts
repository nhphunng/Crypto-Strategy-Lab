import { describe, expect, it, vi } from 'vitest'

import { createBacktestApi } from '../../src/features/backtests/api/backtestApi'

const envelope = (data: unknown) => ({
  success: true,
  message: 'ok',
  timestamp: '2026-08-24T00:00:00.000Z',
  requestId: 'request-1',
  data,
})

const strategy = {
  strategyId: 'ma',
  strategyType: 'MA',
  displayName: 'Simple Moving Average Crossover',
  strategyVersion: '1.0.0',
  contractVersion: '1.0.0',
  status: 'AVAILABLE',
  capabilities: ['REASON'],
  origin: 'BUILT_IN',
  generationProvenanceId: null,
  generatedArtifactFingerprint: null,
  parameters: [{
    name: 'period', description: 'Close-price window', valueType: 'INTEGER',
    defaultValue: 20, minimum: 2, maximum: 500, required: false,
  }],
}

const policies = {
  executionPolicy: { id: '00000000-0000-4000-8000-000000000001', policyId: 'next-open-long-only', version: '1.0.0' },
  evaluationPolicy: { id: '00000000-0000-4000-8000-000000000002', policyId: 'standard-metrics', version: '1.0.0' },
  scoringPolicy: { id: '00000000-0000-4000-8000-000000000003', policyId: 'balanced', version: '1.0.0', name: 'Balanced v1' },
}

describe('Feature 004 REST workflow', () => {
  it('sends exact immutable identities and returns backend-owned results', async () => {
    const requested: { path: string; body?: unknown }[] = []
    const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(String(input))
      requested.push({ path: `${url.pathname}${url.search}`, body: init?.body ? JSON.parse(String(init.body)) : undefined })
      const page = (data: unknown, status = 200) => new Response(JSON.stringify(envelope(data)), { status })
      if (url.pathname === '/api/v1/strategies') return page({ strategies: [strategy] })
      if (url.pathname === '/api/v1/backtest-evaluation/policies') return page(policies)
      if (url.pathname === '/api/v1/market-data/datasets' && init?.method === 'POST') return page({
        schemaVersion: '1', datasetId: '10000000-0000-4000-8000-000000000001',
        selection: { provider: 'BINANCE', pair: 'BTCUSDT', timeframe: '15m' },
        range: { startTime: '2026-08-01T00:00:00.000Z', endTime: '2026-08-02T00:00:00.000Z' },
        status: 'COMPLETE', candleCount: 96, checksum: 'a'.repeat(64), failureCode: null,
        createdAt: '2026-08-24T00:00:00.000Z', updatedAt: '2026-08-24T00:00:00.000Z', completedAt: '2026-08-24T00:00:00.000Z',
      }, 201)
      if (url.pathname === '/api/v1/strategy-definitions') return page({
        definitionId: '00000000-0000-0000-0000-00000000238d', strategyId: 'ma', strategyType: 'MA',
        strategyVersion: '1.0.0', contractVersion: '1.0.0', parameters: { period: 20 },
        parameterSchemaFingerprint: 'b'.repeat(64), contentFingerprint: 'c'.repeat(64),
        createdAt: '2026-08-24T00:00:00.000Z', origin: 'BUILT_IN',
      }, 201)
      if (url.pathname === '/api/v1/backtest-runs' && init?.method === 'POST') return page({
        id: '30000000-0000-4000-8000-000000000001', jobId: '40000000-0000-4000-8000-000000000001', status: 'REQUESTED',
        datasetId: '10000000-0000-4000-8000-000000000001', strategyDefinitionId: '00000000-0000-0000-0000-00000000238d',
        executionPolicyId: policies.executionPolicy.id, executionPolicyVersion: '1.0.0', initialCapital: '10000', feeRate: '0.0004',
        slippageRate: '0.0002', randomSeed: 424242, requestedAt: '2026-08-24T00:00:00.000Z', completedAt: null, failureCode: null,
      }, 201)
      if (url.pathname.endsWith('/start')) return page({
        id: '50000000-0000-4000-8000-000000000001', runId: '30000000-0000-4000-8000-000000000001',
        jobId: '40000000-0000-4000-8000-000000000001', resultChecksum: 'd'.repeat(64), historyState: 'EVALUABLE', tradeState: 'HAS_TRADES',
        initialCapital: '10000', finalEquity: '10100', signalCount: 96, tradeCount: 1, equityPointCount: 96,
        provenance: { datasetId: '10000000-0000-4000-8000-000000000001', datasetSchemaVersion: '1', datasetChecksum: 'a'.repeat(64),
          strategyDefinitionId: '00000000-0000-0000-0000-00000000238d', strategyId: 'ma', strategyVersion: '1.0.0', contractVersion: '1.0.0',
          executionPolicyId: policies.executionPolicy.id, executionPolicyVersion: '1.0.0', executionConfigFingerprint: 'e'.repeat(64) },
        analysisType: 'HISTORICAL_SIMULATION', disclaimer: 'Historical simulation only.',
      })
      if (url.pathname === '/api/v1/evaluation-results') return page({
        id: '60000000-0000-4000-8000-000000000001', backtestResultId: '50000000-0000-4000-8000-000000000001',
        jobId: '40000000-0000-4000-8000-000000000001', runId: '30000000-0000-4000-8000-000000000001', strategyId: 'ma', strategyVersion: '1.0.0',
        datasetId: '10000000-0000-4000-8000-000000000001', pair: 'BTCUSDT', timeframe: '15m', startTime: '2026-08-01T00:00:00.000Z', endTime: '2026-08-02T00:00:00.000Z',
        executionConfig: {}, metrics: { totalReturn: '1', winRate: '100', maxDrawdown: '0.5', numberOfTrades: 1, profitFactor: null, sharpeRatio: '1.2' },
        score: '70', eligible: true, exclusionReasons: [], evaluationPolicyId: policies.evaluationPolicy.id, evaluationPolicyVersion: '1.0.0',
        scoringPolicyId: policies.scoringPolicy.id, scoringPolicyVersion: '1.0.0', evaluatedAt: '2026-08-24T00:00:00.000Z', contentFingerprint: 'f'.repeat(64),
        analysisType: 'HISTORICAL_SIMULATION', disclaimer: 'Historical simulation only.',
      }, 201)
      if (url.pathname.endsWith('/trades')) return page({ items: [{
        id: '70000000-0000-4000-8000-000000000001', sequence: 0, entrySignalId: '80000000-0000-4000-8000-000000000001', exitSignalId: null,
        entryTime: '2026-08-01T01:00:00.000Z', exitTime: '2026-08-01T02:00:00.000Z', entryReferencePrice: '100', exitReferencePrice: '102',
        entryPrice: '100.02', exitPrice: '101.98', side: 'LONG', quantity: '99', entryFee: '4', exitFee: '4', profitLoss: '100', returnPercent: '1', closeReason: 'END_OF_RANGE',
      }], nextCursor: null })
      if (url.pathname.endsWith('/equity-curve')) return page({ items: [{ position: 0, candleOpenTime: '2026-08-01T00:00:00.000Z', valuedAt: '2026-08-01T00:14:59.999Z', closePrice: '100', cash: '10000', quantity: '0', positionValue: '0', equity: '10000' }], nextCursor: null })
      if (url.pathname.endsWith('/candles')) return page({ schemaVersion: '1', datasetId: '10000000-0000-4000-8000-000000000001', candles: [{ provider: 'BINANCE', pair: 'BTCUSDT', timeframe: '15m', openTime: '2026-08-01T00:00:00.000Z', closeTime: '2026-08-01T00:14:59.999Z', open: '99', high: '101', low: '98', close: '100', volume: '10', closed: true, receivedAt: '2026-08-01T00:15:00.000Z' }], nextCursor: null, hasMore: false })
      throw new Error(`unexpected request ${url.pathname}`)
    })
    const api = createBacktestApi({ baseUrl: 'http://localhost:8000', fetcher })
    const catalog = await api.loadCatalog()
    const result = await api.runSingleBacktest({
      strategy: catalog.strategies[0], parameters: { period: 20 }, policies: catalog.policies,
      selection: { provider: 'BINANCE', pair: 'BTCUSDT', timeframe: '15m' },
      range: { startTime: '2026-08-01T00:00:00.000Z', endTime: '2026-08-02T00:00:00.000Z' },
      initialCapital: '10000', feeRate: '0.0004', slippageRate: '0.0002', randomSeed: 424242,
      jobId: '40000000-0000-4000-8000-000000000001',
    })

    expect(result.evaluation.metrics.totalReturn).toBe('1')
    expect(result.trades).toHaveLength(1)
    expect(result.equity).toHaveLength(1)
    expect(result.candles).toHaveLength(1)
    expect(requested.find((item) => item.path === '/api/v1/backtest-runs')?.body).toMatchObject({
      datasetChecksum: 'a'.repeat(64), strategyDefinitionId: '00000000-0000-0000-0000-00000000238d',
      executionPolicyId: policies.executionPolicy.id,
    })
  })

  it('fails closed when a response violates the runtime contract', async () => {
    const api = createBacktestApi({ fetcher: vi.fn(async () => new Response(JSON.stringify(envelope({ strategies: [{ strategyId: 42 }] })), { status: 200 })) })
    await expect(api.loadCatalog()).rejects.toThrow(/strategies\.strategies\[0\]/)
  })
})
