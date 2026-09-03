import { useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  CandlestickChart,
  ChevronDown,
  ChevronsLeft,
  History,
  Newspaper,
  PanelLeft,
  RefreshCw,
  Search,
  ServerCog,
  Trophy,
  Workflow,
} from 'lucide-react'
import { useStore } from '../lib/store'
import { NAV_ITEMS } from '../config'
import { useTopBarMarketData } from '../features/market-chart/hooks/useTopBarMarketData'
import type { ConnectionState } from '../features/market-chart/types'
import { cn, IconBtn, LearnTooltip, Segmented, Toggle } from './ui'
import { CoinIcon, MarketSelector } from './MarketSelector'
import { CommandPalette } from './CommandPalette'

const CONN_META: Record<ConnectionState, { label: string; color: string; pulse?: boolean }> = {
  LIVE: { label: 'Live', color: 'text-pos', pulse: true },
  LOADING: { label: 'Loading', color: 'text-faint' },
  RECONNECTING: { label: 'Reconnecting', color: 'text-warn', pulse: true },
  STALE: { label: 'Stale', color: 'text-warn' },
  ERROR: { label: 'Error', color: 'text-neg' },
  RELEASED: { label: 'Offline', color: 'text-faint' },
}

function ConnectionStatus({ state, onRetry }: { state: ConnectionState; onRetry: () => void }) {
  const m = CONN_META[state]
  const canRetry = state === 'ERROR' || state === 'STALE' || state === 'RECONNECTING'
  return (
    <button
      type="button"
      onClick={canRetry ? onRetry : undefined}
      className={cn(
        'flex items-center gap-1.5 rounded-[5px] border border-subtle bg-workspace px-2 py-1 text-[12px]',
        canRetry && 'hover:bg-surface-hover',
      )}
      title={canRetry ? 'Retry the market-data connection' : `Market data: ${m.label}`}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full bg-current', m.color, m.pulse && 'csl-pulse')} />
      <span className={cn('font-medium', m.color)}>{m.label}</span>
    </button>
  )
}

function TopBar({ onOpenCommandPalette }: { onOpenCommandPalette: () => void }) {
  const { navigate, showExplain, toggleExplain, market } = useStore()
  const summary = useTopBarMarketData(market.pair)
  const [now, setNow] = useState(() => new Date())
  const marketValues = useMemo(
    () => summary.price === null || summary.change24h === null
      ? {}
      : { [market.pair]: { price: summary.price, change24h: summary.change24h } },
    [market.pair, summary.change24h, summary.price],
  )
  const pos = (summary.change24h ?? 0) >= 0

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1_000)
    return () => window.clearInterval(timer)
  }, [])

  return (
    <header className="flex h-12 shrink-0 items-center gap-3 border-b border-line bg-canvas px-3">
      <button onClick={() => navigate('landing')} className="flex items-center gap-2">
        <span className="grid h-6 w-6 place-items-center rounded-[5px] bg-accent text-[11px] font-bold text-white">
          CSL
        </span>
        <span className="text-[13px] font-semibold tracking-tight text-ink">Crypto Strategy Lab</span>
      </button>

      <div className="mx-1 h-5 w-px bg-subtle" />

      {/* global market selector */}
      <MarketSelector
        availablePairs={summary.pairs}
        marketValues={marketValues}
        showMockValues={false}
        loading={summary.pairsLoading}
        trigger={({ onClick, open }) => (
          <button
            onClick={onClick}
            className={cn(
              'flex items-center gap-2 rounded-[5px] border px-2.5 py-1 transition-colors',
              open ? 'border-accent/50 bg-surface-hover' : 'border-subtle bg-workspace hover:bg-surface-hover',
            )}
          >
            <CoinIcon m={market} size={16} />
            <span className="font-mono text-[12px] font-medium text-ink">{market.display}</span>
            <span className="rounded-[3px] bg-surface-active px-1 text-[10px] text-faint">Binance</span>
            <ChevronDown size={13} className={cn('text-faint transition-transform', open && 'rotate-180')} />
          </button>
        )}
      />

      {/* price */}
      <div className="flex items-baseline gap-2">
        <span className="font-mono text-[13px] font-semibold tabular-nums text-ink">
          {summary.price === null
            ? '—'
            : summary.price.toLocaleString('en-US', { minimumFractionDigits: 2 })}
        </span>
        <span className={cn('font-mono text-[12px] tabular-nums', pos ? 'text-pos' : 'text-neg')}>
          {summary.change24h === null ? '—' : `${pos ? '+' : ''}${summary.change24h.toFixed(2)}%`}
        </span>
      </div>

      <div className="ml-auto flex items-center gap-3">
        <LearnTooltip
          always
          content="Turn on plain-language helper text, tooltips and recommended defaults across the app. Advanced controls always stay available."
        >
          <Toggle
            checked={showExplain}
            onChange={toggleExplain}
            label={<span className="hidden sm:inline">Show explanations</span>}
          />
        </LearnTooltip>
        <button
          onClick={onOpenCommandPalette}
          className="hidden items-center gap-1.5 rounded-[5px] border border-subtle bg-workspace px-2 py-1 text-[11px] text-faint hover:text-dim md:flex"
        >
          <Search size={12} />
          <span>Search</span>
          <kbd className="rounded-[3px] border border-subtle bg-surface px-1 font-mono text-[10px]">⌘K</kbd>
        </button>
        <ConnectionStatus state={summary.connectionState} onRetry={summary.retry} />
        <span className="hidden font-mono text-[11px] text-faint xl:inline">
          {now.toLocaleTimeString([], { hour12: false })}
        </span>
        <IconBtn title="Reconnect" onClick={summary.retry} aria-label="Reconnect market data">
          <RefreshCw size={14} />
        </IconBtn>
      </div>
    </header>
  )
}

