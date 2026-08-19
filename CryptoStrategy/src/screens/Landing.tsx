import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import {
  Activity,
  ArrowRight,
  CandlestickChart,
  ChevronDown,
  GitBranch,
  History,
  Newspaper,
  Repeat,
  ServerCog,
  ShieldCheck,
  Trophy,
  Workflow,
} from 'lucide-react'
import { useStore, type Page } from '../lib/store'
import { CandleChart } from '../components/CandleChart'
import { useServices } from '../services/registry'
import { Button, cn, StatusBadge } from '../components/ui'

// ---------------------------------------------------------------------------
// Scroll infrastructure — the whole page lives inside one scroll container, so
// every observer needs that element as its root rather than the viewport.
// ---------------------------------------------------------------------------

const ScrollRootCtx = createContext<React.RefObject<HTMLDivElement | null> | null>(null)

function useScrollRoot() {
  return useContext(ScrollRootCtx)
}

// Reveal-on-scroll wrapper. Animates in once, respects prefers-reduced-motion
// via the CSS class, and reads the shared scroll root.
function Reveal({
  children,
  className,
  delay = 0,
  as: Tag = 'div',
  id,
}: {
  children: ReactNode
  className?: string
  delay?: number
  as?: 'div' | 'section' | 'li' | 'span'
  id?: string
}) {
  const rootRef = useScrollRoot()
  const ref = useRef<HTMLElement>(null)
  const [shown, setShown] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el || shown) return
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            setShown(true)
            io.disconnect()
          }
        }
      },
      { root: rootRef?.current ?? null, threshold: 0.15, rootMargin: '0px 0px -8% 0px' },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [rootRef, shown])
  return (
    <Tag
      // @ts-expect-error polymorphic ref
      ref={ref}
      id={id}
      className={cn('csl-reveal', shown && 'is-visible', className)}
      style={{ ['--csl-delay' as string]: `${delay}ms` }}
    >
      {children}
    </Tag>
  )
}

// ---------------------------------------------------------------------------
// Content
// ---------------------------------------------------------------------------

const WORKFLOW = [
  { label: 'Analyze', desc: 'Read multi-timeframe market structure.' },
  { label: 'Build', desc: 'Compose indicators into strategies.' },
  { label: 'Backtest', desc: 'Replay history, no real trades.' },
  { label: 'Rank', desc: 'Score candidates on a Top-K board.' },
  { label: 'Improve', desc: 'Search combinations continuously.' },
]

const CAPABILITIES: {
  icon: typeof CandlestickChart
  title: string
  body: string
  tags: string[]
  page: Page
}[] = [
  {
    icon: CandlestickChart,
    title: 'Multi-Timeframe Market',
    body: 'Analyze up to four independent crypto timeframes in one workspace, each with its own overlays and realtime state.',
    tags: ['Realtime', 'Beginner-friendly'],
    page: 'market',
  },
  {
    icon: Workflow,
    title: 'Strategy Builder',
    body: 'Configure MA, RSI, Bollinger Bands and Support/Resistance, then combine them into explainable composite strategies.',
    tags: ['Explainable'],
    page: 'strategies',
  },
  {
    icon: History,
    title: 'Backtesting & Search',
    body: 'Test strategies historically and automatically generate candidate combinations with a seeded Random Search.',
    tags: ['Reproducible'],
    page: 'backtests',
  },
  {
    icon: Trophy,
    title: 'Strategy Ranking',
    body: 'Compare candidate performance through quantitative metrics and a reproducible Top-K leaderboard.',
    tags: ['Explainable', 'Reproducible'],
    page: 'leaderboard',
  },
  {
    icon: Newspaper,
    title: 'News & Sentiment',
    body: 'Connect market news with model-generated sentiment — an optional service that degrades gracefully.',
    tags: ['Optional service'],
    page: 'news',
  },
  {
    icon: ServerCog,
    title: 'Operations',
    body: 'Monitor workers, queue depth, search loops, retries and dependency health from an integrated console.',
    tags: ['Advanced'],
    page: 'operations',
  },
]

const CREDIBILITY = [
  { icon: Activity, label: 'Realtime data' },
  { icon: Repeat, label: 'Deterministic backtests' },
  { icon: GitBranch, label: 'Versioned strategies' },
  { icon: ShieldCheck, label: 'Reproducible results' },
]

