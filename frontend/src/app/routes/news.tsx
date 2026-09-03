import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { createNewsQueryOptions, type FetchLike } from '../../features/news/api/newsApi'
import type { NewsQuery, NewsSentimentLabel } from '../../features/news/types'
import { NEWS_RANGE_HOURS } from '../../config'
import { News, type NewsStatus } from '../../screens/News'

export type NewsRouteProps = {
  fetchImpl?: FetchLike
  initialCoin?: string
  initialRange?: string
  initialPage?: number
  pageSize?: number
}

/**
 * Translate the UI's coin/date-range/page filters into the typed NewsQuery.
 * A range is a look-back window: `publishedAfter` is `now - width`, and
 * `publishedBefore` is `now`. Coin 'All' (and an unknown range) is omitted so
 * the API does not narrow the result set.
 */
export function buildNewsQuery(
  input: { coin?: string; sentiment?: NewsSentimentLabel | 'All'; range?: string; page?: number; pageSize?: number },
  now: Date = new Date(),
): NewsQuery {
  const query: NewsQuery = {
    page: input.page ?? 1,
    pageSize: input.pageSize ?? 25,
  }
  if (input.coin && input.coin !== 'All') {
    query.coin = input.coin
  }
  if (input.sentiment && input.sentiment !== 'All') {
    query.sentiment = input.sentiment
  }
  const hours = input.range ? NEWS_RANGE_HOURS[input.range] : undefined
  if (hours !== undefined) {
    query.publishedBefore = now.toISOString()
    query.publishedAfter = new Date(now.getTime() - hours * 3_600_000).toISOString()
  }
  return query
}

/**
 * Production News route: owns the coin / date-range / page filter state and the
 * TanStack Query lifecycle. The data is handed to the presentational <News/>.
 */
export function ConnectedNewsRoute({
  fetchImpl,
  initialCoin = 'All',
  initialRange = '7D',
  initialPage = 1,
  pageSize = 25,
}: NewsRouteProps) {
  const [coin, setCoin] = useState(initialCoin)
  const [sentiment, setSentiment] = useState<NewsSentimentLabel | 'All'>('All')
  const [range, setRange] = useState(initialRange)
  const [page, setPage] = useState(initialPage)

  const query = useMemo<NewsQuery>(
    () => buildNewsQuery({ coin, sentiment, range, page, pageSize }),
    [coin, sentiment, range, page, pageSize],
  )

  const { data, error, isError, refetch } = useQuery(createNewsQueryOptions(query, { fetchImpl }))

  let status: NewsStatus
  if (isError) {
    status = 'error'
  } else if (!data) {
    status = 'loading'
  } else if (data.items.length === 0) {
    status = 'empty'
  } else {
    status = 'success'
  }

  return (
    <News
      status={status}
      items={data?.items ?? []}
      total={data?.total ?? 0}
      page={page}
      pageSize={pageSize}
      coin={coin}
      sentiment={sentiment}
      range={range}
      errorMessage={error instanceof Error ? error.message : 'The news request could not be served.'}
      onRetry={() => {
        void refetch()
      }}
      onCoinChange={(next) => {
        setCoin(next)
        setPage(1)
      }}
      onSentimentChange={(next) => {
        setSentiment(next)
        setPage(1)
      }}
      onRangeChange={(next) => {
        setRange(next)
        setPage(1)
      }}
      onPageChange={setPage}
    />
  )
}

export default ConnectedNewsRoute