function Nav() {
  const { page, navigate, navCollapsed, toggleNav } = useStore()
  return (
    <nav
      className="flex shrink-0 flex-col border-r border-line bg-canvas transition-[width] duration-150"
      style={{ width: navCollapsed ? 52 : 184 }}
    >
      <div className="flex flex-1 flex-col gap-0.5 p-2">
        {NAV_ITEMS.map(({ page: p, label, icon: Icon }) => {
          const active = page === p
          return (
            <button
              key={p}
              onClick={() => navigate(p)}
              title={navCollapsed ? label : undefined}
              className={cn(
                'group relative flex h-9 items-center gap-2.5 rounded-[6px] px-2.5 text-[13px] transition-colors',
                active ? 'bg-surface-active text-ink' : 'text-dim hover:bg-surface-hover hover:text-ink',
              )}
            >
              {active && <span className="absolute left-0 top-1.5 bottom-1.5 w-0.5 rounded-full bg-accent" />}
              <Icon size={17} className={cn('shrink-0', active && 'text-accent')} />
              {!navCollapsed && <span className="truncate">{label}</span>}
            </button>
          )
        })}
      </div>
      <div className="border-t border-subtle p-2">
        <button
          onClick={toggleNav}
          className="flex h-8 w-full items-center gap-2.5 rounded-[6px] px-2.5 text-[12px] text-faint hover:bg-surface-hover hover:text-dim"
        >
          {navCollapsed ? <PanelLeft size={16} /> : <ChevronsLeft size={16} />}
          {!navCollapsed && <span>Collapse</span>}
        </button>
      </div>
    </nav>
  )
}

// A running clock/sync is faked to a deterministic value; keep it visually alive.
export function AppShell({ children }: { children: ReactNode }) {
  // keep the layout locked to a desktop workspace height
  useEffect(() => {
    document.title = 'Crypto Strategy Lab'
  }, [])
  const [commandOpen, setCommandOpen] = useState(false)
  // Global command-palette shortcut: Cmd/Ctrl + K.
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setCommandOpen((o) => !o)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])
  return (
    <div className="flex h-screen flex-col overflow-hidden bg-canvas">
      <TopBar onOpenCommandPalette={() => setCommandOpen(true)} />
      <div className="flex min-h-0 flex-1">
        <Nav />
        <main className="min-w-0 flex-1 overflow-hidden bg-workspace">{children}</main>
      </div>
      <CommandPalette open={commandOpen} onClose={() => setCommandOpen(false)} />
    </div>
  )
}

// Reusable page header used across product screens
export function PageHeader({
  title,
  children,
}: {
  title: string
  children?: ReactNode
}) {
  return (
    <div className="flex min-h-12 shrink-0 flex-wrap items-center justify-between gap-2 border-b border-subtle bg-surface px-4 py-1.5">
      <h1 className="text-[15px] font-semibold text-ink">{title}</h1>
      <div className="flex flex-wrap items-center justify-end gap-2">{children}</div>
    </div>
  )
}

export { Segmented }
