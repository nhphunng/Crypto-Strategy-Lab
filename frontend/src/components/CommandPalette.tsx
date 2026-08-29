import { useEffect, useMemo, useRef, useState } from 'react'
import {
  CandlestickChart,
  History,
  Newspaper,
  ServerCog,
  Trophy,
  Workflow,
  type LucideIcon,
} from 'lucide-react'
import { useStore, type Page } from '../lib/store'
import { cn } from './ui'
import { NAV_ITEMS } from '../config'

type PaletteAction = {
  id: string
  label: string
  hint?: string
  icon: LucideIcon
  keyword: string
  run: () => void
}

// Build the palette actions from nav + a few high-value quick actions that map
// straight into existing routes. No dead entries — every row navigates or runs.
function buildActions(navigate: (p: Page) => void): PaletteAction[] {
  const nav = NAV_ITEMS.map(({ page: p, label, icon }) => ({
    id: `nav-${p}`,
    label,
    icon,
    keyword: label.toLowerCase(),
    run: () => navigate(p),
  }))
  return [
    ...nav,
    {
      id: 'nav-strategy-new',
      label: 'New Strategy',
      hint: 'Open the strategy builder',
      icon: Workflow,
      keyword: 'new strategy create build',
      run: () => navigate('strategyNew'),
    },
    {
      id: 'backtest-run',
      label: 'Run Backtest',
      hint: 'Go to Backtests',
      icon: History,
      keyword: 'run backtest test',
      run: () => navigate('backtests'),
    },
    {
      id: 'backtest-search',
      label: 'Strategy Search',
      hint: 'Go to Backtests › Search',
      icon: Trophy,
      keyword: 'search random loop',
      run: () => navigate('backtests'),
    },
  ]
}

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { navigate } = useStore()
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const listRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const actions = useMemo(() => buildActions(navigate), [navigate])
  const q = query.trim().toLowerCase()
  const results = useMemo(
    () => (q ? actions.filter((a) => a.keyword.includes(q) || a.label.toLowerCase().includes(q)) : actions),
    [q, actions],
  )

  // Focus the input on open; clear on close.
  useEffect(() => {
    if (!open) return
    setQuery('')
    setActive(0)
    const t = window.setTimeout(() => inputRef.current?.focus(), 0)
    return () => window.clearTimeout(t)
  }, [open])

  // Keep the highlighted row in view as it moves.
  useEffect(() => {
    const el = listRef.current?.querySelector<HTMLElement>(`[data-index="${active}"]`)
    el?.scrollIntoView({ block: 'nearest' })
  }, [active])

  if (!open) return null

  const pick = (action: PaletteAction | undefined) => {
    if (!action) return
    action.run()
    onClose()
  }

  return (
    <div className="fixed inset-0 z-[70] flex justify-center px-4 pt-[16vh]">
      <div className="absolute inset-0 bg-black/55" aria-hidden="true" onClick={onClose} />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        className="relative w-full max-w-[560px] overflow-hidden rounded-[12px] border border-line bg-surface shadow-2xl"
        style={{ animation: 'csl-fade-in 120ms ease-out' }}
        onKeyDown={(e) => {
          if (e.key === 'Escape') {
            e.preventDefault()
            onClose()
            return
          }
          if (e.key === 'ArrowDown') {
            e.preventDefault()
            setActive((i) => Math.min(i + 1, results.length - 1))
            return
          }
          if (e.key === 'ArrowUp') {
            e.preventDefault()
            setActive((i) => Math.max(i - 1, 0))
            return
          }
          if (e.key === 'Enter') {
            e.preventDefault()
            pick(results[active])
          }
        }}
      >
        <div className="flex items-center gap-2.5 border-b border-subtle px-4">
          <span className="text-faint">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.3-4.3" />
            </svg>
          </span>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setActive(0)
            }}
            placeholder="Search commands…"
            aria-label="Search commands"
            className="h-12 w-full bg-transparent text-[14px] text-ink outline-none placeholder:text-faint"
          />
          <kbd className="rounded-[3px] border border-subtle bg-workspace px-1 py-0.5 font-mono text-[10px] text-faint">
            esc
          </kbd>
        </div>

        <div ref={listRef} className="max-h-[320px] overflow-y-auto p-1.5">
          {results.length === 0 ? (
            <p className="px-3 py-6 text-center text-[12.5px] text-faint">
              No commands match “{query}”. Try a page name like Market or Backtests.
            </p>
          ) : (
            <ul className="space-y-0.5">
              {results.map((a, i) => (
                <li key={a.id} data-index={i}>
                  <button
                    type="button"
                    onClick={() => pick(a)}
                    onMouseEnter={() => setActive(i)}
                    className={cn(
                      'flex w-full items-center gap-3 rounded-[6px] px-2.5 py-2 text-left transition-colors',
                      i === active ? 'bg-surface-active text-ink' : 'text-dim hover:bg-surface-hover',
                    )}
                  >
                    <a.icon size={16} className={cn('shrink-0', i === active ? 'text-accent' : 'text-faint')} />
                    <span className="flex-1 text-[13px]">{a.label}</span>
                    {a.hint && <span className="text-[11px] text-faint">{a.hint}</span>}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="flex items-center gap-4 border-t border-subtle px-4 py-2 text-[11px] text-faint">
          <span><kbd className="rounded-[3px] border border-subtle bg-workspace px-1 font-mono">↑↓</kbd> navigate</span>
          <span><kbd className="rounded-[3px] border border-subtle bg-workspace px-1 font-mono">↵</kbd> open</span>
          <span><kbd className="rounded-[3px] border border-subtle bg-workspace px-1 font-mono">esc</kbd> close</span>
        </div>
      </div>
    </div>
  )
}
