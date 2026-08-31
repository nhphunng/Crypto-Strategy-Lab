export type SearchStatus = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'
export type SearchRun = {
  id: string; type: 'SEARCH'; status: SearchStatus; datasetId: string; strategyIds: string[]
  minimumSize: number; maximumSize: number; candidateLimit: number; generated: number
  running: number; succeeded: number; failed: number; topScore: string | null
  topCandidate: string | null; currentCandidate: string | null; generator: string; seed: number
  stopReason: string | null; failureDetail: string | null; createdAt: string
  startedAt: string | null; completedAt: string | null
}
export type SearchCandidate = {
  id: string; sequence: number; displayName: string; members: Array<Record<string, unknown>>
  status: 'RUNNING' | 'COMPLETED' | 'FAILED'; score: string | null
  backtestRunId: string | null; evaluationResultId: string | null; failureCode: string | null
}
export type BacktestRunSummary = {
  id: string; jobId: string; status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED'
  datasetId: string; strategyDefinitionId: string; strategyId: string; pair: string; timeframe: string
  parentSearchRunId: string | null; candidateDisplayName: string | null; randomSeed: number
  requestedAt: string; completedAt: string | null; failureCode: string | null
}
type FetchLike = typeof globalThis.fetch

export class SearchApi {
  private readonly baseUrl: string
  private readonly fetcher: FetchLike
  constructor(options: { baseUrl?: string; fetcher?: FetchLike } = {}) {
    this.baseUrl = options.baseUrl ?? globalThis.location?.origin ?? 'http://localhost:8000'
    this.fetcher = options.fetcher ?? globalThis.fetch.bind(globalThis)
  }
  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const response = await this.fetcher(new URL(path, this.baseUrl), { ...options,
      headers: { Accept: 'application/json', ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers } })
    const body = await response.json().catch(() => ({})) as Record<string, unknown>
    if (!response.ok) throw new Error(String(body.message ?? 'Search request failed.'))
    return body.data as T
  }
  async prepareDataset(pair: string, timeframe: string, startDate: string, endDate: string, signal?: AbortSignal): Promise<string> {
    const created = await this.request<{ datasetId: string; status: string }>('/api/v1/market-data/datasets', {
      method: 'POST', signal, body: JSON.stringify({ schemaVersion: '1',
        selection: { provider: 'BINANCE', pair, timeframe },
        range: { startTime: `${startDate}T00:00:00.000Z`, endTime: `${endDate}T00:00:00.000Z` } }) })
    for (let attempt = 0; attempt < 60; attempt += 1) {
      const dataset = attempt === 0 ? created : await this.request<{ datasetId: string; status: string }>(`/api/v1/market-data/datasets/${created.datasetId}`, { signal })
      if (dataset.status === 'COMPLETE') return dataset.datasetId
      if (dataset.status === 'FAILED' || dataset.status === 'INCOMPLETE') throw new Error(`Dataset failed: ${dataset.status}`)
      await new Promise((resolve) => globalThis.setTimeout(resolve, 1000))
    }
    throw new Error('Dataset preparation timed out.')
  }
  start(input: { datasetId: string; strategyIds: string[]; minimumSize: number; maximumSize: number
    candidateLimit: number; timeoutSeconds: number; noImprovementLimit: number; seed: number }, signal?: AbortSignal) {
    return this.request<SearchRun>('/api/v1/search-runs', { method: 'POST', signal, body: JSON.stringify({
      ...input }) })
  }
  listSearchRuns(signal?: AbortSignal) { return this.request<SearchRun[]>('/api/v1/search-runs', { signal }) }
  cancel(id: string) { return this.request<SearchRun>(`/api/v1/search-runs/${id}/cancel`, { method: 'POST' }) }
  candidates(id: string, sort: 'recent' | 'score' = 'recent', signal?: AbortSignal) { return this.request<SearchCandidate[]>(`/api/v1/search-runs/${id}/candidates?limit=50&sort=${sort}`, { signal }) }
  listBacktestRuns(signal?: AbortSignal) { return this.request<BacktestRunSummary[]>('/api/v1/backtest-runs?limit=100', { signal }) }
  subscribe(id: string, onProgress: (run: SearchRun) => void): () => void {
    const url = new URL(`/ws/v1/search-runs/${id}`, this.baseUrl); url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    const socket = new WebSocket(url)
    socket.onmessage = (event) => {
      const value = JSON.parse(String(event.data)) as { eventType?: string; payload?: SearchRun }
      if (value.eventType === 'SEARCH_PROGRESS' && value.payload) onProgress(value.payload)
    }
    return () => socket.close()
  }
}
export const createSearchApi = (options: { baseUrl?: string; fetcher?: FetchLike } = {}) => new SearchApi(options)
