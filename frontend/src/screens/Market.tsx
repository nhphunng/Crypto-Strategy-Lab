import { useMemo, useState } from 'react'
import {
  Maximize2,
  MoreHorizontal,
  PanelRightClose,
  PanelRightOpen,
  RefreshCw,
  Search,
  Settings2,
  Signal,
  Star,
} from 'lucide-react'
import { useStore, type ConnState } from '../lib/store'
import type { Timeframe } from '../domain'
import { DEFAULT_TIMEFRAMES } from '../config'
import { useServices } from '../services/registry'
import { CandleChart } from '../components/CandleChart'
import { PageHeader } from '../components/Shell'
import {
  Button,
  cn,
  Drawer,
  DrawerSection,
  HelperText,
  IconBtn,
  InfoNote,
  KV,
  LearnTooltip,
  RecoBadge,
  Segmented,
  StatusBadge,
} from '../components/ui'

type Layout = '1' | '2' | '4'
type PaneOverlays = { ma20: boolean; ma50: boolean; bb: boolean; sr: boolean }

type PaneState = {
  tf: Timeframe
  overlays: PaneOverlays
  conn: ConnState
}

const OVERLAY_META: {
  key: keyof PaneOverlays
  label: string
  color: string
  name: string
  category: string
  purpose: string
  starter?: boolean
}[] = [
  {
    key: 'ma20',
    label: 'MA20',
    color: 'text-accent',
    name: 'Moving Average · 20',
    category: 'Trend',
    purpose: 'Smooths price into a single line so you can see the general direction more easily.',
    starter: true,
  },
  {
    key: 'ma50',
    label: 'MA50',
    color: 'text-warn',
    name: 'Moving Average · 50',
    category: 'Trend',
    purpose: 'A slower average. Comparing it with MA20 helps you spot shifts in the longer trend.',
  },
  {
    key: 'bb',
    label: 'BB20 σ2',
    color: 'text-info',
    name: 'Bollinger Bands',
    category: 'Volatility',
    purpose: 'Shows how far price is stretching from its recent average — a read on volatility.',
  },
  {
    key: 'sr',
    label: 'S/R v4',
    color: 'text-dim',
    name: 'Support / Resistance',
    category: 'Market structure',
    purpose: 'Marks price areas where the market has repeatedly reacted before.',
  },
]

const CONN_LABEL: Record<ConnState, string> = {
  live: 'Live',
  reconnecting: 'Reconnecting',
  stale: 'Stale · 18s',
}

