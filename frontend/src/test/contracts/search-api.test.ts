import { describe, expect, it, vi } from 'vitest'
import { SearchApi } from '../../features/backtests'

const run = {
  id: '00000000-0000-0000-0000-000000000001', type: 'SEARCH', status: 'QUEUED',
  datasetId: '00000000-0000-0000-0000-000000000002', strategyIds: ['ma', 'rsi'],
  minimumSize: 2, maximumSize: 2, candidateLimit: 25, generated: 0, running: 0,
  succeeded: 0, failed: 0, topScore: null, topCandidate: null, currentCandidate: null,
  generator: 'random-search@1.0.0', seed: 987654, stopReason: null, failureDetail: null,
  createdAt: '2026-08-31T00:00:00Z', startedAt: null, completedAt: null,
}

describe('strategy search API boundary', () => {
  it('sends user-selected search settings without replacing them with defaults', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ data: run })))
    const api = new SearchApi({ baseUrl: 'http://test.local', fetcher })

    await api.start({
      datasetId: run.datasetId, strategyIds: ['ma', 'rsi'], minimumSize: 2, maximumSize: 2,
      candidateLimit: 25, timeoutSeconds: 120, noImprovementLimit: 10, seed: 987654,
    })

    const options = fetcher.mock.calls[0][1] as RequestInit
    expect(JSON.parse(String(options.body))).toEqual({
      datasetId: run.datasetId, strategyIds: ['ma', 'rsi'], minimumSize: 2, maximumSize: 2,
      candidateLimit: 25, timeoutSeconds: 120, noImprovementLimit: 10, seed: 987654,
    })
  })

  it('requests recent feed and ranked Top-K independently', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ data: [] })))
    const api = new SearchApi({ baseUrl: 'http://test.local', fetcher })
    await api.candidates(run.id, 'recent')
    await api.candidates(run.id, 'score')

    expect(String(fetcher.mock.calls[0][0])).toContain('sort=recent')
    expect(String(fetcher.mock.calls[1][0])).toContain('sort=score')
  })
})
