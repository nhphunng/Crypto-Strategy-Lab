import { useEffect, useState, type ReactNode } from 'react'
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
import { useStore, type ConnState } from '../lib/store'
import { NAV_ITEMS } from '../config'
import { useServices } from '../services/registry'
import { cn, IconBtn, LearnTooltip, Segmented, Toggle } from './ui'
import { CoinIcon, MarketSelector } from './MarketSelector'

const CONN_META: Record<ConnState, { label: string; color: string; spin?: boolean; pulse?: boolean }> = {
  live: { label: 'Live', color: 'text-pos', pulse: true },
  reconnecting: { label: 'Reconnecting', color: 'text-warn', spin: true },
  stale: { label: 'Stale · 18s', color: 'text-warn' },
}

function ConnectionStatus() {
  const { conn, setConn } = useStore()
  const [open, setOpen] = useState(false)
  const m = CONN_META[conn]
  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 rounded-[5px] border border-subtle bg-workspace px-2 py-1 text-[12px] hover:bg-surface-hover"
        title="Provider: Binance · toggle demo connection state"
      >
        <span
          className={cn(
            'h-1.5 w-1.5 rounded-full bg-current',
            m.color,
            m.pulse && 'csl-pulse',
          )}
        />
        <span className={cn('font-medium', m.color)}>{m.label}</span>
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-20" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-30 mt-1 w-40 rounded-[8px] border border-line bg-surface p-1 shadow-xl">
            <div className="px-2 py-1 text-[10px] uppercase tracking-wide text-faint">Demo state</div>
            {(['live', 'reconnecting', 'stale'] as ConnState[]).map((c) => (
              <button
                key={c}
                onClick={() => {
                  setConn(c)
                  setOpen(false)
                }}
                className={cn(
                  'flex w-full items-center gap-2 rounded-[4px] px-2 py-1.5 text-left text-[12px] hover:bg-surface-hover',
                  conn === c ? 'text-ink' : 'text-dim',
                )}
              >
                <span className={cn('h-1.5 w-1.5 rounded-full bg-current', CONN_META[c].color)} />
                {CONN_META[c].label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

function TopBar() {
  const { navigate, showExplain, toggleExplain, market } = useStore()
  const { operations } = useServices()
  const pos = market.change24h >= 0
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
          {market.price.toLocaleString('en-US', { minimumFractionDigits: 2 })}
        </span>
        <span className={cn('font-mono text-[12px] tabular-nums', pos ? 'text-pos' : 'text-neg')}>
          {pos ? '+' : ''}
          {market.change24h}%
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
        <button className="hidden items-center gap-1.5 rounded-[5px] border border-subtle bg-workspace px-2 py-1 text-[11px] text-faint hover:text-dim md:flex">
          <Search size={12} />
          <span>Search</span>
          <kbd className="rounded-[3px] border border-subtle bg-surface px-1 font-mono text-[10px]">⌘K</kbd>
        </button>
        <ConnectionStatus />
        <span className="hidden font-mono text-[11px] text-faint xl:inline">{operations.now()}</span>
        <IconBtn title="Reconnect">
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
  return (
    <div className="flex h-screen flex-col overflow-hidden bg-canvas">
      <TopBar />
      <div className="flex min-h-0 flex-1">
        <Nav />
        <main className="min-w-0 flex-1 overflow-hidden bg-workspace">{children}</main>
      </div>
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