const GLOSSARY = [
  { term: 'Trading Pair', def: 'Two assets whose relative price is being analyzed, such as BTC/USDT.' },
  { term: 'Candle', def: 'A summary of price movement during one period of time.' },
  { term: 'Timeframe', def: 'The duration represented by one candle, such as 15 minutes or 1 hour.' },
  { term: 'Strategy', def: 'A set of rules that converts market information into BUY, SELL or HOLD signals.' },
  { term: 'Backtest', def: 'A simulation that applies a strategy to historical data.' },
  { term: 'Win Rate', def: 'The percentage of simulated trades that ended profitably.' },
  { term: 'Maximum Drawdown', def: 'The largest decline from a previous portfolio peak during a simulation.' },
  { term: 'Composite Strategy', def: 'A strategy that combines signals from several other strategies.' },
]

type StepKey = 'market' | 'timeframes' | 'strategies' | 'backtest' | 'compare'

const STEPS: {
  key: StepKey
  n: number
  title: string
  body: string
  hint?: string
  cta: { label: string; page: Page }
}[] = [
  {
    key: 'market',
    n: 1,
    title: 'Choose what you want to analyze',
    body: 'A trading pair compares one asset with another. BTC/USDT shows the price of Bitcoin in USDT.',
    hint: 'For the MVP, start with BTC/USDT.',
    cta: { label: 'View Market', page: 'market' },
  },
  {
    key: 'timeframes',
    n: 2,
    title: 'Look at the market from different timeframes',
    body: 'A timeframe sets how much time each candle represents. Short shows detail; long shows the broader trend.',
    hint: 'Not sure where to start? Use 15m and 1h.',
    cta: { label: 'View Market', page: 'market' },
  },
  {
    key: 'strategies',
    n: 3,
    title: 'Choose how the market should be analyzed',
    body: 'Each method reads the market differently. Use one strategy, or combine several into a composite.',
    cta: { label: 'Explore Strategies', page: 'strategies' },
  },
  {
    key: 'backtest',
    n: 4,
    title: 'Test the strategy on historical data',
    body: 'A backtest simulates how a strategy would have behaved. Results are historical — not a prediction.',
    cta: { label: 'See Backtesting', page: 'backtests' },
  },
  {
    key: 'compare',
    n: 5,
    title: 'Compare strategies and find stronger combinations',
    body: 'Strategies are ranked on several metrics at once. A higher rank means better under the test conditions — not a guaranteed winner.',
    cta: { label: 'View Leaderboard', page: 'leaderboard' },
  },
]

// ---------------------------------------------------------------------------
// Preview frame with signature corner accents
// ---------------------------------------------------------------------------

function PreviewFrame({ children, label }: { children: ReactNode; label?: string }) {
  return (
    <div className="relative">
      {/* corner accents */}
      <span className="pointer-events-none absolute -left-1.5 -top-1.5 z-10 h-4 w-4 rounded-tl-[6px] border-l border-t border-accent/50" />
      <span className="pointer-events-none absolute -right-1.5 -top-1.5 z-10 h-4 w-4 rounded-tr-[6px] border-r border-t border-accent/50" />
      <span className="pointer-events-none absolute -bottom-1.5 -left-1.5 z-10 h-4 w-4 rounded-bl-[6px] border-b border-l border-accent/50" />
      <span className="pointer-events-none absolute -bottom-1.5 -right-1.5 z-10 h-4 w-4 rounded-br-[6px] border-b border-r border-accent/50" />
      <div className="overflow-hidden rounded-[12px] border border-line bg-surface shadow-[0_24px_80px_-24px_rgba(0,0,0,0.7)] ring-1 ring-white/[0.02]">
        {label && (
          <div className="flex items-center gap-2 border-b border-subtle bg-canvas/60 px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-faint">
            <span className="h-1.5 w-1.5 rounded-full bg-accent" />
            {label}
          </div>
        )}
        {children}
      </div>
    </div>
  )
}

