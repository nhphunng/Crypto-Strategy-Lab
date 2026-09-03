import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'

import { buildNewsQuery, ConnectedNewsRoute } from '../../app/routes/news'
import { formatPublishedAt } from '../../screens/News'
import type { NewsItem } from '../../features/news/types'
import { NEWS_RANGE_HOURS } from '../../config'

// ---------------------------------------------------------------------------
// fixtures
// ---------------------------------------------------------------------------

const baseItem = {
  newsId: 'news-1',
  title: 'Bitcoin gains as institutional inflows accelerate',
  content: 'Spot ETF inflows extended a fourth consecutive session.',
  source: 'CoinDesk',
  publishedAt: '2026-08-30T12:00:00.000Z',
  crawledAt: '2026-08-30T12:02:00.000Z',
  relatedCoins: ['BTC'],
  url: 'https://example.com/bitcoin-gains',
  sentiment: null,
} as const

function item(overrides: Record<string, unknown> = {}): NewsItem {
  return { ...baseItem, ...overrides } as unknown as NewsItem
}

function page(items: NewsItem[] = [item()], overrides: Record<string, unknown> = {}) {
  return { items, page: 1, pageSize: 25, total: items.length, ...overrides }
}

function jsonResponse(body: unknown, init?: ResponseInit): Response {
  return new Response(JSON.stringify(body), {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
}

function successEnvelope(body: unknown) {
  return {
    success: true,
    message: 'News loaded.',
    data: body,
    timestamp: '2026-08-30T12:04:00.000Z',
    requestId: 'request-news-route',
  }
}

function fetchOk(body: unknown) {
  return vi.fn<typeof fetch>().mockImplementation(async () => jsonResponse(successEnvelope(body)))
}

// ---------------------------------------------------------------------------
// harness
// ---------------------------------------------------------------------------

function renderRoute(ui: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return { ...render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>), client }
}

const allCoins = ['BTC', 'ETH', 'All'] as const

// ---------------------------------------------------------------------------
// buildNewsQuery
// ---------------------------------------------------------------------------

describe('buildNewsQuery', () => {
  const NOW = new Date('2026-08-30T12:00:00.000Z')

  it('maps a 7D range to a publishedAfter/publishedBefore window and carries paging', () => {
    expect(
      buildNewsQuery({ coin: 'BTC', range: '7D', page: 2, pageSize: 10 }, NOW),
    ).toEqual({
      coin: 'BTC',
      page: 2,
      pageSize: 10,
      publishedAfter: '2026-08-23T12:00:00.000Z',
      publishedBefore: '2026-08-30T12:00:00.000Z',
    })
  })

  it('omits the coin filter when All and omits the window when range is unknown', () => {
    expect(
      buildNewsQuery({ coin: 'All', range: '7D', page: 1, pageSize: 25 }, NOW),
    ).toEqual({
      page: 1,
      pageSize: 25,
      publishedAfter: '2026-08-23T12:00:00.000Z',
      publishedBefore: '2026-08-30T12:00:00.000Z',
    })
    expect(buildNewsQuery({ coin: 'BTC', page: 1, pageSize: 25 }, NOW)).toEqual({
      coin: 'BTC',
      page: 1,
      pageSize: 25,
    })
  })

  it('honours every configured range width', () => {
    for (const range of Object.keys(NEWS_RANGE_HOURS)) {
      const q = buildNewsQuery({ range, page: 1, pageSize: 25 }, NOW)
      const hours = NEWS_RANGE_HOURS[range]
      expect(q.publishedAfter).toBe(new Date(NOW.getTime() - hours * 3_600_000).toISOString())
      expect(q.publishedBefore).toBe(NOW.toISOString())
    }
  })
})

// ---------------------------------------------------------------------------
// ConnectedNewsRoute
// ---------------------------------------------------------------------------

describe('ConnectedNewsRoute', () => {
  it('renders API rows with a formatted publishedAt and an external article link', async () => {
    const fetchImpl = fetchOk(page([item()], { total: 1 }))
    renderRoute(<ConnectedNewsRoute fetchImpl={fetchImpl} />)

    expect(await screen.findByText(/Bitcoin gains as institutional inflows/)).toBeInTheDocument()
    expect(screen.getByText('CoinDesk')).toBeInTheDocument()
    // ISO publishedAt is reformatted into a readable date, never shown raw.
    expect(screen.getByText(new RegExp(formatPublishedAt('2026-08-30T12:00:00.000Z')))).toBeInTheDocument()
    expect(screen.queryByText('2026-08-30T12:00:00.000Z')).not.toBeInTheDocument()

    const link = screen.getByRole('link', { name: /Bitcoin gains as institutional inflows/ })
    expect(link).toHaveAttribute('href', 'https://example.com/bitcoin-gains')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('renders Pending analysis for null sentiment and never fabricates a model or score', async () => {
    const fetchImpl = fetchOk(page([item()], { total: 1 }))
    renderRoute(<ConnectedNewsRoute fetchImpl={fetchImpl} />)

    expect(await screen.findByText('Pending analysis')).toBeInTheDocument()
    expect(screen.queryByText(/FinSent-v2\.3/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Positive \d+%/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Neutral \d+%/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Negative \d+%/)).not.toBeInTheDocument()
  })

  it('renders the versioned sentiment analysis and never the legacy model string', async () => {
    const sentiment = {
      label: 'POSITIVE' as const,
      score: '0.840000',
      modelId: 'finsent',
      modelVersion: '2.3.0',
      analyzedAt: '2026-08-30T12:03:00.000Z',
    }
    const fetchImpl = fetchOk(page([item({ sentiment })], { total: 1 }))
    renderRoute(<ConnectedNewsRoute fetchImpl={fetchImpl} />)

    expect(await screen.findByText(/POSITIVE/)).toBeInTheDocument()
    expect(screen.getAllByText(/0\.84/).length).toBeGreaterThan(0)
    expect(screen.queryByText(/FinSent-v2\.3/)).not.toBeInTheDocument()
  })

  it('renders every related coin for an item', async () => {
    const fetchImpl = fetchOk(page([item({ relatedCoins: ['BTC', 'ETH', 'SOL'] })], { total: 1 }))
    renderRoute(<ConnectedNewsRoute fetchImpl={fetchImpl} />)

    await screen.findByText(/Bitcoin gains as institutional inflows/)
    expect(screen.getByText('BTC · ETH · SOL')).toBeInTheDocument()
  })

  it('requeries the API when the coin, date range, or page changes', async () => {
    const fetchImpl = fetchOk(page([item()], { pageSize: 25, total: 30 }))
    renderRoute(<ConnectedNewsRoute fetchImpl={fetchImpl} />)
    await screen.findByText(/Bitcoin gains as institutional inflows/)
    const user = userEvent.setup()

    // coin -> ETH
    await user.click(screen.getByRole('button', { name: 'ETH' }))
    await waitFor(() => {
      const lastUrl = new URL(String(fetchImpl.mock.calls.at(-1)?.[0]))
      expect(lastUrl.searchParams.get('coin')).toBe('ETH')
    })

    // date range -> 30D (publishedAfter shifts by 30 days)
    await user.click(screen.getByRole('button', { name: '30D' }))
    await waitFor(() => {
      const lastUrl = new URL(String(fetchImpl.mock.calls.at(-1)?.[0]))
      const after = lastUrl.searchParams.get('publishedAfter')
      const before = lastUrl.searchParams.get('publishedBefore')
      expect(after).toBeDefined()
      expect(before).toBeDefined()
      const start = new Date(String(after)).getTime()
      const end = new Date(String(before)).getTime()
      expect(end - start).toBeGreaterThan(29 * 24 * 3_600_000)
    })

    // page -> 2
    await user.click(screen.getByRole('button', { name: 'Next page' }))
    await waitFor(() => {
      const lastUrl = new URL(String(fetchImpl.mock.calls.at(-1)?.[0]))
      expect(lastUrl.searchParams.get('page')).toBe('2')
    })
  })

  it('shows a loading state while the request is in flight', async () => {
    let release!: () => void
    const pending = new Promise<void>((resolve) => {
      release = resolve
    })
    const fetchImpl = vi.fn<typeof fetch>().mockImplementation(async () => {
      await pending
      return jsonResponse(successEnvelope(page([item()], { total: 1 })))
    })

    renderRoute(<ConnectedNewsRoute fetchImpl={fetchImpl} />)
    expect(screen.getByTestId('news-loading')).toBeInTheDocument()

    release()
    expect(await screen.findByText(/Bitcoin gains as institutional inflows/)).toBeInTheDocument()
  })

  it('shows an empty state when the API returns no rows', async () => {
    const fetchImpl = fetchOk(page([], { total: 0 }))
    renderRoute(<ConnectedNewsRoute fetchImpl={fetchImpl} />)

    expect(await screen.findByText(/No news found/)).toBeInTheDocument()
  })

  it('shows an error state with a retry that refetches successfully', async () => {
    const fetchImpl = vi.fn<typeof fetch>()
    fetchImpl.mockRejectedValueOnce(
      jsonResponse(
        { success: false, message: 'The News query is invalid.', error: { code: 'NEWS_QUERY_INVALID' } },
        { status: 422 },
      ),
    )
    renderRoute(<ConnectedNewsRoute fetchImpl={fetchImpl} />)

    const retry = await screen.findByRole('button', { name: /retry the request/i })
    fetchImpl.mockResolvedValueOnce(jsonResponse(successEnvelope(page([item()], { total: 1 }))))

    const user = userEvent.setup()
    await user.click(retry)

    expect(await screen.findByText(/Bitcoin gains as institutional inflows/)).toBeInTheDocument()
  })

  it('filters by sentiment on the server and resets pagination', async () => {
    const fetchImpl = fetchOk(page([item()], { total: 1 }))
    renderRoute(<ConnectedNewsRoute fetchImpl={fetchImpl} initialPage={2} />)

    expect(await screen.findByText(/Bitcoin gains as institutional inflows/)).toBeInTheDocument()
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Positive' }))
    await waitFor(() => {
      const url = new URL(String(fetchImpl.mock.calls.at(-1)?.[0]))
      expect(url.searchParams.get('sentiment')).toBe('POSITIVE')
      expect(url.searchParams.get('page')).toBe('1')
    })
    await user.click(within(screen.getByRole('group', { name: 'Sentiment filter' })).getByRole('button', { name: 'All' }))
    await waitFor(() => {
      const url = new URL(String(fetchImpl.mock.calls.at(-1)?.[0]))
      expect(url.searchParams.has('sentiment')).toBe(false)
    })
  })

  it('refreshes pending sentiment in both the table and the open drawer', async () => {
    const fetchImpl = fetchOk(page([item()]))
    const { client } = renderRoute(<ConnectedNewsRoute fetchImpl={fetchImpl} />)
    const row = await screen.findByRole('row', { name: `Inspect ${baseItem.title}` })
    await userEvent.setup().click(row)
    expect(within(screen.getByRole('dialog')).getByText('Available after sentiment analysis completes')).toBeInTheDocument()
    fetchImpl.mockImplementation(async () => jsonResponse(successEnvelope(page([item({
      sentiment: { label: 'POSITIVE', score: '0.912345', modelId: 'ProsusAI/finbert', modelVersion: 'pinned', analyzedAt: '2026-08-30T12:03:00.000Z' },
    })]))))
    await act(async () => { await client.invalidateQueries({ queryKey: ['news'] }) })
    expect(await within(screen.getByRole('dialog')).findByText(/POSITIVE · 0.91/)).toBeInTheDocument()
    expect(within(row).getByText(/POSITIVE · 0.91/)).toBeInTheDocument()
    expect(screen.queryByText('Available after sentiment analysis completes')).not.toBeInTheDocument()
  })

  it('removes the simulate-degraded affordance', async () => {
    const fetchImpl = fetchOk(page([item()], { total: 1 }))
    renderRoute(<ConnectedNewsRoute fetchImpl={fetchImpl} />)

    await screen.findByText(/Bitcoin gains as institutional inflows/)
    expect(screen.queryByRole('button', { name: /Simulate degraded/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Restore sentiment/i })).not.toBeInTheDocument()
    expect(screen.queryByText(/Sentiment unavailable/)).not.toBeInTheDocument()
  })

  it('initialises the coin filter to All unless an initial coin is provided', async () => {
    const fetchImpl = fetchOk(page([item()], { total: 1 }))
    renderRoute(<ConnectedNewsRoute fetchImpl={fetchImpl} />)

    await screen.findByText(/Bitcoin gains as institutional inflows/)
    const coinGroup = screen.getByRole('group', { name: 'Coin filter' })
    const all = within(coinGroup).getByRole('button', { name: 'All' })
    expect(all).toHaveAttribute('aria-pressed', 'true')
    for (const coin of allCoins) {
      expect(within(coinGroup).getByRole('button', { name: coin })).toBeInTheDocument()
    }
  })
})
