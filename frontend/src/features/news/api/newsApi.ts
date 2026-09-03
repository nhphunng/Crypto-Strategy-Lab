import { queryOptions } from '@tanstack/react-query'

import { ContractError, parseNewsPage } from '../schemas'
import type { NewsApiError, NewsPage, NewsQuery } from '../types'

export const API_BASE_URL: string =
  (import.meta.env?.VITE_API_BASE_URL as string | undefined) ??
  globalThis.location?.origin ??
  'http://localhost:8000'

export type FetchLike = typeof globalThis.fetch

export class NewsRequestError extends Error {
  constructor(
    readonly status: number,
    readonly detail: NewsApiError,
  ) {
    super(detail.message)
    this.name = 'NewsRequestError'
  }
}

export type NewsRequestOptions = {
  fetchImpl?: FetchLike
  signal?: AbortSignal
}

function newsParams(query: NewsQuery): URLSearchParams {
  const params = new URLSearchParams()
  if (query.coin !== undefined) params.set('coin', query.coin)
  if (query.sentiment !== undefined) params.set('sentiment', query.sentiment)
  if (query.publishedAfter !== undefined) params.set('publishedAfter', query.publishedAfter)
  if (query.publishedBefore !== undefined) params.set('publishedBefore', query.publishedBefore)
  if (query.page !== undefined) params.set('page', String(query.page))
  if (query.pageSize !== undefined) params.set('pageSize', String(query.pageSize))
  return params
}

export function newsQueryKey(query: NewsQuery) {
  return ['news', query] as const
}

export function createNewsQueryOptions(
  query: NewsQuery,
  options: NewsRequestOptions = {},
) {
  return queryOptions({
    queryKey: newsQueryKey(query),
    queryFn: ({ signal }) => fetchNews(query, { ...options, signal }),
    refetchInterval: 15_000,
  })
}

export async function fetchNews(
  query: NewsQuery = {},
  options: NewsRequestOptions = {},
): Promise<NewsPage> {
  const params = newsParams(query)
  const queryString = params.toString()
  const response = await (options.fetchImpl ?? globalThis.fetch)(
    `${API_BASE_URL}/api/v1/news${queryString ? `?${queryString}` : ''}`,
    {
      headers: { Accept: 'application/json' },
      signal: options.signal,
    },
  )
  const body: unknown = await response.json().catch(() => null)
  const envelope = (body ?? {}) as Record<string, unknown>
  if (!response.ok) {
    const error = (envelope.error ?? {}) as Record<string, unknown>
    const details = error.details
    throw new NewsRequestError(response.status, {
      code: typeof error.code === 'string' ? error.code : 'NEWS_REQUEST_FAILED',
      message:
        typeof envelope.message === 'string'
          ? envelope.message
          : 'The request could not be served.',
      ...(typeof details === 'object' && details !== null && !Array.isArray(details)
        ? { details: details as Record<string, unknown> }
        : {}),
    })
  }
  try {
    return parseNewsPage(envelope.data)
  } catch (error) {
    if (error instanceof ContractError) {
      throw new NewsRequestError(response.status, {
        code: 'NEWS_CONTRACT_INVALID',
        message: error.message,
      })
    }
    throw error
  }
}
