import { useMemo, useState } from 'react'
import { ArrowDownRight, ArrowUpRight, Minus, WifiOff } from 'lucide-react'
import { useStore } from '../lib/store'
import type { NewsItem } from '../domain'
import { useServices } from '../services/registry'
import { PageHeader } from '../components/Shell'
import {
  Button,
  cn,
  DegradedNote,
  Drawer,
  DrawerSection,
  EmptyState,
  HelperText,
  KV,
  LearnTooltip,
  Segmented,
} from '../components/ui'

function SentimentTag({ s, score }: { s: NewsItem['sentiment']; score: number }) {
  const map = {
    POSITIVE: { icon: ArrowUpRight, cls: 'text-pos' },
    NEUTRAL: { icon: Minus, cls: 'text-neutral' },
    NEGATIVE: { icon: ArrowDownRight, cls: 'text-neg' },
  } as const
  const { icon: Icon, cls } = map[s]
  return (
    <span className={cn('inline-flex items-center gap-1 font-mono text-[11px] font-semibold', cls)}>
      <Icon size={12} /> {s} · {score.toFixed(2)}
    </span>
  )
}

export function News() {
  const { market } = useStore()
  const services = useServices()
  const [coin, setCoin] = useState(market.base)
  const [sentiment, setSentiment] = useState('All')
  const [range, setRange] = useState('7D')
  const [degraded, setDegraded] = useState(false)
  const [selected, setSelected] = useState<NewsItem | null>(null)

  const rows = useMemo(() => {
    return services.news.listNews({ coin, sentiment, range })
  }, [coin, sentiment, range, services])

  const dist = useMemo(() => {
    const total = Math.max(1, rows.length)
    const count = (value: NewsItem['sentiment']) => rows.filter((item) => item.sentiment === value).length
    const positive = Math.round((count('POSITIVE') / total) * 100)
    const neutral = Math.round((count('NEUTRAL') / total) * 100)
    return { positive, neutral, negative: Math.max(0, 100 - positive - neutral) }
  }, [rows])

  return (
    <div className="flex h-full flex-col">
      <PageHeader title="News & Sentiment">
        {import.meta.env?.DEV && (
          <Button variant="ghost" size="sm" onClick={() => setDegraded((d) => !d)}>
            <WifiOff size={13} /> {degraded ? 'Restore sentiment' : 'Simulate degraded'}
          </Button>
        )}
      </PageHeader>

      {/* filters */}
      <div className="flex flex-wrap items-center gap-2 border-b border-subtle bg-surface px-4 py-2 text-[12px]">
        <Segmented ariaLabel="Coin filter" options={[{ value: 'BTC', label: 'BTC' }, { value: 'ETH', label: 'ETH' }, { value: 'All', label: 'All' }]} value={coin} onChange={setCoin} />
        <div className="h-4 w-px bg-subtle" />
        <Segmented
          ariaLabel="Sentiment filter"
          options={[
            { value: 'All', label: 'All' },
            { value: 'POSITIVE', label: 'Positive' },
            { value: 'NEUTRAL', label: 'Neutral' },
            { value: 'NEGATIVE', label: 'Negative' },
          ]}
          value={sentiment}
          onChange={setSentiment}
        />
        <div className="h-4 w-px bg-subtle" />
        <Segmented ariaLabel="Date range" options={[{ value: '24H', label: '24H' }, { value: '7D', label: '7D' }, { value: '30D', label: '30D' }]} value={range} onChange={setRange} />
      </div>

      {/* sentiment summary */}
      <div className="border-b border-subtle bg-surface px-4 py-3">
        {degraded ? (
          <DegradedNote>
            Sentiment unavailable — technical analysis continues. Market and backtest features remain
            operational.
          </DegradedNote>
        ) : (
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <div className="mb-1.5 flex items-center justify-between text-[11px]">
                <LearnTooltip content="Sentiment estimates whether recent coverage sounds positive, neutral or negative. It does not predict price by itself — treat it as extra context alongside your own analysis.">
                  <span className="text-faint">Sentiment distribution</span>
                </LearnTooltip>
                <span className="font-mono text-faint">model FinSent-v2.3 · last {range}</span>
              </div>
              <div className="flex h-2.5 overflow-hidden rounded-full">
                <div className="bg-pos" style={{ width: `${dist.positive}%` }} />
                <div className="bg-neutral" style={{ width: `${dist.neutral}%` }} />
                <div className="bg-neg" style={{ width: `${dist.negative}%` }} />
              </div>
              <div className="mt-1.5 flex gap-4 font-mono text-[11px]">
                <span className="text-pos">Positive {dist.positive}%</span>
                <span className="text-neutral">Neutral {dist.neutral}%</span>
                <span className="text-neg">Negative {dist.negative}%</span>
              </div>
              <HelperText>
                Sentiment summarizes the tone of recent news. It's context, not a trade
                recommendation — a positive mood doesn't guarantee the price will rise.
              </HelperText>
            </div>
          </div>
        )}
      </div>

      {/* news table */}
      <div className="min-h-0 flex-1 overflow-auto bg-surface">
        {rows.length === 0 ? (
          <EmptyState title={`No news found for ${coin} in this period.`} hint="Try widening the date range or clearing filters." />
        ) : (
          <table className="w-full border-collapse text-[13px]">
            <thead className="sticky top-0 z-10">
              <tr className="border-b border-line bg-surface text-left text-faint">
                {['Published', 'Source', 'Headline', 'Coin', 'Sentiment', 'Score'].map((h) => (
                  <th key={h} className="h-[34px] whitespace-nowrap px-3 text-[11px] font-semibold uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((n) => (
                <tr
                  key={n.id}
                  onClick={() => setSelected(n)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault()
                      setSelected(n)
                    }
                  }}
                  tabIndex={0}
                  aria-label={`Inspect ${n.headline}`}
                  className="h-9 cursor-pointer border-b border-subtle transition-colors hover:bg-surface-hover"
                >
                  <td className="whitespace-nowrap px-3 font-mono text-[11px] tabular-nums text-faint">{n.published}</td>
                  <td className="px-3 text-dim">{n.source}</td>
                  <td className="px-3 text-ink">{n.headline}</td>
                  <td className="px-3 font-mono text-[11px] text-dim">{n.coin}</td>
                  <td className="px-3">
                    {degraded ? <span className="font-mono text-[11px] text-faint">—</span> : <SentimentTag s={n.sentiment} score={n.score} />}
                  </td>
                  <td className="px-3 font-mono tabular-nums text-dim">{degraded ? '—' : n.score.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <Drawer open={!!selected} onClose={() => setSelected(null)} title={selected?.headline ?? ''} subtitle={selected ? `${selected.source} · ${selected.published}` : ''}>
        {selected && (
          <>
            <DrawerSection title="Article">
              <p className="text-[13px] leading-relaxed text-dim">{selected.excerpt}</p>
            </DrawerSection>
            <DrawerSection title="Classification">
              {degraded ? (
                <DegradedNote>Sentiment model unavailable for this article.</DegradedNote>
              ) : (
                <>
                  <div className="mb-2"><SentimentTag s={selected.sentiment} score={selected.score} /></div>
                  <KV k="Model" v={selected.model} />
                  <KV k="Analyzed" v={selected.analyzed} />
                  <KV k="Related coin" v={selected.coin} />
                </>
              )}
            </DrawerSection>
          </>
        )}
      </Drawer>
    </div>
  )
}
