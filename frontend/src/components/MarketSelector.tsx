import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Search, Star } from 'lucide-react'
import { useStore } from '../lib/store'
import type { MarketInfo } from '../domain'
import { useServices } from '../services/registry'
import { cn } from './ui'

function CoinIcon({ m, size = 18 }: { m: MarketInfo; size?: number }) {
  return (
    <span
      className="grid shrink-0 place-items-center rounded-full font-bold text-black"
      style={{ width: size, height: size, background: m.color, fontSize: size * 0.55 }}
    >
      {m.symbol}
    </span>
  )
}

function pct(n: number) {
  return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`
}

function MarketRow({
  m,
  onPick,
  marketValues,
  showMockValues,
}: {
  m: MarketInfo
  onPick: () => void
  marketValues?: { price: number; change24h: number }
  showMockValues: boolean
}) {
  const { watchlist, toggleWatch, market } = useStore()
  const fav = watchlist.includes(m.pair)
  const active = market.pair === m.pair
  return (
    <div
      className={cn(
        'flex items-center gap-2.5 rounded-[6px] border px-2.5 py-2 transition-colors',
        active ? 'border-accent/40 bg-accent/10' : 'border-transparent hover:bg-surface-hover',
        !m.available && 'opacity-70',
      )}
    >
      <button
        onClick={() => toggleWatch(m.pair)}
        title={fav ? 'Remove from watchlist' : 'Add to watchlist'}
        className={cn('shrink-0 transition-colors', fav ? 'text-warn' : 'text-faint hover:text-dim')}
      >
        <Star size={14} fill={fav ? 'currentColor' : 'none'} />
      </button>
      <CoinIcon m={m} />
      <button
        onClick={onPick}
        disabled={!m.available}
        className="flex min-w-0 flex-1 items-center gap-3 text-left disabled:cursor-not-allowed"
      >
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[12.5px] font-medium text-ink">{m.display}</span>
            {active && <span className="text-[10px] font-semibold uppercase text-accent">Selected</span>}
          </div>
          <div className="truncate text-[11px] text-faint">{m.name} priced in {m.quote}</div>
        </div>
        {m.available && (marketValues !== undefined || showMockValues) ? (
          <div className="text-right">
            <div className="font-mono text-[12px] tabular-nums text-ink">
              {(marketValues?.price ?? m.price).toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </div>
            <div className={cn('font-mono text-[11px] tabular-nums', (marketValues?.change24h ?? m.change24h) >= 0 ? 'text-pos' : 'text-neg')}>
              {pct(marketValues?.change24h ?? m.change24h)}
            </div>
          </div>
        ) : m.available ? (
          <span className="text-[10px] text-faint">Select to load</span>
        ) : (
          <span className="rounded-[3px] border border-subtle bg-workspace px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-faint">
            Coming later
          </span>
        )}
      </button>
    </div>
  )
}

// Floating market selector. Follows the InfoPopover render-prop pattern so it can
// anchor to the top-bar pair control or a "Change Market" button.
export function MarketSelector({
  trigger,
  align = 'left',
  width = 320,
  availablePairs,
  marketValues,
  showMockValues = true,
  loading = false,
}: {
  trigger: (props: { onClick: () => void; open: boolean }) => ReactNode
  align?: 'left' | 'right'
  width?: number
  availablePairs?: readonly string[]
  marketValues?: Readonly<Record<string, { price: number; change24h: number }>>
  showMockValues?: boolean
  loading?: boolean
}) {
  const { setMarket, watchlist, toast } = useStore()
  const { market: marketService } = useServices()
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    window.addEventListener('mousedown', onDown)
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('mousedown', onDown)
      window.removeEventListener('keydown', onKey)
    }
  }, [open])

  const query = q.trim().toLowerCase()
  const match = (m: MarketInfo) =>
    !query ||
    m.display.toLowerCase().includes(query) ||
    m.base.toLowerCase().includes(query) ||
    m.name.toLowerCase().includes(query)

  const markets = availablePairs === undefined
    ? marketService.listMarkets(query)
    : availablePairs
        .map((pair) => marketService.getMarket(pair))
        .filter((item): item is MarketInfo => item !== undefined)
        .map((item) => ({ ...item, available: true }))
  const filtered = markets.filter(match)
  const watched = filtered.filter((m) => watchlist.includes(m.pair))
  const others = filtered.filter((m) => !watchlist.includes(m.pair))

  const pick = (m: MarketInfo) => {
    if (!m.available) return
    setMarket(m.pair)
    setOpen(false)
    toast(`Market context set to ${m.display}`, 'info')
  }

  return (
    <div ref={ref} className="relative inline-flex">
      {trigger({ onClick: () => setOpen((o) => !o), open })}
      {open && (
        <div
          className={cn(
            'absolute top-full z-50 mt-1.5 rounded-[10px] border border-line bg-surface shadow-2xl',
            align === 'right' ? 'right-0' : 'left-0',
          )}
          style={{ width, animation: 'csl-fade-in 100ms ease-out' }}
        >
          <div className="border-b border-subtle px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-faint">
            Select market
          </div>
          <div className="border-b border-subtle p-2.5">
            <div className="flex items-center gap-2 rounded-[6px] border border-subtle bg-workspace px-2.5 py-1.5">
              <Search size={13} className="text-faint" />
              <input
                autoFocus
                aria-label="Search markets"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search coin or pair…"
                className="w-full bg-transparent text-[12.5px] text-ink outline-none placeholder:text-faint"
              />
            </div>
          </div>
          <div className="max-h-[340px] overflow-y-auto p-1.5">
            {watched.length > 0 && (
              <>
                <div className="px-1.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-faint">
                  Watchlist
                </div>
                {watched.map((m) => (
                  <MarketRow
                    key={m.pair}
                    m={m}
                    onPick={() => pick(m)}
                    marketValues={marketValues?.[m.pair]}
                    showMockValues={showMockValues}
                  />
                ))}
              </>
            )}
            {others.length > 0 && (
              <>
                <div className="px-1.5 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wide text-faint">
                  All markets
                </div>
                {others.map((m) => (
                  <MarketRow
                    key={m.pair}
                    m={m}
                    onPick={() => pick(m)}
                    marketValues={marketValues?.[m.pair]}
                    showMockValues={showMockValues}
                  />
                ))}
              </>
            )}
            {filtered.length === 0 && (
              <p className="px-2 py-6 text-center text-[12px] text-faint">
                {loading ? 'Loading supported markets…' : `No markets match “${q}”.`}
              </p>
            )}
          </div>
          <div className="border-t border-subtle px-3 py-2 text-[11px] leading-relaxed text-faint">
            {availablePairs === undefined
              ? 'Configured market contexts.'
              : 'Supported pairs reported by the backend.'}
          </div>
        </div>
      )}
    </div>
  )
}

export { CoinIcon }