function StepPreview({ step }: { step: StepKey }) {
  const services = useServices()
  const leaderboard = services.leaderboard.listEntries()
  const c15 = services.market.getCandles('15m', 60)
  const c1h = services.market.getCandles('1h', 60)

  if (step === 'market') {
    return (
      <PreviewFrame label="Pair selector">
        <div className="p-4">
          <div className="flex items-center gap-2 rounded-[8px] border border-accent/40 bg-accent/10 px-3 py-3">
            <span className="grid h-7 w-7 place-items-center rounded-full bg-[#f7931a] text-[12px] font-bold text-black">₿</span>
            <div className="flex-1">
              <div className="font-mono text-[14px] font-medium text-ink">BTC / USDT</div>
              <div className="text-[11px] text-faint">Bitcoin priced in USDT · Binance</div>
            </div>
            <StatusBadge tone="live" pulse>Live</StatusBadge>
          </div>
          <div className="mt-3 flex items-baseline gap-2 px-1">
            <span className="font-mono text-[24px] font-semibold tabular-nums text-ink">63,008.57</span>
            <span className="font-mono text-[14px] text-pos">+1.82%</span>
          </div>
        </div>
      </PreviewFrame>
    )
  }

  if (step === 'timeframes') {
    return (
      <PreviewFrame label="Multi-timeframe">
        <div className="flex items-center gap-2 border-b border-subtle bg-canvas/40 px-3 py-2">
          {['5m', '15m', '1h', '4h'].map((t) => (
            <span
              key={t}
              className={cn(
                'rounded-[4px] px-2 py-0.5 font-mono text-[11px]',
                t === '15m' || t === '1h' ? 'bg-accent/15 text-accent' : 'text-faint',
              )}
            >
              {t}
            </span>
          ))}
          <span className="ml-auto text-[11px] text-faint">15m &amp; 1h recommended</span>
        </div>
        <div className="grid grid-cols-2 divide-x divide-subtle">
          <div className="p-2">
            <div className="mb-1 px-1 font-mono text-[10px] text-faint">BTCUSDT · 15m</div>
            <CandleChart candles={c15} overlays={{ ma20: true }} height={130} volume={false} compact />
          </div>
          <div className="p-2">
            <div className="mb-1 px-1 font-mono text-[10px] text-faint">BTCUSDT · 1h</div>
            <CandleChart candles={c1h} overlays={{ ma20: true, ma50: true }} height={130} volume={false} compact />
          </div>
        </div>
      </PreviewFrame>
    )
  }

  if (step === 'strategies') {
    const items = [
      { name: 'Moving Average', cat: 'Trend', desc: 'Identifies the general direction of price.' },
      { name: 'RSI', cat: 'Momentum', desc: 'Flags unusually strong buying or selling.' },
      { name: 'Bollinger Bands', cat: 'Volatility', desc: 'Shows how far price stretches from its average.' },
      { name: 'Support / Resistance', cat: 'Structure', desc: 'Finds levels the market reacts to.' },
    ]
    return (
      <PreviewFrame label="Analysis methods">
        <div className="divide-y divide-subtle">
          {items.map((s) => (
            <div key={s.name} className="px-4 py-2.5">
              <div className="flex items-center gap-2">
                <span className="text-[13px] font-medium text-ink">{s.name}</span>
                <span className="rounded-[3px] bg-surface-active px-1.5 py-0.5 text-[10px] uppercase text-faint">{s.cat}</span>
              </div>
              <p className="mt-0.5 text-[11.5px] text-dim">{s.desc}</p>
            </div>
          ))}
        </div>
      </PreviewFrame>
    )
  }

  if (step === 'backtest') {
    return (
      <PreviewFrame label="Backtest result">
        <div className="grid grid-cols-4 divide-x divide-subtle border-b border-subtle">
          {[
            ['Return', '+24.2%', 'text-pos'],
            ['Win Rate', '62%', 'text-ink'],
            ['Max DD', '-7.1%', 'text-neg'],
            ['Trades', '81', 'text-ink'],
          ].map(([l, v, c]) => (
            <div key={l} className="px-3 py-2.5">
              <div className="text-[10px] uppercase text-faint">{l}</div>
              <div className={cn('font-mono text-[15px] font-semibold tabular-nums', c)}>{v}</div>
            </div>
          ))}
        </div>
        <div className="p-2">
          <CandleChart candles={c15} overlays={{ ma20: true, sr: true }} height={150} volume={false} compact />
        </div>
        <p className="border-t border-subtle px-4 py-2.5 text-[11.5px] leading-relaxed text-dim">
          A positive historical return with a 7.1% maximum drawdown — one simulation, not a forecast.
        </p>
      </PreviewFrame>
    )
  }

  return (
    <PreviewFrame label="Leaderboard">
      <div className="divide-y divide-subtle">
        {leaderboard.map((r) => (
          <div key={r.rank} className={cn('flex items-center gap-2 px-4 py-2.5', r.rank === 1 && 'border-l-2 border-l-accent')}>
            <span className="w-4 font-mono text-[11px] text-faint">{r.rank}</span>
            <span className={cn('flex-1 truncate text-[12px]', r.rank === 1 ? 'text-ink' : 'text-dim')}>{r.strategy}</span>
            <span className="font-mono text-[11px] text-pos">+{r.ret}%</span>
            <span className="font-mono text-[13px] font-semibold tabular-nums text-ml">{r.score}</span>
          </div>
        ))}
      </div>
      <p className="border-t border-subtle px-4 py-2.5 text-[11.5px] leading-relaxed text-dim">
        Ranked by the Balanced v2 policy — a blend of return, win rate, drawdown and Sharpe.
      </p>
    </PreviewFrame>
  )
}

