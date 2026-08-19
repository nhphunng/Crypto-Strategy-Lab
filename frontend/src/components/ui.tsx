import {
  useEffect,
  useId,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type ReactNode,
} from 'react'
import {
  ArrowDownRight,
  ArrowUpRight,
  Check,
  HelpCircle,
  Info,
  Minus,
  TriangleAlert,
  X,
} from 'lucide-react'
import { useStore } from '../lib/store'

export function cn(...parts: (string | false | null | undefined)[]) {
  return parts.filter(Boolean).join(' ')
}

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

function useDialogFocus<T extends HTMLElement>(open: boolean, onClose: () => void) {
  const dialogRef = useRef<T>(null)
  const returnFocusRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (!open) return
    returnFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const focusTimer = window.setTimeout(() => {
      const firstFocusable = dialogRef.current?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR)
      ;(firstFocusable ?? dialogRef.current)?.focus()
    }, 0)

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
        return
      }
      if (event.key !== 'Tab' || !dialogRef.current) return
      const focusable = Array.from(dialogRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR))
      if (focusable.length === 0) {
        event.preventDefault()
        dialogRef.current.focus()
        return
      }
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.clearTimeout(focusTimer)
      window.removeEventListener('keydown', onKeyDown)
      returnFocusRef.current?.focus()
    }
  }, [open, onClose])

  return dialogRef
}

// ---------------------------------------------------------------------------
// Buttons & compact controls
// ---------------------------------------------------------------------------

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'default' | 'ghost' | 'danger' | 'ml'
  size?: 'sm' | 'md'
}

export function Button({ variant = 'default', size = 'md', className, ...rest }: BtnProps) {
  const base =
    'inline-flex items-center justify-center gap-1.5 rounded-[5px] font-medium whitespace-nowrap transition-colors disabled:opacity-40 disabled:cursor-not-allowed select-none'
  const sizes = {
    sm: 'h-7 px-2.5 text-[12px]',
    md: 'h-9 px-3.5 text-[13px]',
  }
  const variants = {
    primary: 'bg-accent text-white hover:bg-accent-hover',
    default: 'bg-surface-active text-ink border border-line hover:bg-surface-hover',
    ghost: 'text-dim hover:text-ink hover:bg-surface-hover',
    danger: 'bg-neg/15 text-neg border border-neg/40 hover:bg-neg/25',
    ml: 'bg-ml/15 text-ml border border-ml/40 hover:bg-ml/25',
  }
  return <button type="button" className={cn(base, sizes[size], variants[variant], className)} {...rest} />
}