function ChartPane({
  index,
  state,
  onChange,
  onOpenSettings,
  height,
  globalConn,
  partial,
}: {
  index: number
  state: PaneState
  onChange: (s: Partial<PaneState>) => void
  onOpenSettings: (i: number) => void
  height: number
  globalConn: ConnState
  partial?: boolean
}) {
  const { showExplain, market } = useStore()
  const services = useServices()
  const noOverlays = !state.overlays.ma20 && !state.overlays.ma50 && !state.overlays.bb && !state.overlays.sr
  const candles = useMemo(
    () => services.market.getCandles(state.tf, 100),
    [services, state.tf],
  )
  const markers = useMemo(
    () =>
      state.overlays.sr || state.overlays.ma20
        ? services.market.getSignalMarkers(candles, index + 3)
        : [],
    [candles, index, services, state.overlays.sr, state.overlays.ma20],
  )
  const conn = globalConn
  const last = candles[candles.length - 1]
  const up = last.c >= last.o

  return (
    <div className="flex min-h-0 flex-col bg-surface">
      {/* pane header */}
      <div className="flex h-8 shrink-0 items-center gap-2 border-b border-subtle px-2.5">
        <span className="font-mono text-[11px] font-medium text-ink">{market.pair}</span>
        <span className="font-mono text-[11px] tabular-nums text-faint">·</span>
        <Segmented<Timeframe>
          ariaLabel={`Timeframe for chart ${index + 1}`}
          options={services.market.timeframes.map((t) => ({ value: t, label: t }))}
          value={state.tf}
          onChange={(tf) => onChange({ tf })}
        />
        <div className="ml-auto flex items-center gap-1.5">
          {conn === 'live' && <StatusBadge tone="live" pulse>Live</StatusBadge>}
          {conn === 'reconnecting' && <StatusBadge tone="reconnecting" pulse>Reconnecting</StatusBadge>}
          {conn === 'stale' && <StatusBadge tone="stale">Stale · 18s</StatusBadge>}
          <IconBtn onClick={() => onOpenSettings(index)} title="Indicator settings">
            <Settings2 size={13} />
          </IconBtn>
          <IconBtn title="More"><MoreHorizontal size={13} /></IconBtn>
        </div>
      </div>

      {/* legend */}
      <div className="flex h-7 shrink-0 items-center gap-3 border-b border-subtle px-2.5">
        <span className="font-mono text-[11px] tabular-nums">
          <span className={up ? 'text-pos' : 'text-neg'}>{last.c.toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
        </span>
        {OVERLAY_META.filter((o) => state.overlays[o.key]).map((o) => (
          <button
            key={o.key}
            onClick={() => onOpenSettings(index)}
            className={cn('font-mono text-[10px] hover:underline', o.color)}
          >
            {o.label}
          </button>
        ))}
        {conn === 'stale' && (
          <span className="ml-auto font-mono text-[10px] text-warn">Market data stale · last update 18s ago</span>
        )}
        {partial && conn !== 'stale' && (
          <span className="ml-auto font-mono text-[10px] text-info">312 / 500 candles loaded · backfilling…</span>
        )}
      </div>

      {/* chart */}
      <div className={cn('relative min-h-0 flex-1', conn === 'reconnecting' && 'opacity-70')}>
        <CandleChart
          candles={candles}
          overlays={state.overlays}
          markers={markers}
          height={height}
          compact={height < 200}
        />
        {conn === 'reconnecting' && (
          <div className="absolute right-2 top-8 flex items-center gap-1.5 rounded-[5px] border border-warn/40 bg-surface/90 px-2 py-1 text-[11px] text-warn">
            <RefreshCw size={11} className="csl-spin" /> Reconnecting — showing last candles
          </div>
        )}
        {noOverlays && showExplain && conn !== 'reconnecting' && (
          <div className="pointer-events-none absolute inset-x-0 top-3 flex justify-center">
            <div className="pointer-events-auto flex items-center gap-2.5 rounded-[6px] border border-line bg-surface/95 px-3 py-1.5 shadow-lg">
              <span className="text-[11.5px] text-dim">
                Add an indicator to read trend, momentum, volatility or market structure.
              </span>
              <Button size="sm" onClick={() => onOpenSettings(index)}>
                Add indicator
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function WatchlistPanel({ open, onToggle }: { open: boolean; onToggle: () => void }) {
  const { watchlist, toggleWatch, market, setMarket, toast } = useStore()
  const services = useServices()
  const [q, setQ] = useState('')

  if (!open) {
    return (
      <button
        onClick={onToggle}
        title="Show watchlist"
        className="flex w-9 shrink-0 flex-col items-center gap-2 border-l border-subtle bg-surface py-3 text-faint hover:text-dim"
      >
        <PanelRightOpen size={15} />
        <span className="text-[10px] font-semibold uppercase tracking-wide [writing-mode:vertical-rl]">
          Watchlist
        </span>
      </button>
    )
  }

  const query = q.trim().toLowerCase()
  const rows = services.market.listMarkets().filter(
    (m) =>
      watchlist.includes(m.pair) &&
      (!query || m.display.toLowerCase().includes(query) || m.name.toLowerCase().includes(query)),
  )
  const matchesQuery = (m: { display: string; name: string; base: string; pair: string }) =>
    !query || [m.display, m.name, m.base, m.pair].some((value) => value.toLowerCase().includes(query))
  const addable = services.market
    .listMarkets()
    .filter((m) => !watchlist.includes(m.pair) && matchesQuery(m))

  return (
    <aside className="flex w-[210px] shrink-0 flex-col border-l border-subtle bg-surface">
      <div className="flex h-8 shrink-0 items-center justify-between border-b border-subtle px-2.5">
        <span className="text-[11px] font-semibold uppercase tracking-wide text-faint">Watchlist</span>
        <IconBtn onClick={onToggle} title="Hide watchlist"><PanelRightClose size={14} /></IconBtn>
      </div>
      <div className="border-b border-subtle p-2">
        <div className="flex items-center gap-1.5 rounded-[5px] border border-subtle bg-workspace px-2 py-1">
          <Search size={12} className="text-faint" />
          <input
            aria-label="Search watchlist"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search"
            className="w-full bg-transparent text-[12px] text-ink outline-none placeholder:text-faint"
          />
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="flex items-center gap-2 border-b border-subtle px-2.5 py-1 text-[10px] uppercase tracking-wide text-faint">
          <span className="flex-1">Pair</span>
          <span>24h</span>
        </div>
        {rows.map((m) => {
          const active = market.pair === m.pair
          return (
            <div
              key={m.pair}
              className={cn(
                'group flex items-center gap-1.5 border-b border-subtle px-2.5 py-1.5',
                active && 'bg-accent/10',
              )}
            >
              <button
                onClick={() => toggleWatch(m.pair)}
                title="Remove from watchlist"
                className="shrink-0 text-warn"
              >
                <Star size={12} fill="currentColor" />
              </button>
              <button
                onClick={() => {
                  if (!m.available) {
                    toast(`${m.display} is coming later — not yet available`, 'warning')
                    return
                  }
                  setMarket(m.pair)
                }}
                disabled={!m.available}
                className="flex min-w-0 flex-1 flex-col items-start text-left disabled:cursor-not-allowed"
              >
                <span className={cn('font-mono text-[11.5px]', active ? 'text-accent' : 'text-ink')}>
                  {m.base}/{m.quote}
                </span>
                {m.available ? (
                  <span className="font-mono text-[10px] tabular-nums text-faint">
                    {m.price.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                  </span>
                ) : (
                  <span className="text-[10px] text-faint">Coming later</span>
                )}
              </button>
              {m.available && (
                <span className={cn('font-mono text-[11px] tabular-nums', m.change24h >= 0 ? 'text-pos' : 'text-neg')}>
                  {m.change24h >= 0 ? '+' : ''}
                  {m.change24h}%
                </span>
              )}
            </div>
          )
        })}
        {rows.length === 0 && (
          <p className="px-2.5 py-4 text-[11px] leading-relaxed text-faint">
            {query ? 'No markets match your search.' : 'No pairs in your watchlist. Add one below.'}
          </p>
        )}
        {addable.length > 0 && (
          <div className="p-2">
            <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-faint">Add to watchlist</div>
            <div className="space-y-1">
              {addable.map((m) => (
                <button
                  key={m.pair}
                  onClick={() => toggleWatch(m.pair)}
                  className="flex w-full items-center gap-1.5 rounded-[4px] px-1.5 py-1 text-left text-[11.5px] text-dim hover:bg-surface-hover"
                >
                  <Star size={11} className="text-faint" />
                  <span className="font-mono">{m.base}/{m.quote}</span>
                  <span className="ml-auto text-[10px] text-faint">{m.name}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </aside>
  )
}

export function Market() {
  const { conn, overlayContext, showExplain, market } = useStore()
  const [watchOpen, setWatchOpen] = useState(false)
  const [layout, setLayout] = useState<Layout>('4')
  const [sync, setSync] = useState(true)
  const [settingsFor, setSettingsFor] = useState<number | null>(null)

  const [panes, setPanes] = useState<PaneState[]>(
    DEFAULT_TIMEFRAMES.map((tf, i) => ({
      tf,
      overlays: { ma20: i < 2, ma50: i === 2, bb: false, sr: !!overlayContext },
      conn,
    })),
  )

  const visible = layout === '1' ? 1 : layout === '2' ? 2 : 4

  const updatePane = (i: number, s: Partial<PaneState>) =>
    setPanes((p) => p.map((x, k) => (k === i ? { ...x, ...s } : x)))

  const gridClass =
    layout === '1'
      ? 'grid-cols-1 grid-rows-1'
      : layout === '2'
        ? 'grid-cols-2 grid-rows-1'
        : 'grid-cols-2 grid-rows-2'

  const paneHeight = layout === '1' ? 520 : layout === '2' ? 520 : 250

  return (
    <div className="flex h-full flex-col">
      <PageHeader title="Market">
        {overlayContext && (
          <StatusBadge tone="new">Overlay: {overlayContext}</StatusBadge>
        )}
        <Segmented
          ariaLabel="Chart layout"
          options={[
            { value: '1', label: '1' },
            { value: '2', label: '2' },
            { value: '4', label: '4' },
          ]}
          value={layout}
          onChange={(v) => setLayout(v as Layout)}
        />
        <button
          onClick={() => setSync((s) => !s)}
          className={cn(
            'inline-flex h-7 items-center gap-1.5 rounded-[5px] border px-2 text-[12px]',
            sync ? 'border-accent/40 bg-accent/15 text-accent' : 'border-subtle text-dim hover:bg-surface-hover',
          )}
        >
          <Signal size={13} /> Sync crosshair
        </button>
        <IconBtn title="Reconnect"><RefreshCw size={14} /></IconBtn>
        <IconBtn title="Fullscreen workspace"><Maximize2 size={14} /></IconBtn>
      </PageHeader>

      {showExplain && (
        <div className="shrink-0 border-b border-subtle bg-surface px-4 py-2.5">
          <InfoNote>
            You're looking at <span className="font-medium text-ink">{market.display}</span> — {market.name}{' '}
            priced in {market.quote}. Each chart shows one timeframe: how much time a single candle covers. New
            to charts? Start with <span className="font-mono text-ink">15m</span> or{' '}
            <span className="font-mono text-ink">1h</span>, then add an indicator to read trend,
            momentum, volatility or market structure. Availability is supplied by the market service.
          </InfoNote>
        </div>
      )}

      <div className="flex min-h-0 flex-1">
        <div className={cn('grid min-h-0 flex-1 gap-px bg-subtle p-px', gridClass)}>
          {panes.slice(0, visible).map((p, i) => (
            <ChartPane
              key={i}
              index={i}
              state={p}
              onChange={(s) => updatePane(i, s)}
              onOpenSettings={setSettingsFor}
              height={paneHeight}
              globalConn={conn}
              partial={i === 3}
            />
          ))}
        </div>
        <WatchlistPanel open={watchOpen} onToggle={() => setWatchOpen((o) => !o)} />
      </div>

      {/* Indicator settings drawer */}
      <Drawer
        open={settingsFor != null}
        onClose={() => setSettingsFor(null)}
        title="Indicators"
        subtitle={settingsFor != null ? `${market.pair} · ${panes[settingsFor].tf} pane` : ''}
      >
        {settingsFor != null && (
          <>
            <DrawerSection title="Indicators">
              <HelperText>
                Indicators draw extra information on top of the price. Add one to help read the
                market — they don't place any trades.
              </HelperText>
              <div className="mt-2 space-y-1.5">
                {OVERLAY_META.map((o) => {
                  const on = panes[settingsFor].overlays[o.key]
                  return (
                    <button
                      key={o.key}
                      onClick={() =>
                        updatePane(settingsFor, {
                          overlays: { ...panes[settingsFor].overlays, [o.key]: !on },
                        })
                      }
                      className={cn(
                        'flex w-full items-start gap-3 rounded-[6px] border px-3 py-2.5 text-left transition-colors',
                        on ? 'border-accent/40 bg-accent/10' : 'border-subtle hover:bg-surface-hover',
                      )}
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className={cn('font-mono text-[12px]', o.color)}>{o.label}</span>
                          <span className="text-[12px] text-ink">{o.name}</span>
                          <span className="rounded-[3px] bg-surface-active px-1.5 py-0.5 text-[10px] uppercase text-faint">
                            {o.category}
                          </span>
                          {o.starter && showExplain && <RecoBadge>Good starting point</RecoBadge>}
                        </div>
                        {showExplain && (
                          <p className="mt-1 text-[11.5px] leading-relaxed text-faint">{o.purpose}</p>
                        )}
                      </div>
                      <span className="mt-0.5 shrink-0 text-[11px] font-medium text-accent">
                        {on ? 'Remove' : 'Add'}
                      </span>
                    </button>
                  )
                })}
              </div>
            </DrawerSection>
            <DrawerSection title="Moving Average · MA20">
              <KV k="Period" v="20" />
              <KV k="Source" v="close" />
              <KV k="Type" v="SMA" />
            </DrawerSection>
            <DrawerSection title="Support / Resistance">
              <KV k="Lookback" v="120" />
              <KV k="Tolerance" v="0.7%" />
              <p className="mt-2 text-[11px] leading-relaxed text-faint">
                Translucent zones mark detected support (green) and resistance (red) bands. BUY / SELL
                and Entry / Exit markers are drawn from the active strategy overlay.
              </p>
            </DrawerSection>
          </>
        )}
      </Drawer>
    </div>
  )
}
