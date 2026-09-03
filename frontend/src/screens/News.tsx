import { useState } from 'react'
import { ArrowDownRight, ArrowUpRight, ChevronLeft, ChevronRight, Minus } from 'lucide-react'
import type { NewsItem, NewsSentimentLabel, SentimentSummary } from '../features/news/types'
import { PageHeader } from '../components/Shell'
import {
  Button,
  cn,
  Drawer,
  DrawerSection,
  EmptyState,
  ErrorState,
  KV,
  Segmented,
} from '../components/ui'

export type NewsStatus = 'loading' | 'success' | 'error' | 'empty'

export type NewsProps = {
  status: NewsStatus
  items: NewsItem[]
  total: number
  sentimentSummary?: SentimentSummary | null
  page: number
  pageSize: number
  coin: string
  sentiment: NewsSentimentLabel | 'All'
  range: string
  errorMessage?: string
  onRetry: () => void
  onCoinChange: (coin: string) => void
  onSentimentChange: (sentiment: NewsSentimentLabel | 'All') => void
  onRangeChange: (range: string) => void
  onPageChange: (page: number) => void
}

/** Format a UTC ISO instant into a readable, locale-stable timestamp. */
export function formatPublishedAt(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'UTC',
  })
}

const COIN_OPTIONS = [
  { value: 'BTC', label: 'BTC' },
  { value: 'ETH', label: 'ETH' },
  { value: 'All', label: 'All' },
]

const SENTIMENT_OPTIONS = [
  { value: 'All', label: 'All' },
  { value: 'POSITIVE', label: 'Positive' },
  { value: 'NEUTRAL', label: 'Neutral' },
  { value: 'NEGATIVE', label: 'Negative' },
]

const RANGE_OPTIONS = [
  { value: '24H', label: '24H' },
  { value: '7D', label: '7D' },
  { value: '30D', label: '30D' },
]

const SENTIMENT_HELPER = 'Available after sentiment analysis completes'

const SENTIMENT_META = {
  POSITIVE: { icon: ArrowUpRight, cls: 'text-pos' },
  NEUTRAL: { icon: Minus, cls: 'text-neutral' },
  NEGATIVE: { icon: ArrowDownRight, cls: 'text-neg' },
} as const

function SentimentTag({ item }: { item: NewsItem }) {
  const sentiment = item.sentiment
  if (!sentiment) {
    return <span className="font-mono text-[11px] text-faint">Pending analysis</span>
  }
  const meta = SENTIMENT_META[sentiment.label]
  const Icon = meta.icon
  const score = Number.parseFloat(sentiment.score)
  return (
    <span className={cn('inline-flex items-center gap-1 font-mono text-[11px] font-semibold', meta.cls)}>
      <Icon size={12} /> {sentiment.label} · {Number.isFinite(score) ? score.toFixed(2) : sentiment.score}
    </span>
  )
}

function ScoreCell({ item }: { item: NewsItem }) {
  const score = item.sentiment ? Number.parseFloat(item.sentiment.score) : Number.NaN
  if (item.sentiment && Number.isFinite(score)) {
    return <span className="font-mono tabular-nums text-dim">{score.toFixed(2)}</span>
  }
  return <span className="font-mono text-[11px] text-faint">—</span>
}

function SentimentDistribution({ summary }: { summary: SentimentSummary }) {
  const analyzed = summary.positive + summary.neutral + summary.negative
  return (
    <section aria-label="Sentiment distribution" className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-subtle bg-surface px-4 py-3 text-sm">
      <span className="text-dim">{analyzed} analyzed · {summary.pending} pending analysis</span>
      {(['positive', 'neutral', 'negative'] as const).map((label) => (
        <span key={label} className={SENTIMENT_META[label.toUpperCase() as NewsSentimentLabel].cls}>
          {label[0].toUpperCase() + label.slice(1)} {analyzed ? `${(summary[label] / analyzed * 100).toFixed(1)}%` : '—'} ({summary[label]})
        </span>
      ))}
      <span className="text-faint">All articles in the selected coin and date range</span>
    </section>
  )
}

