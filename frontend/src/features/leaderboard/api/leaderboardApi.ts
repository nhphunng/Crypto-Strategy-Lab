/** Typed REST client for the leaderboard feature. */

import {
  ContractError,
  parseLeaderboardSnapshot,
  parseScoringPolicies,
  parseRankedResultDetail,
  parseTradePage,
  parseVisualization,
} from '../schemas'
import type {
  LeaderboardApiError,
  LeaderboardIdentity,
  LeaderboardSnapshot,
  LeaderboardViewState,
  RankedResultDetail,
  ScoringPolicySummary,
  TradePage,
  VisualizationData,
} from '../types'

/**
 * Same-origin by default so the Vite dev proxy and the nginx container both
 * serve `/api` and `/ws` without a cross-origin hop. Override with
 * VITE_API_BASE_URL when the API is reached directly.
 */
export const API_BASE_URL: string =
  (import.meta.env?.VITE_API_BASE_URL as string | undefined) ??
  globalThis.location?.origin ??
  'http://localhost:8000'

export class LeaderboardRequestError extends Error {
  constructor(
    readonly status: number,
    readonly detail: LeaderboardApiError,
  ) {
    super(detail.message)
    this.name = 'LeaderboardRequestError'
  }
}

export type FetchLike = typeof globalThis.fetch

function identityParams(identity: LeaderboardIdentity): URLSearchParams {
  const params = new URLSearchParams({
    scoringPolicyId: identity.scoringPolicyId,
    scoringPolicyVersion: identity.scoringPolicyVersion,
    rankBy: identity.rankBy,
    k: String(identity.k),
  })
  if (identity.pair) params.set('pair', identity.pair)
  if (identity.timeframe) params.set('timeframe', identity.timeframe)
  if (identity.runId) params.set('runId', identity.runId)
  return params
}

function viewParams(params: URLSearchParams, view: Partial<LeaderboardViewState>): URLSearchParams {
  if (view.sortBy) params.set('sortBy', view.sortBy)
  if (view.sortDirection) params.set('sortDirection', view.sortDirection)
  if (view.page) params.set('page', String(view.page))
  if (view.pageSize) params.set('pageSize', String(view.pageSize))
  for (const key of [
    'minScore',
    'minTotalReturn',
    'minWinRate',
    'maxDrawdown',
    'minSharpeRatio',
  ] as const) {
    const value = view[key]
    if (value !== undefined && value !== '') params.set(key, value)
  }
  return params
}

async function request<T>(
  path: string,
  parse: (data: unknown) => T,
  options: { fetchImpl?: FetchLike; signal?: AbortSignal } = {},
): Promise<T> {
  const fetchImpl = options.fetchImpl ?? globalThis.fetch
  const response = await fetchImpl(`${API_BASE_URL}${path}`, {
    headers: { Accept: 'application/json' },
    signal: options.signal,
  })
  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const envelope = (body ?? {}) as Record<string, unknown>
    const detail = (envelope.error ?? {}) as Record<string, unknown>
    throw new LeaderboardRequestError(response.status, {
      code: typeof detail.code === 'string' ? detail.code : 'LEADERBOARD_REQUEST_FAILED',
      message:
        typeof envelope.message === 'string' ? envelope.message : 'The request could not be served.',
      details: detail.details as Record<string, unknown> | undefined,
    })
  }
  const envelope = (body ?? {}) as Record<string, unknown>
  try {
    return parse(envelope.data)
  } catch (error) {
    if (error instanceof ContractError) {
      throw new LeaderboardRequestError(response.status, {
        code: 'LEADERBOARD_CONTRACT_INVALID',
        message: error.message,
      })
    }
    throw error
  }
}

/** Ranking definitions the backend actually publishes. */
export function fetchScoringPolicies(
  options: { fetchImpl?: FetchLike; signal?: AbortSignal } = {},
): Promise<ScoringPolicySummary[]> {
  return request('/api/v1/leaderboards/policies', parseScoringPolicies, options)
}

export function fetchLeaderboardSnapshot(
  identity: LeaderboardIdentity,
  view: Partial<LeaderboardViewState> = {},
  options: { fetchImpl?: FetchLike; signal?: AbortSignal } = {},
): Promise<LeaderboardSnapshot> {
  const params = viewParams(identityParams(identity), view)
  return request(`/api/v1/leaderboards?${params.toString()}`, parseLeaderboardSnapshot, options)
}

export function fetchRankedResultDetail(
  leaderboardId: string,
  evaluationResultId: string,
  options: { fetchImpl?: FetchLike; signal?: AbortSignal } = {},
): Promise<RankedResultDetail> {
  return request(
    `/api/v1/leaderboards/${leaderboardId}/entries/${evaluationResultId}`,
    parseRankedResultDetail,
    options,
  )
}

export function fetchRankedResultVisualization(
  leaderboardId: string,
  evaluationResultId: string,
  range: { startTime: string; endTime: string },
  options: { fetchImpl?: FetchLike; signal?: AbortSignal } = {},
): Promise<VisualizationData> {
  const params = new URLSearchParams({ startTime: range.startTime, endTime: range.endTime })
  return request(
    `/api/v1/leaderboards/${leaderboardId}/entries/${evaluationResultId}/visualization?${params.toString()}`,
    parseVisualization,
    options,
  )
}

export function fetchRankedResultTrades(
  leaderboardId: string,
  evaluationResultId: string,
  page: { page?: number; pageSize?: number; sortBy?: string; sortDirection?: string } = {},
  options: { fetchImpl?: FetchLike; signal?: AbortSignal } = {},
): Promise<TradePage> {
  const params = new URLSearchParams()
  if (page.page) params.set('page', String(page.page))
  if (page.pageSize) params.set('pageSize', String(page.pageSize))
  if (page.sortBy) params.set('sortBy', page.sortBy)
  if (page.sortDirection) params.set('sortDirection', page.sortDirection)
  const query = params.toString()
  return request(
    `/api/v1/leaderboards/${leaderboardId}/entries/${evaluationResultId}/trades${query ? `?${query}` : ''}`,
    parseTradePage,
    options,
  )
}

export function leaderboardWebSocketUrl(): string {
  const base = API_BASE_URL.replace(/^http/, 'ws')
  return `${base}/ws/v1/leaderboards`
}
