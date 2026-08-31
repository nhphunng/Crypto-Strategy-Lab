import { describe, expect, it, vi } from 'vitest'

import {
  createNewsQueryOptions,
  fetchNews,
  newsQueryKey,
  NewsRequestError,
} from './newsApi'

const newsItem = {
  newsId: '9d67943c-d95a-4da8-9505-bda81236ea0d',
  title: 'Bitcoin gains after market update',
  content: 'A normalized RSS summary.',
  source: 'Cointelegraph',
  publishedAt: '2026-08-30T12:00:00.000Z',
  crawledAt: '2026-08-30T12:02:00.000Z',
  relatedCoins: ['BTC'],
  url: 'https://example.com/bitcoin-gains',
  sentiment: null,
}

function successEnvelope(item: unknown = newsItem) {
  return {
    success: true,
    message: 'News loaded.',
    data: {
      items: [item],
      page: 2,
      pageSize: 25,
      total: 26,
    },
    timestamp: '2026-08-30T12:04:00.000Z',
    requestId: 'request-news-1',
  }
}

function jsonResponse(body: unknown, init?: ResponseInit): Response {
  return new Response(JSON.stringify(body), {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
}

describe('news API', () => {
  it('serializes every supported news query parameter', async () => {
    const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(jsonResponse(successEnvelope()))

    await fetchNews(
      {
        coin: 'BTC',
        publishedAfter: '2026-08-23T00:00:00.000Z',
        publishedBefore: '2026-08-30T00:00:00.000Z',
        page: 2,
        pageSize: 25,
      },
      { fetchImpl },
    )

    const [input] = fetchImpl.mock.calls[0]
    const url = new URL(String(input))
    expect(url.pathname).toBe('/api/v1/news')
    expect(Object.fromEntries(url.searchParams)).toEqual({
      coin: 'BTC',
      publishedAfter: '2026-08-23T00:00:00.000Z',
      publishedBefore: '2026-08-30T00:00:00.000Z',
      page: '2',
      pageSize: '25',
    })
  })

  it('accepts a null sentiment analysis', async () => {
    const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(jsonResponse(successEnvelope()))

    const page = await fetchNews({}, { fetchImpl })

    expect(page.items[0]?.sentiment).toBeNull()
  })

  it('accepts a versioned sentiment analysis', async () => {
    const sentiment = {
      label: 'POSITIVE',
      score: '0.840000',
      modelId: 'finsent',
      modelVersion: '2.3.0',
      analyzedAt: '2026-08-30T12:03:00.000Z',
    }
    const fetchImpl = vi
      .fn<typeof fetch>()
      .mockResolvedValue(jsonResponse(successEnvelope({ ...newsItem, sentiment })))

    const page = await fetchNews({}, { fetchImpl })

    expect(page.items[0]?.sentiment).toEqual(sentiment)
  })

  it.each([
    ['date', { ...newsItem, publishedAt: 'not-a-date' }],
    [
      'label',
      {
        ...newsItem,
        sentiment: {
          label: 'MIXED',
          score: '0.500000',
          modelId: 'finsent',
          modelVersion: '2.3.0',
          analyzedAt: '2026-08-30T12:03:00.000Z',
        },
      },
    ],
    [
      'decimal score',
      {
        ...newsItem,
        sentiment: {
          label: 'NEUTRAL',
          score: 'not-a-decimal',
          modelId: 'finsent',
          modelVersion: '2.3.0',
          analyzedAt: '2026-08-30T12:03:00.000Z',
        },
      },
    ],
  ])('rejects an invalid %s with NEWS_CONTRACT_INVALID', async (_field, invalidItem) => {
    const fetchImpl = vi
      .fn<typeof fetch>()
      .mockResolvedValue(jsonResponse(successEnvelope(invalidItem)))

    const error = await fetchNews({}, { fetchImpl }).catch((caught: unknown) => caught)

    expect(error).toBeInstanceOf(NewsRequestError)
    expect(error).toMatchObject({
      status: 200,
      detail: { code: 'NEWS_CONTRACT_INVALID' },
    })
  })

  it('maps backend error envelopes to NewsRequestError', async () => {
    const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(
      jsonResponse(
        {
          success: false,
          message: 'The News query is invalid.',
          error: {
            code: 'NEWS_QUERY_INVALID',
            details: { coin: 'DOGE' },
          },
          timestamp: '2026-08-30T12:04:00.000Z',
          requestId: 'request-news-error-1',
        },
        { status: 422 },
      ),
    )

    const error = await fetchNews({ coin: 'DOGE' }, { fetchImpl }).catch(
      (caught: unknown) => caught,
    )

    expect(error).toBeInstanceOf(NewsRequestError)
    expect(error).toMatchObject({
      status: 422,
      detail: {
        code: 'NEWS_QUERY_INVALID',
        message: 'The News query is invalid.',
        details: { coin: 'DOGE' },
      },
    })
  })

  it('uses the News query key in TanStack query options', () => {
    const query = { coin: 'ETH', page: 3, pageSize: 10 }

    const options = createNewsQueryOptions(query)

    expect(options.queryKey).toEqual(newsQueryKey(query))
    expect(options.queryKey).toEqual(['news', query])
  })

  it('forwards TanStack Query AbortSignal to fetch', async () => {
    const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(jsonResponse(successEnvelope()))
    const controller = new AbortController()
    const options = createNewsQueryOptions({ coin: 'BTC' }, { fetchImpl })
    expect(options.queryFn).toBeTypeOf('function')
    if (typeof options.queryFn !== 'function') throw new Error('Expected a query function')

    await options.queryFn({ signal: controller.signal } as never)

    expect(fetchImpl).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ signal: controller.signal }),
    )
  })
})