export function News({
  status,
  items,
  total,
  sentimentSummary,
  page,
  pageSize,
  coin,
  sentiment,
  range,
  errorMessage,
  onRetry,
  onCoinChange,
  onSentimentChange,
  onRangeChange,
  onPageChange,
}: NewsProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const selected = items.find((item) => item.newsId === selectedId) ?? null
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const showPagination = total > pageSize

  return (
    <div className="flex h-full flex-col">
      <PageHeader title="News & Sentiment" />

      {/* filters */}
      <div className="flex flex-wrap items-end gap-2 border-b border-subtle bg-surface px-4 py-2 text-[12px]">
        <div className="flex flex-col gap-0.5">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-faint">Coin</span>
          <Segmented ariaLabel="Coin filter" options={COIN_OPTIONS} value={coin} onChange={onCoinChange} />
        </div>
        <div className="h-8 w-px bg-subtle" />
        <div className="flex flex-col gap-0.5">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-faint">Sentiment</span>
          <Segmented ariaLabel="Sentiment filter" options={SENTIMENT_OPTIONS} value={sentiment} onChange={(value) => onSentimentChange(value as NewsSentimentLabel | 'All')} />
        </div>
        <div className="h-8 w-px bg-subtle" />
        <div className="flex flex-col gap-0.5">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-faint">Date range</span>
          <Segmented ariaLabel="Date range" options={RANGE_OPTIONS} value={range} onChange={onRangeChange} />
        </div>
      </div>

      {sentimentSummary && status !== 'loading' && status !== 'error' && (
        <SentimentDistribution summary={sentimentSummary} />
      )}

      {/* news table */}
      <div className="min-h-0 flex-1 overflow-auto bg-surface">
        {status === 'loading' && (
          <div data-testid="news-loading" role="status" className="flex h-full items-center justify-center px-6 py-10">
            <p className="text-[12px] text-faint">Loading news…</p>
          </div>
        )}

        {status === 'error' && (
          <ErrorState
            title="News could not be loaded"
            hint={errorMessage}
            action={
              <Button variant="default" size="sm" onClick={onRetry}>
                Retry the request
              </Button>
            }
          />
        )}

        {status === 'empty' && (
          <EmptyState
            title={`No news found for ${coin} in this period.`}
            hint="Try widening the date range or clearing filters."
          />
        )}

        {status === 'success' && (
          <>
            <table className="w-full border-collapse text-[13px]">
              <thead className="sticky top-0 z-10">
                <tr className="border-b border-line bg-surface text-left text-faint">
                  {['Published', 'Source', 'Headline', 'Coin', 'Sentiment', 'Score'].map((h) => (
                    <th key={h} className="h-[34px] whitespace-nowrap px-3 text-[11px] font-semibold uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map((n) => (
                  <tr
                    key={n.newsId}
                    onClick={() => setSelectedId(n.newsId)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        setSelectedId(n.newsId)
                      }
                    }}
                    tabIndex={0}
                    aria-label={`Inspect ${n.title}`}
                    className="h-9 cursor-pointer border-b border-subtle transition-colors hover:bg-surface-hover"
                  >
                    <td className="whitespace-nowrap px-3 font-mono text-[11px] tabular-nums text-faint">{formatPublishedAt(n.publishedAt)}</td>
                    <td className="px-3 text-dim">{n.source}</td>
                    <td className="px-3 text-ink">
                      <a
                        href={n.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(event) => event.stopPropagation()}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter') event.stopPropagation()
                        }}
                        className="underline decoration-transparent underline-offset-2 transition-colors hover:text-accent hover:decoration-current"
                      >
                        {n.title}
                      </a>
                    </td>
                    <td className="px-3 font-mono text-[11px] text-dim">{n.relatedCoins.join(' · ')}</td>
                    <td className="px-3">{<SentimentTag item={n} />}</td>
                    <td className="px-3">{<ScoreCell item={n} />}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            {showPagination && (
              <div className="flex items-center justify-between border-t border-subtle bg-surface px-4 py-2 text-[12px]">
                <span className="font-mono text-faint">
                  Page {page} of {totalPages}
                </span>
                <div className="flex items-center gap-1">
                  <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => onPageChange(page - 1)} aria-label="Previous page">
                    <ChevronLeft size={14} /> Previous
                  </Button>
                  <Button variant="ghost" size="sm" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)} aria-label="Next page">
                    Next <ChevronRight size={14} />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      <Drawer open={!!selected} onClose={() => setSelectedId(null)} title={selected?.title ?? ''} subtitle={selected ? `${selected.source} · ${formatPublishedAt(selected.publishedAt)}` : ''}>
        {selected && (
          <>
            <DrawerSection title="Article">
              <p className="text-[13px] leading-relaxed text-dim">{selected.content}</p>
              <a
                href={selected.url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-3 inline-flex items-center gap-1 text-[12px] font-medium text-accent underline decoration-dotted underline-offset-2 hover:text-accent-hover"
              >
                Read article
              </a>
            </DrawerSection>
            <DrawerSection title="Analysis">
              {selected.sentiment ? (
                <>
                  <div className="mb-2"><SentimentTag item={selected} /></div>
                  <KV k="Analyzed" v={formatPublishedAt(selected.sentiment.analyzedAt)} />
                  <KV k="Model" v={`${selected.sentiment.modelId} · ${selected.sentiment.modelVersion}`} />
                  <KV k="Related coins" v={selected.relatedCoins.join(', ')} />
                </>
              ) : (
                <p className="text-[13px] text-dim">{SENTIMENT_HELPER}</p>
              )}
            </DrawerSection>
          </>
        )}
      </Drawer>
    </div>
  )
}

export default News