export function IconBtn({
  className,
  active,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { active?: boolean }) {
  return (
    <button
      type="button"
      aria-label={rest['aria-label'] ?? (typeof rest.title === 'string' ? rest.title : undefined)}
      className={cn(
        'inline-flex h-7 w-7 items-center justify-center rounded-[5px] transition-colors',
        active
          ? 'bg-accent/15 text-accent'
          : 'text-dim hover:text-ink hover:bg-surface-hover',
        className,
      )}
      {...rest}
    />
  )
}

// Segmented toolbar (timeframes, layout switch, tabs-as-toolbar)
export function Segmented<T extends string>({
  options,
  value,
  onChange,
  size = 'sm',
  ariaLabel = 'Options',
}: {
  options: { value: T; label: ReactNode }[]
  value: T
  onChange: (v: T) => void
  size?: 'sm' | 'md'
  ariaLabel?: string
}) {
  return (
    <div role="group" aria-label={ariaLabel} className="inline-flex items-center rounded-[5px] border border-subtle bg-workspace p-0.5">
      {options.map((o, index) => (
        <button
          type="button"
          key={o.value}
          aria-pressed={value === o.value}
          onClick={() => onChange(o.value)}
          onKeyDown={(event) => {
            if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return
            event.preventDefault()
            const direction = event.key === 'ArrowLeft' || event.key === 'ArrowUp' ? -1 : 1
            const nextIndex = (index + direction + options.length) % options.length
            onChange(options[nextIndex].value)
            const buttons = event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>('button')
            buttons?.[nextIndex]?.focus()
          }}
          className={cn(
            'rounded-[3px] font-medium transition-colors',
            size === 'sm' ? 'h-6 px-2 text-[12px]' : 'h-7 px-2.5 text-[13px]',
            value === o.value
              ? 'bg-surface-active text-accent'
              : 'text-faint hover:text-dim',
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Status / semantic badges
// ---------------------------------------------------------------------------

type BadgeTone =
  | 'live'
  | 'running'
  | 'queued'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'degraded'
  | 'stale'
  | 'reconnecting'
  | 'healthy'
  | 'connected'
  | 'buy'
  | 'sell'
  | 'hold'
  | 'positive'
  | 'neutral'
  | 'negative'
  | 'new'
  | 'idle'
  | 'win'
  | 'loss'

const TONE_MAP: Record<BadgeTone, { color: string; dot?: boolean }> = {
  live: { color: 'text-pos', dot: true },
  running: { color: 'text-accent', dot: true },
  queued: { color: 'text-neutral', dot: true },
  completed: { color: 'text-pos' },
  failed: { color: 'text-neg' },
  cancelled: { color: 'text-neutral' },
  degraded: { color: 'text-warn', dot: true },
  stale: { color: 'text-warn', dot: true },
  reconnecting: { color: 'text-warn', dot: true },
  healthy: { color: 'text-pos', dot: true },
  connected: { color: 'text-pos', dot: true },
  buy: { color: 'text-pos' },
  sell: { color: 'text-neg' },
  hold: { color: 'text-neutral' },
  positive: { color: 'text-pos' },
  neutral: { color: 'text-neutral' },
  negative: { color: 'text-neg' },
  new: { color: 'text-ml' },
  idle: { color: 'text-faint' },
  win: { color: 'text-pos' },
  loss: { color: 'text-neg' },
}

export function StatusBadge({
  tone,
  children,
  pulse,
}: {
  tone: BadgeTone
  children: ReactNode
  pulse?: boolean
}) {
  const m = TONE_MAP[tone]
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-[3px] border border-current/25 bg-current/10 px-1.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide',
        m.color,
      )}
    >
      {m.dot && (
        <span className={cn('h-1.5 w-1.5 rounded-full bg-current', pulse && 'csl-pulse')} />
      )}
      {children}
    </span>
  )
}

// BUY / SELL / HOLD signal chip — always icon + label + color (never color alone)
export function SignalTag({ side }: { side: 'buy' | 'sell' | 'hold' }) {
  if (side === 'hold')
    return (
      <span className="inline-flex items-center gap-1 rounded-[3px] bg-neutral/10 px-1.5 py-0.5 text-[11px] font-semibold uppercase text-neutral">
        <Minus size={11} /> Hold
      </span>
    )
  const buy = side === 'buy'
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-[3px] px-1.5 py-0.5 text-[11px] font-semibold uppercase',
        buy ? 'bg-pos/10 text-pos' : 'bg-neg/10 text-neg',
      )}
    >
      {buy ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
      {buy ? 'Buy' : 'Sell'}
    </span>
  )
}

// Signed numeric with direction arrow
export function Delta({ value, suffix = '%', className }: { value: number; suffix?: string; className?: string }) {
  const pos = value >= 0
  return (
    <span
      className={cn('inline-flex items-center gap-0.5 font-mono tabular-nums', pos ? 'text-pos' : 'text-neg', className)}
    >
      {pos ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
      {pos ? '+' : ''}
      {value.toFixed(value % 1 === 0 ? 0 : 2)}
      {suffix}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Panels
// ---------------------------------------------------------------------------

export function Panel({
  title,
  right,
  children,
  className,
  bodyClassName,
}: {
  title?: ReactNode
  right?: ReactNode
  children: ReactNode
  className?: string
  bodyClassName?: string
}) {
  return (
    <section className={cn('flex flex-col overflow-hidden border border-subtle bg-surface', className)}>
      {title && (
        <header className="flex h-9 shrink-0 items-center justify-between border-b border-subtle px-3">
          <h2 className="text-[13px] font-semibold text-ink">{title}</h2>
          {right}
        </header>
      )}
      <div className={cn('min-h-0 flex-1', bodyClassName)}>{children}</div>
    </section>
  )
}

// Compact metric cell used inside strips
export function Metric({
  label,
  value,
  tone,
  sub,
  info,
}: {
  label: string
  value: ReactNode
  tone?: 'pos' | 'neg' | 'default'
  sub?: ReactNode
  info?: ReactNode
}) {
  return (
    <div className="flex flex-col gap-0.5 px-4 py-2.5">
      <span className="text-[11px] font-medium uppercase tracking-wide text-faint">
        {info ? (
          <LearnTooltip content={info}>
            <span>{label}</span>
          </LearnTooltip>
        ) : (
          label
        )}
      </span>
      <span
        className={cn(
          'font-mono text-[16px] font-semibold tabular-nums',
          tone === 'pos' && 'text-pos',
          tone === 'neg' && 'text-neg',
          !tone && 'text-ink',
        )}
      >
        {value}
      </span>
      {sub && <span className="text-[11px] text-faint">{sub}</span>}
    </div>
  )
}

export function MetricStrip({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-wrap items-stretch divide-x divide-subtle border-b border-subtle bg-surface">
      {children}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Drawer (right context panel)
// ---------------------------------------------------------------------------

export function Drawer({
  open,
  onClose,
  title,
  subtitle,
  children,
  footer,
  width = 400,
}: {
  open: boolean
  onClose: () => void
  title: ReactNode
  subtitle?: ReactNode
  children: ReactNode
  footer?: ReactNode
  width?: number
}) {
  const titleId = useId()
  const dialogRef = useDialogFocus<HTMLElement>(open, onClose)

  if (!open) return null
  return (
    <div className="fixed inset-0 z-40 flex justify-end" style={{ animation: 'csl-fade-in 120ms ease-out' }}>
      <div className="absolute inset-0 bg-black/45" aria-hidden="true" onClick={onClose} />
      <aside
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="relative flex h-full flex-col border-l border-line bg-surface shadow-2xl"
        style={{ width: `min(${width}px, 100vw)` }}
      >
        <header className="flex items-start justify-between gap-3 border-b border-subtle px-4 py-3">
          <div className="min-w-0">
            <h3 id={titleId} className="truncate text-[14px] font-semibold text-ink">{title}</h3>
            {subtitle && <p className="mt-0.5 text-[12px] text-faint">{subtitle}</p>}
          </div>
          <IconBtn onClick={onClose} aria-label="Close drawer">
            <X size={16} />
          </IconBtn>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
        {footer && <footer className="border-t border-subtle p-3">{footer}</footer>}
      </aside>
    </div>
  )
}

// key/value provenance-style rows
export function KV({ k, v, mono = true }: { k: string; v: ReactNode; mono?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-1.5">
      <span className="shrink-0 text-[12px] text-faint">{k}</span>
      <span className={cn('text-right text-[12px] text-ink', mono && 'font-mono tabular-nums')}>{v}</span>
    </div>
  )
}

export function DrawerSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="border-b border-subtle px-4 py-3">
      <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-faint">{title}</div>
      {children}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Modal (confirmations)
// ---------------------------------------------------------------------------

export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
}: {
  open: boolean
  onClose: () => void
  title: ReactNode
  children: ReactNode
  footer: ReactNode
}) {
  const titleId = useId()
  const dialogRef = useDialogFocus<HTMLDivElement>(open, onClose)
  if (!open) return null
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-6"
      style={{ animation: 'csl-fade-in 120ms ease-out' }}
    >
      <div className="absolute inset-0 bg-black/55" aria-hidden="true" onClick={onClose} />
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="relative w-full max-w-md rounded-[10px] border border-line bg-surface shadow-2xl"
      >
        <header className="border-b border-subtle px-4 py-3">
          <h3 id={titleId} className="text-[15px] font-semibold text-ink">{title}</h3>
        </header>
        <div className="px-4 py-4 text-[13px] leading-relaxed text-dim">{children}</div>
        <footer className="flex justify-end gap-2 border-t border-subtle px-4 py-3">{footer}</footer>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Empty / degraded inline states
// ---------------------------------------------------------------------------

export function EmptyState({
  title,
  hint,
  action,
}: {
  title: string
  hint?: string
  action?: ReactNode
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 px-6 py-10 text-center">
      <p className="text-[13px] font-medium text-dim">{title}</p>
      {hint && <p className="max-w-sm text-[12px] leading-relaxed text-faint">{hint}</p>}
      {action && <div className="mt-1">{action}</div>}
    </div>
  )
}

export function ErrorState({
  title,
  hint,
  action,
  secondary,
}: {
  title: string
  hint?: string
  action?: ReactNode
  secondary?: ReactNode
}) {
  return (
    <div className="m-4 rounded-[8px] border border-neg/30 bg-neg/10 p-4">
      <div className="flex items-start gap-2.5">
        <TriangleAlert size={16} className="mt-0.5 shrink-0 text-neg" />
        <div className="min-w-0 flex-1">
          <p className="text-[13px] font-medium text-ink">{title}</p>
          {hint && <p className="mt-0.5 text-[12px] leading-relaxed text-dim">{hint}</p>}
          {(action || secondary) && (
            <div className="mt-3 flex items-center gap-2">
              {action}
              {secondary}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Beginner learning system — tooltips & popovers (progressive disclosure)
// ---------------------------------------------------------------------------

// Hover/focus tooltip attached to a small "?" affordance next to a term.
// Only renders the icon when explanations are enabled; label always shows.
export function LearnTooltip({
  children,
  content,
  always,
}: {
  children: ReactNode
  content: ReactNode
  always?: boolean
}) {
  const { showExplain } = useStore()
  const [open, setOpen] = useState(false)
  const show = always || showExplain
  return (
    <span className="inline-flex items-center gap-1">
      {children}
      {show && (
        <span
          className="relative inline-flex"
          onMouseEnter={() => setOpen(true)}
          onMouseLeave={() => setOpen(false)}
        >
          <button
            type="button"
            aria-label="Learn more"
            onFocus={() => setOpen(true)}
            onBlur={() => setOpen(false)}
            onClick={(e) => {
              e.stopPropagation()
              setOpen((o) => !o)
            }}
            className="text-faint transition-colors hover:text-accent"
          >
            <HelpCircle size={12} />
          </button>
          {open && (
            <span
              role="tooltip"
              className="absolute bottom-full left-1/2 z-50 mb-1.5 w-60 -translate-x-1/2 rounded-[8px] border border-line bg-surface px-3 py-2 text-left text-[11.5px] font-normal normal-case leading-relaxed text-dim shadow-xl"
              style={{ animation: 'csl-fade-in 100ms ease-out' }}
            >
              {content}
            </span>
          )}
        </span>
      )}
    </span>
  )
}

// Click-to-open explanatory popover anchored to a trigger element.
export function InfoPopover({
  trigger,
  title,
  children,
  align = 'left',
  width = 280,
}: {
  trigger: (props: { onClick: () => void; open: boolean }) => ReactNode
  title?: string
  children: ReactNode
  align?: 'left' | 'right'
  width?: number
}) {
  const [open, setOpen] = useState(false)
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
  return (
    <div ref={ref} className="relative inline-flex">
      {trigger({ onClick: () => setOpen((o) => !o), open })}
      {open && (
        <div
          className={cn(
            'absolute top-full z-50 mt-1.5 rounded-[8px] border border-line bg-surface p-3 shadow-xl',
            align === 'right' ? 'right-0' : 'left-0',
          )}
          style={{ width, animation: 'csl-fade-in 100ms ease-out' }}
        >
          {title && (
            <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-faint">{title}</div>
          )}
          <div className="text-[12px] leading-relaxed text-dim">{children}</div>
        </div>
      )}
    </div>
  )
}

// "Why?" inline learning link
export function WhyLink({ children }: { children: ReactNode }) {
  return (
    <InfoPopover
      width={260}
      trigger={({ onClick }) => (
        <button
          type="button"
          onClick={onClick}
          className="text-[11px] font-medium text-accent underline decoration-dotted underline-offset-2 hover:text-accent-hover"
        >
          Why?
        </button>
      )}
    >
      {children}
    </InfoPopover>
  )
}

// Small pill toggle switch with label
export function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean
  onChange: (v: boolean) => void
  label?: ReactNode
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="inline-flex items-center gap-2 text-[12px] text-dim hover:text-ink"
    >
      <span
        className={cn(
          'relative h-4 w-7 rounded-full transition-colors',
          checked ? 'bg-accent' : 'bg-surface-active',
        )}
      >
        <span
          className={cn(
            'absolute top-0.5 h-3 w-3 rounded-full bg-white transition-all',
            checked ? 'left-3.5' : 'left-0.5',
          )}
        />
      </span>
      {label}
    </button>
  )
}

// Recommended / beginner badge
export function RecoBadge({ children = 'Recommended' }: { children?: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-[3px] bg-pos/12 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-pos">
      <Check size={10} /> {children}
    </span>
  )
}

// Helper caption shown only when explanations are enabled
export function HelperText({ children }: { children: ReactNode }) {
  const { showExplain } = useStore()
  if (!showExplain) return null
  return <p className="text-[11.5px] leading-relaxed text-faint">{children}</p>
}

// Inline info banner (blue) — teaches without alarming
export function InfoNote({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-start gap-2 rounded-[6px] border border-info/25 bg-info/10 px-3 py-2 text-[12px] leading-relaxed text-info">
      <Info size={14} className="mt-0.5 shrink-0" />
      <span className="text-dim">{children}</span>
    </div>
  )
}

export function DegradedNote({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-center gap-2 border border-warn/30 bg-warn/10 px-3 py-2 text-[12px] text-warn">
      <TriangleAlert size={14} className="shrink-0" />
      <span className="leading-snug">{children}</span>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Toasts
// ---------------------------------------------------------------------------

export function Toasts() {
  const { toasts, dismissToast } = useStore()
  return (
    <div aria-live="polite" aria-relevant="additions" className="pointer-events-none fixed bottom-4 right-4 z-[60] flex w-80 flex-col gap-2">
      {toasts.map((t) => {
        const Icon = t.tone === 'positive' ? Check : t.tone === 'warning' ? TriangleAlert : Info
        const color =
          t.tone === 'positive' ? 'text-pos' : t.tone === 'warning' ? 'text-warn' : 'text-accent'
        return (
          <div
            key={t.id}
            role="status"
            className="pointer-events-auto flex items-start gap-2.5 rounded-[8px] border border-line bg-surface px-3 py-2.5 shadow-xl"
            style={{ animation: 'csl-fade-in 160ms ease-out' }}
          >
            <Icon size={15} className={cn('mt-0.5 shrink-0', color)} />
            <span className="flex-1 text-[12.5px] leading-snug text-ink">{t.text}</span>
            <button type="button" aria-label="Dismiss notification" onClick={() => dismissToast(t.id)} className="text-faint hover:text-ink">
              <X size={13} />
            </button>
          </div>
        )
      })}
    </div>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('csl-pulse rounded-[4px] bg-surface-active', className)} />
}