// ---------------------------------------------------------------------------
// Eyebrow label — a recurring signature cue
// ---------------------------------------------------------------------------

function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <div className="mb-4 inline-flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-faint">
      <span className="h-px w-6 bg-gradient-to-r from-accent to-transparent" />
      {children}
    </div>
  )
}

// ---------------------------------------------------------------------------
// How to use — sticky preview driven by which step is in view
// ---------------------------------------------------------------------------

function HowToUse() {
  const { navigate } = useStore()
  const rootRef = useScrollRoot()
  const [active, setActive] = useState(0)
  const stepRefs = useRef<(HTMLDivElement | null)[]>([])

  useEffect(() => {
    const io = new IntersectionObserver(
      (entries) => {
        // pick the entry closest to the centre band that is intersecting
        const visible = entries.filter((e) => e.isIntersecting)
        if (visible.length === 0) return
        let best = visible[0]
        for (const e of visible) if (e.intersectionRatio > best.intersectionRatio) best = e
        const idx = stepRefs.current.indexOf(best.target as HTMLDivElement)
        if (idx >= 0) setActive(idx)
      },
      { root: rootRef?.current ?? null, threshold: [0.4, 0.6, 0.8], rootMargin: '-30% 0px -30% 0px' },
    )
    stepRefs.current.forEach((el) => el && io.observe(el))
    return () => io.disconnect()
  }, [rootRef])

  const fillPct = ((active + 1) / STEPS.length) * 100

  return (
    <section id="how-to-use" className="relative mx-auto max-w-[1180px] px-6 py-24">
      <Reveal>
        <Eyebrow>Guided walkthrough</Eyebrow>
        <h2 className="max-w-2xl text-[30px] font-semibold leading-tight tracking-tight text-ink">
          How to use Crypto Strategy Lab
        </h2>
        <p className="mt-3 max-w-xl text-[15px] leading-relaxed text-dim">
          You don't need to build a strategy from scratch. Follow the path — choose a market, pick a
          few methods, test them on history, then compare.
        </p>
      </Reveal>

      <div className="mt-14 grid gap-12 lg:grid-cols-[1fr_1.05fr]">
        {/* stepper with a rail that fills as you scroll */}
        <ol className="relative">
          <span className="absolute left-[17px] top-2 bottom-2 w-px bg-subtle" />
          <span
            className="csl-rail-fill absolute left-[17px] top-2 w-px bg-gradient-to-b from-accent to-accent/30"
            style={{ height: `calc(${fillPct}% - 8px)` }}
          />
          {STEPS.map((s, i) => {
            const on = i === active
            return (
              <div
                key={s.key}
                ref={(el) => {
                  stepRefs.current[i] = el
                }}
                className="relative min-h-[42vh] pl-14"
              >
                <span
                  className={cn(
                    'absolute left-0 top-1 z-10 grid h-9 w-9 place-items-center rounded-full border font-mono text-[13px] font-semibold transition-all duration-300',
                    on
                      ? 'border-accent bg-accent text-white shadow-[0_0_0_5px_rgba(79,124,255,0.14)]'
                      : 'border-subtle bg-canvas text-faint',
                  )}
                >
                  {s.n}
                </span>
                <div className={cn('transition-all duration-500', on ? 'opacity-100' : 'opacity-45')}>
                  <h3 className={cn('text-[19px] font-semibold tracking-tight', on ? 'text-ink' : 'text-dim')}>
                    {s.title}
                  </h3>
                  <p className="mt-2 max-w-md text-[14px] leading-relaxed text-dim">{s.body}</p>
                  {s.hint && (
                    <p className="mt-3 inline-flex rounded-[5px] bg-accent/10 px-2.5 py-1 text-[12px] text-accent">
                      {s.hint}
                    </p>
                  )}
                  <div className="mt-4">
                    <Button
                      size="sm"
                      variant="default"
                      onClick={() => navigate(s.cta.page)}
                      className="transition-transform hover:-translate-y-0.5"
                    >
                      {s.cta.label}
                      <ArrowRight size={13} />
                    </Button>
                  </div>
                </div>
              </div>
            )
          })}
        </ol>

        {/* sticky preview */}
        <div className="hidden lg:block">
          <div className="sticky top-28">
            <div key={active} className="csl-swap">
              <StepPreview step={STEPS[active].key} />
            </div>
            <div className="mt-4 flex items-center justify-center gap-1.5">
              {STEPS.map((s, i) => (
                <span
                  key={s.key}
                  className={cn(
                    'h-1 rounded-full transition-all duration-300',
                    i === active ? 'w-6 bg-accent' : 'w-1.5 bg-subtle',
                  )}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Workflow — a compact connected band that summarises the walkthrough
// ---------------------------------------------------------------------------

function WorkflowBand() {
  return (
    <section id="workflow" className="mx-auto max-w-[1180px] px-6 py-20">
      <Reveal className="text-center">
        <Eyebrow>
          <span className="mx-auto">The loop, in five moves</span>
        </Eyebrow>
      </Reveal>
      <Reveal delay={80}>
        <div className="relative mt-4 overflow-hidden rounded-[16px] border border-subtle bg-gradient-to-b from-surface/80 to-workspace/40 p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-start">
            {WORKFLOW.map((s, i) => (
              <div key={s.label} className="flex flex-1 items-start gap-4 md:contents">
                <div className="flex-1 md:basis-0">
                  <div className="flex items-center gap-2">
                    <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-accent/15 font-mono text-[11px] font-semibold text-accent">
                      {i + 1}
                    </span>
                    <span className="text-[14px] font-semibold text-ink">{s.label}</span>
                  </div>
                  <p className="mt-1.5 text-[12px] leading-relaxed text-faint">{s.desc}</p>
                </div>
                {i < WORKFLOW.length - 1 && (
                  <ArrowRight size={16} className="mt-1 hidden shrink-0 text-faint md:block" />
                )}
              </div>
            ))}
          </div>
        </div>
      </Reveal>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Capabilities — editorial alternating rows, each tied to the story
// ---------------------------------------------------------------------------

function Capabilities() {
  const { navigate } = useStore()
  return (
    <section id="capabilities" className="mx-auto max-w-[1180px] px-6 py-20">
      <Reveal>
        <Eyebrow>What's inside</Eyebrow>
        <h2 className="max-w-2xl text-[30px] font-semibold leading-tight tracking-tight text-ink">
          Built for analysts, not gamblers
        </h2>
        <p className="mt-3 max-w-xl text-[15px] text-dim">
          Every capability maps back to a step in the walkthrough — the full experiment lifecycle,
          end to end.
        </p>
      </Reveal>

      <div className="mt-14 flex flex-col gap-5">
        {CAPABILITIES.map((c, i) => {
          const flip = i % 2 === 1
          return (
            <Reveal key={c.title} delay={(i % 2) * 60}>
              <button
                onClick={() => navigate(c.page)}
                className={cn(
                  'group grid w-full items-center gap-6 rounded-[16px] border border-subtle bg-surface/50 p-6 text-left transition-all duration-300 hover:-translate-y-0.5 hover:border-accent/40 hover:bg-surface md:grid-cols-[auto_1fr]',
                  flip && 'md:grid-cols-[1fr_auto]',
                )}
              >
                <div className={cn('flex items-center gap-4', flip && 'md:order-2 md:justify-end')}>
                  <span className="grid h-14 w-14 shrink-0 place-items-center rounded-[12px] border border-line bg-gradient-to-br from-accent/15 to-transparent text-accent transition-transform duration-300 group-hover:scale-105">
                    <c.icon size={24} />
                  </span>
                  <span className="font-mono text-[13px] tabular-nums text-faint md:hidden">
                    0{i + 1}
                  </span>
                </div>
                <div className={cn(flip && 'md:order-1')}>
                  <div className="flex items-center gap-2">
                    <span className="hidden font-mono text-[12px] tabular-nums text-faint md:inline">
                      0{i + 1}
                    </span>
                    <h3 className="text-[18px] font-semibold text-ink">{c.title}</h3>
                  </div>
                  <p className="mt-1.5 max-w-xl text-[13.5px] leading-relaxed text-dim">{c.body}</p>
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {c.tags.map((t) => (
                      <span
                        key={t}
                        className="rounded-full border border-subtle bg-workspace px-2.5 py-0.5 text-[11px] font-medium text-dim"
                      >
                        {t}
                      </span>
                    ))}
                    <span className="ml-auto inline-flex items-center gap-1 text-[12px] font-medium text-accent opacity-0 transition-opacity group-hover:opacity-100">
                      Open <ArrowRight size={13} />
                    </span>
                  </div>
                </div>
              </button>
            </Reveal>
          )
        })}
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Glossary — approachable knowledge layer
// ---------------------------------------------------------------------------

function Glossary() {
  const [open, setOpen] = useState<string | null>('Trading Pair')
  return (
    <section className="mx-auto max-w-[1180px] px-6 py-20">
      <Reveal className="text-center">
        <Eyebrow>
          <span className="mx-auto">Knowledge layer</span>
        </Eyebrow>
        <h2 className="text-[26px] font-semibold tracking-tight text-ink">New to these terms?</h2>
        <p className="mx-auto mt-2 max-w-lg text-[14px] text-dim">
          Short, plain-language definitions for the concepts you will meet inside the lab.
        </p>
      </Reveal>
      <div className="mx-auto mt-10 grid max-w-3xl gap-2.5 md:grid-cols-2">
        {GLOSSARY.map((g, i) => {
          const on = open === g.term
          return (
            <Reveal key={g.term} delay={(i % 2) * 60}>
              <div
                className={cn(
                  'rounded-[12px] border transition-colors',
                  on ? 'border-accent/40 bg-surface' : 'border-subtle bg-surface/40 hover:bg-surface/70',
                )}
              >
                <button
                  onClick={() => setOpen(on ? null : g.term)}
                  className="flex w-full items-center justify-between px-4 py-3 text-left"
                >
                  <span className="text-[13.5px] font-medium text-ink">{g.term}</span>
                  <ChevronDown size={15} className={cn('text-faint transition-transform', on && 'rotate-180')} />
                </button>
                {on && <p className="px-4 pb-3.5 text-[12.5px] leading-relaxed text-dim">{g.def}</p>}
              </div>
            </Reveal>
          )
        })}
      </div>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Closing — credibility flowing into the final CTA
// ---------------------------------------------------------------------------

function Closing() {
  const { navigate } = useStore()
  return (
    <section className="relative mx-auto max-w-[1180px] px-6 pb-28 pt-10">
      <Reveal>
        <div className="flex flex-wrap items-center justify-center gap-x-10 gap-y-4">
          {CREDIBILITY.map((c) => (
            <div key={c.label} className="flex items-center gap-2.5">
              <c.icon size={17} className="text-pos" />
              <span className="text-[13px] font-medium text-ink">{c.label}</span>
            </div>
          ))}
        </div>
      </Reveal>

      <Reveal delay={100}>
        <div className="relative mx-auto mt-16 max-w-2xl overflow-hidden rounded-[20px] border border-subtle bg-gradient-to-b from-surface/70 to-workspace/30 px-8 py-14 text-center">
          <div className="pointer-events-none absolute inset-x-0 -top-24 mx-auto h-48 w-48 rounded-full bg-accent/20 blur-[80px]" />
          <h2 className="relative text-[30px] font-semibold tracking-tight text-ink">
            Ready to test a strategy?
          </h2>
          <p className="relative mx-auto mt-3 max-w-md text-[14px] text-dim">
            Open the lab and follow the path you just read — no account, no funds, no real trades.
          </p>
          <div className="relative mt-7">
            <Button
              variant="primary"
              className="h-11 px-6 text-[14px] transition-transform hover:-translate-y-0.5"
              onClick={() => navigate('market')}
            >
              Open Strategy Lab
              <ArrowRight size={16} />
            </Button>
          </div>
        </div>
      </Reveal>

      <p className="mx-auto mt-16 max-w-xl text-center text-[12px] leading-relaxed text-faint">
        Crypto Strategy Lab is a research, analysis and simulation platform. It does not place real
        trades, hold funds, or provide financial advice.
      </p>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Navigation with scroll-spy
// ---------------------------------------------------------------------------

const NAV_LINKS: { id: string; label: string }[] = [
  { id: 'product', label: 'Product' },
  { id: 'how-to-use', label: 'How to Use' },
  { id: 'workflow', label: 'Workflow' },
  { id: 'capabilities', label: 'Capabilities' },
]

function LandingNav({ scrolled, activeId }: { scrolled: boolean; activeId: string }) {
  const { navigate } = useStore()
  const rootRef = useScrollRoot()
  const go = (id: string) => {
    const root = rootRef?.current
    const el = root?.querySelector(`#${id}`) as HTMLElement | null
    if (el && root) root.scrollTo({ top: el.offsetTop - 80, behavior: 'smooth' })
  }
  return (
    <header
      className={cn(
        'sticky top-0 z-30 border-b transition-all duration-300',
        scrolled ? 'border-subtle bg-canvas/85 backdrop-blur-md' : 'border-transparent bg-transparent',
      )}
    >
      <div className="mx-auto flex h-16 max-w-[1180px] items-center gap-2 px-6">
        <span className="grid h-7 w-7 place-items-center rounded-[6px] bg-accent text-[12px] font-bold text-white">
          CSL
        </span>
        <span className="text-[14px] font-semibold tracking-tight text-ink">Crypto Strategy Lab</span>
        <nav className="ml-8 hidden items-center gap-1 md:flex">
          {NAV_LINKS.map((l) => (
            <button
              key={l.id}
              onClick={() => go(l.id)}
              className={cn(
                'rounded-[5px] px-3 py-1.5 text-[13px] transition-colors',
                activeId === l.id ? 'text-ink' : 'text-dim hover:text-ink',
              )}
            >
              <span className="relative">
                {l.label}
                {activeId === l.id && (
                  <span className="absolute -bottom-1 left-0 h-px w-full bg-accent" />
                )}
              </span>
            </button>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={() => go('how-to-use')}
            className="hidden h-9 items-center rounded-[5px] px-3 text-[13px] text-dim hover:text-ink sm:flex"
          >
            Learn How It Works
          </button>
          <Button variant="primary" onClick={() => navigate('market')}>
            Open Strategy Lab
          </Button>
        </div>
      </div>
    </header>
  )
}

// ---------------------------------------------------------------------------
// Hero
// ---------------------------------------------------------------------------

function ProductPreview() {
  const services = useServices()
  const market = services.market.listMarkets()[0]
  const searchRun = services.backtests.searchRun
  const leaderboard = services.leaderboard.listEntries()
  const c1 = services.market.getCandles('15m', 60)
  const c2 = services.market.getCandles('1h', 60)
  const pct = Math.round((searchRun.tested / searchRun.candidateLimit) * 100)
  return (
    <PreviewFrame>
      <div className="flex h-9 items-center gap-2 border-b border-subtle bg-canvas/60 px-3">
        <span className="font-mono text-[11px] font-medium text-ink">{market.pair}</span>
        <span className="rounded-[3px] bg-surface-active px-1 text-[10px] text-faint">Binance</span>
        <span className="font-mono text-[11px] tabular-nums text-ink">63,008.57</span>
        <span className="font-mono text-[11px] tabular-nums text-pos">+1.82%</span>
        <div className="ml-auto">
          <StatusBadge tone="live" pulse>Live</StatusBadge>
        </div>
      </div>
      <div className="grid grid-cols-2 divide-x divide-subtle border-b border-subtle">
        <div className="p-1.5">
          <div className="mb-1 px-1 font-mono text-[10px] text-faint">{market.pair} · 15m</div>
          <CandleChart candles={c1} overlays={{ ma20: true }} height={120} volume={false} compact />
        </div>
        <div className="p-1.5">
          <div className="mb-1 px-1 font-mono text-[10px] text-faint">{market.pair} · 1h</div>
          <CandleChart candles={c2} overlays={{ ma20: true, ma50: true }} height={120} volume={false} compact />
        </div>
      </div>
      <div className="flex items-center gap-3 border-b border-subtle px-3 py-2">
        <StatusBadge tone="running" pulse>Running</StatusBadge>
        <span className="font-mono text-[11px] text-dim">{searchRun.id}</span>
        <div className="flex-1">
          <div className="h-1.5 overflow-hidden rounded-full bg-surface-active">
            <div className="h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
          </div>
        </div>
        <span className="font-mono text-[11px] tabular-nums text-faint">
          {searchRun.tested} / {searchRun.candidateLimit}
        </span>
      </div>
      <div className="px-3 py-2">
        <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-faint">Live Top-K</div>
        <div className="space-y-1">
          {leaderboard.slice(0, 3).map((r) => (
            <div key={r.rank} className="flex items-center gap-2 text-[11px]">
              <span className="w-3 font-mono text-faint">{r.rank}</span>
              <span className={cn('flex-1 truncate', r.rank === 1 ? 'text-ink' : 'text-dim')}>{r.strategy}</span>
              {r.rank === 1 && <StatusBadge tone="new">Top</StatusBadge>}
              <span className="font-mono tabular-nums text-ink">{r.score}</span>
            </div>
          ))}
        </div>
      </div>
    </PreviewFrame>
  )
}

function Hero() {
  const { navigate } = useStore()
  const rootRef = useScrollRoot()
  const scrollToHow = () => {
    const root = rootRef?.current
    const el = root?.querySelector('#how-to-use') as HTMLElement | null
    if (el && root) root.scrollTo({ top: el.offsetTop - 80, behavior: 'smooth' })
  }
  return (
    <section id="product" className="relative mx-auto max-w-[1180px] px-6 pb-8 pt-16 md:pt-24">
      <div className="grid items-center gap-12 lg:grid-cols-[1fr_1.05fr]">
        <Reveal>
          <Eyebrow>Crypto strategy research &amp; simulation</Eyebrow>
          <h1 className="max-w-xl text-[44px] font-semibold leading-[1.08] tracking-tight text-ink">
            Research crypto strategies with reproducible evidence.
          </h1>
          <p className="mt-5 max-w-lg text-[16px] leading-relaxed text-dim">
            Build, backtest and compare crypto strategies using market data — without placing real
            trades.
          </p>
          <p className="mt-3 max-w-lg text-[13.5px] leading-relaxed text-faint">
            New to crypto analysis? Start with guided presets and learn each step as you go.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Button
              variant="primary"
              className="h-11 px-5 text-[14px] transition-transform hover:-translate-y-0.5"
              onClick={() => navigate('market')}
            >
              Open Strategy Lab
              <ArrowRight size={16} />
            </Button>
            <button
              onClick={scrollToHow}
              className="inline-flex h-11 items-center rounded-[5px] border border-line px-5 text-[14px] text-ink transition-colors hover:bg-surface-hover"
            >
              Learn How It Works
            </button>
          </div>
          <p className="mt-7 font-mono text-[12px] text-faint">
            Realtime market data · Deterministic backtests · Versioned experiments
          </p>
        </Reveal>
        <Reveal delay={120}>
          <ProductPreview />
        </Reveal>
      </div>

      {/* scroll cue that connects the hero to the story below */}
      <button
        onClick={scrollToHow}
        className="mx-auto mt-16 flex flex-col items-center gap-2 text-faint transition-colors hover:text-dim"
      >
        <span className="text-[11px] uppercase tracking-[0.18em]">Scroll to explore</span>
        <span className="h-8 w-px bg-gradient-to-b from-accent/60 to-transparent" />
        <ChevronDown size={16} className="csl-pulse" />
      </button>
    </section>
  )
}

// ---------------------------------------------------------------------------

export function Landing() {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [scrolled, setScrolled] = useState(false)
  const [activeId, setActiveId] = useState('product')

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    const onScroll = () => setScrolled(el.scrollTop > 40)
    el.addEventListener('scroll', onScroll, { passive: true })
    return () => el.removeEventListener('scroll', onScroll)
  }, [])

  // section scroll-spy for the nav
  useEffect(() => {
    const root = scrollRef.current
    if (!root) return
    const io = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting)
        if (visible.length === 0) return
        let best = visible[0]
        for (const e of visible) if (e.intersectionRatio > best.intersectionRatio) best = e
        if (best.target.id) setActiveId(best.target.id)
      },
      { root, threshold: 0.3, rootMargin: '-20% 0px -60% 0px' },
    )
    NAV_LINKS.forEach((l) => {
      const el = root.querySelector(`#${l.id}`)
      if (el) io.observe(el)
    })
    return () => io.disconnect()
  }, [])

  return (
    <ScrollRootCtx.Provider value={scrollRef}>
      <div ref={scrollRef} className="relative h-screen overflow-y-auto bg-canvas">
        {/* ambient depth — restrained glows, one continuous canvas */}
        <div className="pointer-events-none fixed inset-0 z-0">
          <div className="absolute -left-40 top-0 h-[520px] w-[520px] rounded-full bg-accent/10 blur-[130px]" />
          <div className="absolute right-0 top-[40%] h-[440px] w-[440px] rounded-full bg-ml/[0.07] blur-[130px]" />
          <div className="absolute bottom-0 left-1/3 h-[420px] w-[420px] rounded-full bg-accent/[0.06] blur-[130px]" />
        </div>

        <div className="relative z-10">
          <LandingNav scrolled={scrolled} activeId={activeId} />
          <Hero />
          <HowToUse />
          <WorkflowBand />
          <Capabilities />
          <Glossary />
          <Closing />
        </div>
      </div>
    </ScrollRootCtx.Provider>
  )
}
