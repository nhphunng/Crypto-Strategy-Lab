import { useMemo, useState } from 'react'
import {
  ArrowLeft,
  Check,
  ChevronDown,
  GitBranch,
  Info,
  RotateCcw,
  Scale,
  TriangleAlert,
  Vote,
  Sparkles,
} from 'lucide-react'
import { useStore } from '../lib/store'
import {
  STRATEGY_PRESENTATION as STRAT_META,
  STRATEGY_PRESETS as PRESETS,
  recommendedStrategyValues,
  validateStrategyParameters,
  validateStrategyWeights,
  type StrategyPreset as Preset,
  type StrategyPresentation as StratMeta,
  type StrategySignal as Sig,
} from '../config'
import { useServices } from '../services/registry'
import { PageHeader } from '../components/Shell'
import { MarketSelector } from '../components/MarketSelector'
import { StrategyGenerationForm } from '../features/strategies/components/StrategyGenerationForm'
import { GeneratedStrategyReview } from '../features/strategies/components/GeneratedStrategyReview'
import type { GeneratedDraft } from '../features/strategies/types'
import {
  Button,
  cn,
  Drawer,
  DrawerSection,
  HelperText,
  KV,
  RecoBadge,
  Segmented,
  SignalTag,
} from '../components/ui'

// ---------------------------------------------------------------------------
// Strategy metadata — plain-language layer over the technical STRATEGIES.
// Beginners see friendly names & purposes; version/id stay in Strategy Details.
// ---------------------------------------------------------------------------

const SIGNAL_VALUE: Record<Sig, number> = { buy: 1, sell: -1, hold: 0 }

function useStrategyCatalog() {
  const services = useServices()
  const methods = services.strategies.listMethods()
  const byId = (id: string) => {
    const strategy = services.strategies.getMethod(id)
    if (!strategy) throw new Error(`Unknown strategy method: ${id}`)
    return strategy
  }
  const recommendedValues = (id: string) => recommendedStrategyValues(byId(id))
  return { methods, byId, recommendedValues }
}

function fmtSigned(n: number) {
  const r = Math.round(n * 100) / 100
  return `${r > 0 ? '+' : r < 0 ? '−' : ''}${Math.abs(r).toFixed(2)}`
}

// ---------------------------------------------------------------------------
// Stepper header
// ---------------------------------------------------------------------------

type Phase = 1 | 2 | 3 | 4

const STEP_LABELS: Record<Phase, string> = {
  1: 'Choose methods',
  2: 'Configure',
  3: 'Combine',
  4: 'Review & Test',
}

function Stepper({
  step,
  single,
  onGo,
}: {
  step: Phase
  single: boolean
  onGo: (p: Phase) => void
}) {
  const phases: Phase[] = [1, 2, 3, 4]
  return (
    <div className="flex shrink-0 items-center gap-1 border-b border-subtle bg-surface px-5 py-2.5 text-[12px]">
      {phases.map((p, i) => {
        const skipped = p === 3 && single
        const completed = p < step && !skipped
        const current = p === step
        const clickable = p < step && !skipped
        return (
          <span key={p} className="flex items-center gap-1">
            <button
              disabled={!clickable}
              onClick={() => clickable && onGo(p)}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-[6px] px-2 py-1 font-medium transition-colors',
                current && 'bg-accent/15 text-accent',
                completed && 'text-dim hover:bg-surface-hover hover:text-ink',
                !current && !completed && 'text-faint',
                skipped && 'italic',
                !clickable && 'cursor-default',
              )}
            >
              <span
                className={cn(
                  'grid h-4 w-4 place-items-center rounded-full text-[10px] font-semibold',
                  current ? 'bg-accent text-white' : completed ? 'bg-pos/20 text-pos' : 'bg-surface-active text-faint',
                )}
              >
                {completed ? <Check size={11} /> : skipped ? '–' : p}
              </span>
              {skipped ? 'Combine not needed' : STEP_LABELS[p]}
            </button>
            {i < phases.length - 1 && (
              <span className={cn('mx-0.5 h-px w-5 transition-colors', p < step ? 'bg-pos/40' : 'bg-subtle')} />
            )}
          </span>
        )
      })}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Bottom action bar
// ---------------------------------------------------------------------------

function ActionBar({
  back,
  status,
  statusTone = 'faint',
  primary,
}: {
  back?: () => void
  status?: React.ReactNode
  statusTone?: 'faint' | 'pos' | 'neg'
  primary: { label: string; onClick: () => void; disabled?: boolean }
}) {
  return (
    <div className="flex shrink-0 items-center gap-3 border-t border-line bg-surface px-5 py-3">
      {back ? (
        <button
          onClick={back}
          className="inline-flex items-center gap-1.5 rounded-[6px] border border-subtle bg-workspace px-3 py-1.5 text-[12.5px] text-dim hover:bg-surface-hover hover:text-ink"
        >
          <ArrowLeft size={14} /> Back
        </button>
      ) : (
        <span />
      )}
      {status && (
        <span
          className={cn(
            'text-[12px]',
            statusTone === 'pos' && 'text-pos',
            statusTone === 'neg' && 'text-neg',
            statusTone === 'faint' && 'text-faint',
          )}
        >
          {status}
        </span>
      )}
      <Button variant="primary" className="ml-auto" disabled={primary.disabled} onClick={primary.onClick}>
        {primary.label}
      </Button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Orientation aside (steps 2–4)
// ---------------------------------------------------------------------------

function SummaryAside({
  selected,
  market,
  timeframe,
  status,
}: {
  selected: string[]
  market: { display: string }
  timeframe: string
  status: string
}) {
  return (
    <aside className="hidden w-[220px] shrink-0 border-l border-subtle bg-surface/50 p-4 lg:block">
      <div className="text-[10px] font-semibold uppercase tracking-wide text-faint">Your strategy</div>
      <div className="mt-2 font-mono text-[12px] text-ink">
        {market.display} · {timeframe}
      </div>
      <div className="mt-4 text-[10px] font-semibold uppercase tracking-wide text-faint">
        Methods · {selected.length}
      </div>
      <div className="mt-1.5 space-y-1">
        {selected.map((id) => (
          <div key={id} className="text-[12px] text-dim">
            {STRAT_META[id].friendly}
          </div>
        ))}
        {selected.length === 0 && <div className="text-[12px] text-faint">None yet</div>}
      </div>
      <div className="mt-4 text-[10px] font-semibold uppercase tracking-wide text-faint">Status</div>
      <div className="mt-1 text-[12px] text-dim">{status}</div>
    </aside>
  )
}

// ---------------------------------------------------------------------------
// Main screen
// ---------------------------------------------------------------------------

export function Strategies() {
  const { navigate, setActiveStrategy, toast, showExplain, market, timeframe } = useStore()
  const { byId: stratById, recommendedValues } = useStrategyCatalog()

  const [step, setStep] = useState<Phase>(1)
  const [dir, setDir] = useState<'fwd' | 'back'>('fwd')
  const [selected, setSelected] = useState<string[]>([])
  const [params, setParams] = useState<Record<string, Record<string, number>>>({})
  const [method, setMethod] = useState<'majority' | 'weighted'>('majority')
  const [weights, setWeights] = useState<Record<string, number>>({})
  const [tie, setTie] = useState<Sig>('hold')
  const [buyTh, setBuyTh] = useState(0.3)
  const [sellTh, setSellTh] = useState(-0.3)
  const [advanced, setAdvanced] = useState(false)
  const [configActive, setConfigActive] = useState<string | null>(null)
  const [inspector, setInspector] = useState(false)
  const [generationOpen, setGenerationOpen] = useState(false)
  const [generatedDrafts, setGeneratedDrafts] = useState<GeneratedDraft[]>([])

  const single = selected.length === 1
  const paramsFor = (id: string) => params[id] ?? recommendedValues(id)

  const ensureWeights = (ids: string[]) => {
    setWeights((prev) => {
      const even = Math.round(100 / Math.max(ids.length, 1))
      const next: Record<string, number> = {}
      let acc = 0
      ids.forEach((id, i) => {
        const v = i === ids.length - 1 ? 100 - acc : (prev[id] ?? even)
        next[id] = v
        acc += v
      })
      return next
    })
  }

  const toggleMethod = (id: string) => {
    setSelected((prev) => {
      const next = prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
      ensureWeights(next)
      return next
    })
    setParams((p) => (p[id] ? p : { ...p, [id]: recommendedValues(id) }))
  }

  const applyPreset = (p: Preset) => {
    setSelected(p.ids)
    setMethod('majority')
    setParams(Object.fromEntries(p.ids.map((id) => [id, recommendedValues(id)])))
    ensureWeights(p.ids)
    toast(`${p.name} selected`, 'positive')
  }

  const goTo = (p: Phase) => {
    setDir(p > step ? 'fwd' : 'back')
    setStep(p)
  }

  const members = selected.map((id) => ({ id, ...STRAT_META[id] }))
  const isCombine = !single && selected.length >= 2

  const { total: totalWeight, valid: weightValid } = validateStrategyWeights(selected, weights)
  const balanceWeights = () => ensureWeights(selected)

  // per-method validity for the Configure step
  const invalidById = useMemo(() => {
    const map: Record<string, string | null> = {}
    selected.forEach((id) => (map[id] = validateStrategyParameters(stratById(id), paramsFor(id))))
    return map
  }, [selected, params])
  const configuredCount = selected.filter((id) => !invalidById[id]).length
  const allConfigured = selected.length > 0 && configuredCount === selected.length

  // decision preview
  const decision = useMemo<Decision | null>(() => {
    if (selected.length === 0) return null
    if (!isCombine) return { side: members[0].signal, kind: 'single' }
    if (method === 'weighted') {
      const score = members.reduce((a, m) => a + ((weights[m.id] ?? 0) / 100) * SIGNAL_VALUE[m.signal], 0)
      const rounded = Math.round(score * 100) / 100
      const side: Sig = rounded >= buyTh ? 'buy' : rounded <= sellTh ? 'sell' : 'hold'
      return { side, kind: 'weighted', score: rounded }
    }
    const buys = members.filter((m) => m.signal === 'buy').length
    const sells = members.filter((m) => m.signal === 'sell').length
    const side: Sig = buys > sells ? 'buy' : sells > buys ? 'sell' : tie
    return { side, kind: 'majority', buys, sells, tied: buys === sells }
  }, [selected, isCombine, method, members, weights, buyTh, sellTh, tie])

  function buildName() {
    const abbr = selected.map((id) => STRAT_META[id].abbr).join(' + ')
    return isCombine ? `${abbr} · ${method === 'majority' ? 'Majority Vote' : 'Weighted'}` : abbr
  }

  function runBacktest() {
    const name = buildName()
    setActiveStrategy(name)
    navigate('backtests', { backtestTab: 'single', strategyName: name })
    toast(`Prefilled ${name} on ${market.display} · ${timeframe}`, 'info')
  }

  // advance from Configure — skip Combine when single
  const continueFromConfigure = () => goTo(single ? 4 : 3)
  const backFromReview = () => goTo(single ? 2 : 3)

  return (
    <div className="flex h-full flex-col">
      <PageHeader title="Strategies">
        <Button variant="default" onClick={() => setGenerationOpen((value) => !value)}>
          <Sparkles size={14} /> Generate Strategy
        </Button>
        <Button variant="default" onClick={() => setInspector(true)}>
          <GitBranch size={14} /> Strategy Details
        </Button>
      </PageHeader>

      {generationOpen && (
        <div className="max-h-[55vh] shrink-0 overflow-auto border-b border-line">
          <StrategyGenerationForm onDrafts={setGeneratedDrafts} />
          {generatedDrafts.map((draft) => (
            <GeneratedStrategyReview
              key={draft.id}
              draft={draft}
              onActivated={(label) => {
                toast(`${label} is available for later workflows`, 'positive')
                setGeneratedDrafts((items) => items.filter((item) => item.id !== draft.id))
              }}
            />
          ))}
          {generatedDrafts.length === 0 && (
            <p className="bg-workspace px-5 py-3 text-[11px] text-faint">A source may validly produce zero drafts.</p>
          )}
        </div>
      )}

      {/* market context bar — always visible */}
      <div className="flex shrink-0 flex-wrap items-center gap-x-6 gap-y-2 border-b border-subtle bg-surface px-5 py-2.5">
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-wide text-faint">Market</div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[13px] font-medium text-ink">{market.display}</span>
            <span className="text-[11px] text-faint">
              {market.name} priced in {market.quote}
            </span>
          </div>
        </div>
        <div>
          <div className="text-[10px] font-semibold uppercase tracking-wide text-faint">Timeframe</div>
          <span className="font-mono text-[13px] text-ink">{timeframe}</span>
        </div>
        <MarketSelector
          trigger={({ onClick }) => (
            <button
              onClick={onClick}
              className="ml-auto inline-flex h-7 items-center gap-1.5 rounded-[5px] border border-subtle bg-workspace px-2.5 text-[12px] text-dim hover:bg-surface-hover hover:text-ink"
            >
              Change Market
            </button>
          )}
        />
      </div>

      <Stepper step={step} single={single} onGo={goTo} />

      {/* phase body */}
      <div className="flex min-h-0 flex-1">
        <div key={step} className={cn('flex min-h-0 flex-1 flex-col', dir === 'fwd' ? 'csl-step-fwd' : 'csl-step-back')}>
          {step === 1 && (
            <StepChoose
              selected={selected}
              showExplain={showExplain}
              market={market}
              onPreset={applyPreset}
              onToggle={toggleMethod}
              onContinue={() => {
                setConfigActive(selected[0] ?? null)
                goTo(2)
              }}
            />
          )}

          {step === 2 && (
            <StepConfigure
              selected={selected}
              active={configActive && selected.includes(configActive) ? configActive : selected[0] ?? null}
              setActive={setConfigActive}
              paramsFor={paramsFor}
              onChange={(id, v) => setParams((p) => ({ ...p, [id]: v }))}
              invalidById={invalidById}
              configuredCount={configuredCount}
              allConfigured={allConfigured}
              showExplain={showExplain}
              market={market}
              timeframe={timeframe}
              onBack={() => goTo(1)}
              onContinue={continueFromConfigure}
            />
          )}

          {step === 3 && isCombine && (
            <StepCombine
              members={members}
              method={method}
              setMethod={setMethod}
              weights={weights}
              setWeights={setWeights}
              weightValid={weightValid}
              totalWeight={totalWeight}
              balanceWeights={balanceWeights}
              tie={tie}
              setTie={setTie}
              buyTh={buyTh}
              setBuyTh={setBuyTh}
              sellTh={sellTh}
              setSellTh={setSellTh}
              advanced={advanced}
              setAdvanced={setAdvanced}
              decision={decision}
              showExplain={showExplain}
              market={market}
              timeframe={timeframe}
              onBack={() => goTo(2)}
              onContinue={() => goTo(4)}
            />
          )}

          {step === 4 && (
            <StepReview
              selected={selected}
              single={single}
              method={method}
              weights={weights}
              tie={tie}
              buyTh={buyTh}
              sellTh={sellTh}
              paramsFor={paramsFor}
              decision={decision}
              showExplain={showExplain}
              market={market}
              timeframe={timeframe}
              onEditMethods={() => goTo(2)}
              onEditCombine={() => goTo(3)}
              onBack={backFromReview}
              onRun={runBacktest}
              onSave={() => toast(`Saved ${buildName()} as a new version`, 'positive')}
            />
          )}
        </div>
      </div>

      {/* Strategy Details */}
      <Drawer
        open={inspector}
        onClose={() => setInspector(false)}
        title="Strategy Details"
        subtitle={selected.length ? buildName() : 'No strategy selected'}
      >
        <DrawerSection title="Version & provenance">
          <KV
            k="Strategy ID"
            v={
              selected.length
                ? `cs-${selected.map((id) => STRAT_META[id].abbr.toLowerCase().replace('/', '')).join('-')}`
                : '—'
            }
          />
          <KV k="Plugin type" v={isCombine ? 'Composite' : 'Single method'} />
          <KV k="Version" v={<span className="text-ml">v1 (draft)</span>} />
          <KV k="Created" v="2026-08-16 18:20" />
          <div className="mt-2 flex items-center gap-1.5 rounded-[5px] border border-warn/30 bg-warn/10 px-2 py-1.5 text-[11px] text-warn">
            <Info size={12} /> Historical versions are immutable — saving creates a new version.
          </div>
        </DrawerSection>
        {selected.map((id) => {
          const strat = stratById(id)
          const m = STRAT_META[id]
          return (
            <DrawerSection key={id} title={`${m.friendly} · ${m.tech}`}>
              {strat.params.map((p) => (
                <KV key={p.key} k={p.label} v={`${paramsFor(id)[p.key]}  (${p.min}–${p.max})`} />
              ))}
              <div className="mt-1.5 space-y-0.5">
                {strat.rules.map((r, i) => (
                  <div key={i} className="font-mono text-[11px] text-dim">
                    {r.text} → {r.side.toUpperCase()}
                  </div>
                ))}
              </div>
            </DrawerSection>
          )
        })}
        {isCombine && (
          <DrawerSection title="Composite decision trace">
            <div className="space-y-1 font-mono text-[11px] text-dim">
              {members.map((m) => (
                <div key={m.id}>
                  {m.abbr} → {m.signal.toUpperCase()}
                  {method === 'weighted' && (
                    <span className="text-faint"> (w {((weights[m.id] ?? 0) / 100).toFixed(2)})</span>
                  )}
                </div>
              ))}
              {decision && (
                <div className="border-t border-subtle pt-1 text-ml">
                  {method === 'weighted' && decision.kind === 'weighted'
                    ? `weighted = ${fmtSigned(decision.score)} → ${decision.side.toUpperCase()}`
                    : `majority → ${decision.side.toUpperCase()}`}
                </div>
              )}
            </div>
          </DrawerSection>
        )}
      </Drawer>
    </div>
  )
}

// ===========================================================================
// STEP 1 — CHOOSE METHODS
// ===========================================================================

function StepChoose({
  selected,
  showExplain,
  market,
  onPreset,
  onToggle,
  onContinue,
}: {
  selected: string[]
  showExplain: boolean
  market: { display: string }
  onPreset: (p: Preset) => void
  onToggle: (id: string) => void
  onContinue: () => void
}) {
  const { methods } = useStrategyCatalog()
  const presetSelected = (p: Preset) =>
    p.ids.length === selected.length && p.ids.every((id) => selected.includes(id))

  return (
    <>
      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5 pb-8">
        <div className="mx-auto max-w-3xl">
          <h2 className="text-[16px] font-semibold text-ink">Choose how you want to analyze {market.display}</h2>
          {showExplain && (
            <p className="mt-1 text-[12.5px] text-dim">Start with a recommended setup or build your own.</p>
          )}

          {/* presets */}
          <div className="mt-4 grid gap-2.5 md:grid-cols-3">
            {PRESETS.map((p) => {
              const on = presetSelected(p)
              return (
                <div
                  key={p.id}
                  className={cn(
                    'flex flex-col rounded-[10px] border p-3.5 transition-colors',
                    on ? 'border-accent/50 bg-accent/10' : 'border-subtle bg-workspace',
                  )}
                >
                  <div className="flex items-center gap-1.5">
                    <span className="text-[13.5px] font-semibold text-ink">{p.name}</span>
                    {p.recommended && <RecoBadge>Recommended</RecoBadge>}
                  </div>
                  <div className="mt-1.5 text-[12px] text-dim">
                    {p.ids.map((id) => STRAT_META[id].friendly).join(' + ')}
                  </div>
                  {showExplain && (
                    <p className="mt-1.5 text-[11.5px] leading-relaxed text-faint">{p.tagline}</p>
                  )}
                  <Button
                    size="sm"
                    variant={on ? 'default' : 'primary'}
                    className="mt-3 w-full justify-center"
                    onClick={() => onPreset(p)}
                  >
                    {on ? (
                      <>
                        <Check size={13} /> Selected
                      </>
                    ) : (
                      'Select'
                    )}
                  </Button>
                </div>
              )
            })}
          </div>

          {/* divider */}
          <div className="my-6 flex items-center gap-3 text-[11px] uppercase tracking-wide text-faint">
            <span className="h-px flex-1 bg-subtle" />
            Or build your own
            <span className="h-px flex-1 bg-subtle" />
          </div>

          {showExplain && (
            <p className="mb-3 -mt-2 text-center text-[12px] text-dim">Choose one or more analysis methods.</p>
          )}

          {/* build your own */}
          <div className="space-y-2">
            {methods.map((s) => {
              const m = STRAT_META[s.id]
              const on = selected.includes(s.id)
              return (
                <button
                  key={s.id}
                  onClick={() => onToggle(s.id)}
                  className={cn(
                    'flex w-full items-start gap-3 rounded-[9px] border p-3 text-left transition-colors',
                    on ? 'border-accent/50 bg-accent/10' : 'border-subtle bg-workspace hover:bg-surface-hover',
                  )}
                >
                  <span
                    className={cn(
                      'mt-0.5 grid h-4.5 w-4.5 shrink-0 place-items-center rounded-[5px] border transition-colors',
                      on ? 'border-accent bg-accent text-white' : 'border-line',
                    )}
                    style={{ width: 18, height: 18 }}
                  >
                    {on && <Check size={12} />}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[13.5px] font-medium text-ink">{m.friendly}</span>
                      <span className="rounded-[3px] bg-surface-active px-1.5 py-0.5 text-[10px] uppercase text-faint">
                        {m.catLabel}
                      </span>
                      <span className="font-mono text-[11px] text-faint">{m.tech}</span>
                    </div>
                    <p className="mt-1 text-[12px] text-dim">{m.question}</p>
                    {showExplain && <p className="mt-0.5 text-[11.5px] leading-relaxed text-faint">{m.plain}</p>}
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* sticky selection summary + primary CTA */}
      <ActionBar
        status={
          selected.length > 0 ? (
            <span className="flex flex-wrap items-center gap-1.5">
              <span className="text-dim">Selected:</span>
              {selected.map((id) => (
                <span
                  key={id}
                  className="rounded-[4px] border border-subtle bg-workspace px-1.5 py-0.5 font-mono text-[11px] text-ink"
                >
                  {STRAT_META[id].abbr}
                </span>
              ))}
              <span className="ml-1 text-faint">
                {selected.length} {selected.length === 1 ? 'method' : 'methods'} selected
              </span>
            </span>
          ) : (
            'Select at least one method to continue.'
          )
        }
        primary={{
          label: 'Continue to Configure',
          onClick: onContinue,
          disabled: selected.length === 0,
        }}
      />
    </>
  )
}

// ===========================================================================
// STEP 2 — CONFIGURE
// ===========================================================================

function StepConfigure({
  selected,
  active,
  setActive,
  paramsFor,
  onChange,
  invalidById,
  configuredCount,
  allConfigured,
  showExplain,
  market,
  timeframe,
  onBack,
  onContinue,
}: {
  selected: string[]
  active: string | null
  setActive: (id: string) => void
  paramsFor: (id: string) => Record<string, number>
  onChange: (id: string, v: Record<string, number>) => void
  invalidById: Record<string, string | null>
  configuredCount: number
  allConfigured: boolean
  showExplain: boolean
  market: { display: string }
  timeframe: string
  onBack: () => void
  onContinue: () => void
}) {
  const { byId: stratById, recommendedValues } = useStrategyCatalog()
  const activeId = active ?? selected[0]
  const strat = activeId ? stratById(activeId) : null
  const m = activeId ? STRAT_META[activeId] : null
  const values = activeId ? paramsFor(activeId) : {}
  const activeError = activeId ? invalidById[activeId] : null

  return (
    <>
      <div className="flex min-h-0 flex-1">
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
          <div className="mx-auto max-w-3xl">
            <h2 className="text-[16px] font-semibold text-ink">Configure your methods</h2>
            {showExplain && (
              <p className="mt-1 text-[12.5px] text-dim">
                Recommended values are already filled in. You can keep them or customize them.
              </p>
            )}

            <div className="mt-4 grid gap-4 md:grid-cols-[200px_1fr]">
              {/* method list */}
              <div className="space-y-1.5">
                <div className="text-[10px] font-semibold uppercase tracking-wide text-faint">Selected methods</div>
                {selected.map((id) => {
                  const err = invalidById[id]
                  const on = id === activeId
                  return (
                    <button
                      key={id}
                      onClick={() => setActive(id)}
                      className={cn(
                        'flex w-full items-center gap-2 rounded-[7px] border px-2.5 py-2 text-left text-[12.5px] transition-colors',
                        on ? 'border-accent/50 bg-accent/10 text-ink' : 'border-subtle bg-workspace text-dim hover:bg-surface-hover',
                      )}
                    >
                      <span
                        className={cn(
                          'grid h-4 w-4 shrink-0 place-items-center rounded-full',
                          err ? 'bg-neg/20 text-neg' : 'bg-pos/20 text-pos',
                        )}
                      >
                        {err ? <TriangleAlert size={10} /> : <Check size={11} />}
                      </span>
                      <span className="truncate">{STRAT_META[id].friendly}</span>
                    </button>
                  )
                })}
              </div>

              {/* config panel */}
              {strat && m && (
                <div className="rounded-[10px] border border-subtle bg-workspace p-4">
                  <div className="flex items-baseline gap-2">
                    <h3 className="text-[14.5px] font-semibold text-ink">{m.friendly}</h3>
                    <span className="font-mono text-[11px] text-faint">{m.tech}</span>
                  </div>
                  {showExplain && <p className="mt-0.5 text-[12px] text-dim">{m.purpose}</p>}

                  <div className="mt-3.5 grid gap-3 sm:grid-cols-2">
                    {strat.params.map((p) => {
                      const v = values[p.key]
                      const bad = Number.isNaN(v) || v < p.min || v > p.max
                      return (
                        <div key={p.key}>
                          <div className="mb-1 flex items-baseline justify-between">
                            <label htmlFor={`${activeId}-${p.key}`} className="text-[12px] text-dim">{p.label}</label>
                            <span className="font-mono text-[10px] text-faint">
                              {p.min}–{p.max}
                            </span>
                          </div>
                          <input
                            id={`${activeId}-${p.key}`}
                            type="number"
                            aria-invalid={bad || Boolean(activeError)}
                            aria-describedby={activeError ? `${activeId}-error` : undefined}
                            value={Number.isNaN(v) ? '' : v}
                            min={p.min}
                            max={p.max}
                            step={p.step}
                            onChange={(e) => onChange(activeId!, { ...values, [p.key]: parseFloat(e.target.value) })}
                            className={cn(
                              'h-9 w-full rounded-[6px] border bg-surface px-2.5 font-mono text-[13px] tabular-nums text-ink outline-none',
                              bad ? 'border-neg' : 'border-subtle focus:border-accent',
                            )}
                          />
                        </div>
                      )
                    })}
                  </div>

                  <div className="mt-2 flex items-center gap-2">
                    <RecoBadge>Recommended</RecoBadge>
                    <button
                      onClick={() => onChange(activeId!, recommendedValues(activeId!))}
                      className="inline-flex items-center gap-1 text-[11.5px] font-medium text-accent hover:text-accent-hover"
                    >
                      <RotateCcw size={11} /> Reset to recommended
                    </button>
                  </div>

                  {activeError && (
                    <div id={`${activeId}-error`} className="mt-3 flex items-center gap-1.5 rounded-[6px] border border-neg/30 bg-neg/10 px-2.5 py-2 text-[12px] text-neg">
                      <TriangleAlert size={13} className="shrink-0" /> {activeError}
                    </div>
                  )}

                  {/* signal rules */}
                  <div className="mt-4 border-t border-subtle pt-3">
                    <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-faint">
                      Signal rules
                    </div>
                    <div className="space-y-1.5">
                      {strat.rules.map((r, i) => (
                        <div key={i} className="flex items-center gap-2 text-[12px]">
                          <span className="text-dim">{r.text}</span>
                          <span className="text-faint">→</span>
                          <SignalTag side={r.side} />
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <SummaryAside
          selected={selected}
          market={market}
          timeframe={timeframe}
          status={allConfigured ? 'All methods ready' : 'Configuring'}
        />
      </div>

      <ActionBar
        back={onBack}
        status={
          allConfigured
            ? `${selected.length} of ${selected.length} methods ready`
            : `${configuredCount} of ${selected.length} methods configured`
        }
        statusTone={allConfigured ? 'pos' : 'faint'}
        primary={{ label: 'Continue', onClick: onContinue, disabled: !allConfigured }}
      />
    </>
  )
}

// ===========================================================================
// STEP 3 — COMBINE
// ===========================================================================

function StepCombine({
  members,
  method,
  setMethod,
  weights,
  setWeights,
  weightValid,
  totalWeight,
  balanceWeights,
  tie,
  setTie,
  buyTh,
  setBuyTh,
  sellTh,
  setSellTh,
  advanced,
  setAdvanced,
  decision,
  showExplain,
  market,
  timeframe,
  onBack,
  onContinue,
}: {
  members: (StratMeta & { id: string })[]
  method: 'majority' | 'weighted'
  setMethod: (m: 'majority' | 'weighted') => void
  weights: Record<string, number>
  setWeights: React.Dispatch<React.SetStateAction<Record<string, number>>>
  weightValid: boolean
  totalWeight: number
  balanceWeights: () => void
  tie: Sig
  setTie: (s: Sig) => void
  buyTh: number
  setBuyTh: (n: number) => void
  sellTh: number
  setSellTh: (n: number) => void
  advanced: boolean
  setAdvanced: React.Dispatch<React.SetStateAction<boolean>>
  decision: Decision | null
  showExplain: boolean
  market: { display: string }
  timeframe: string
  onBack: () => void
  onContinue: () => void
}) {
  return (
    <>
      <div className="flex min-h-0 flex-1">
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
          <div className="mx-auto max-w-3xl">
            <h2 className="text-[16px] font-semibold text-ink">Combine strategy signals</h2>
            {showExplain && (
              <p className="mt-1 text-[12.5px] text-dim">
                You selected {members.length} analysis methods. Choose how their signals should work together.
              </p>
            )}

            {/* method choice */}
            <div className="mt-4 grid gap-2.5 sm:grid-cols-2">
              <button
                onClick={() => setMethod('majority')}
                className={cn(
                  'rounded-[10px] border p-3.5 text-left transition-colors',
                  method === 'majority' ? 'border-accent/50 bg-accent/10' : 'border-subtle bg-workspace hover:bg-surface-hover',
                )}
              >
                <div className="flex items-center gap-1.5">
                  <Vote size={15} className={method === 'majority' ? 'text-accent' : 'text-faint'} />
                  <span className="text-[13.5px] font-semibold text-ink">Majority Vote</span>
                  <RecoBadge>Recommended for beginners</RecoBadge>
                </div>
                {showExplain && (
                  <p className="mt-1.5 text-[11.5px] leading-relaxed text-faint">
                    Every strategy gets one vote. The most common signal becomes the final signal.
                  </p>
                )}
              </button>
              <button
                onClick={() => setMethod('weighted')}
                className={cn(
                  'rounded-[10px] border p-3.5 text-left transition-colors',
                  method === 'weighted' ? 'border-accent/50 bg-accent/10' : 'border-subtle bg-workspace hover:bg-surface-hover',
                )}
              >
                <div className="flex items-center gap-1.5">
                  <Scale size={15} className={method === 'weighted' ? 'text-accent' : 'text-faint'} />
                  <span className="text-[13.5px] font-semibold text-ink">Weighted</span>
                </div>
                {showExplain && (
                  <p className="mt-1.5 text-[11.5px] leading-relaxed text-faint">
                    Give some methods more influence over the final decision.
                  </p>
                )}
              </button>
            </div>

            {/* method settings */}
            <div className="mt-4 rounded-[10px] border border-subtle bg-workspace p-4">
              {method === 'majority' ? (
                <>
                  <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-faint">Tie behavior</div>
                  {showExplain && (
                    <p className="mb-2 text-[12px] text-dim">
                      What should happen when BUY and SELL receive the same number of votes?
                    </p>
                  )}
                  <Segmented
                    ariaLabel="Combination method"
                    options={[
                      { value: 'hold', label: 'HOLD' },
                      { value: 'buy', label: 'BUY' },
                      { value: 'sell', label: 'SELL' },
                    ]}
                    value={tie}
                    onChange={(v) => setTie(v as Sig)}
                  />
                </>
              ) : (
                <>
                  <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-faint">Influence</div>
                  <div className="space-y-2.5">
                    {members.map((m) => (
                      <div key={m.id}>
                        <div className="mb-1 flex items-baseline justify-between">
                          <span className="text-[12px] text-dim">{m.friendly}</span>
                          <span className="font-mono text-[12px] tabular-nums text-ink">{weights[m.id] ?? 0}%</span>
                        </div>
                        <input
                          type="range"
                          min={0}
                          max={100}
                          step={5}
                          value={weights[m.id] ?? 0}
                          onChange={(e) => setWeights((w) => ({ ...w, [m.id]: parseInt(e.target.value) }))}
                          className="w-full accent-[#4F7CFF]"
                        />
                      </div>
                    ))}
                  </div>
                  <div className="mt-3 flex items-center justify-between border-t border-subtle pt-2.5">
                    <span className={cn('text-[12px]', weightValid ? 'text-faint' : 'text-neg')}>
                      Total {totalWeight}%
                    </span>
                    {!weightValid && (
                      <button
                        onClick={balanceWeights}
                        className="text-[11.5px] font-medium text-accent hover:text-accent-hover"
                      >
                        Balance automatically
                      </button>
                    )}
                  </div>
                  {!weightValid && (
                    <p className="mt-1 text-[11.5px] text-neg">
                      Strategy influence currently totals {totalWeight}%. Adjust the weights to reach 100%.
                    </p>
                  )}

                  {/* advanced thresholds */}
                  <div className="mt-3 border-t border-subtle pt-3">
                    <button
                      onClick={() => setAdvanced((a) => !a)}
                      className="inline-flex items-center gap-1 text-[11.5px] font-medium text-dim hover:text-ink"
                    >
                      <ChevronDown size={12} className={cn('transition-transform', advanced && 'rotate-180')} />
                      Advanced combination settings
                    </button>
                    {advanced && (
                      <div className="mt-2.5">
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <label className="mb-1 block text-[12px] text-dim">BUY threshold</label>
                            <input
                              type="number"
                              step={0.05}
                              value={buyTh}
                              onChange={(e) => setBuyTh(parseFloat(e.target.value))}
                              className="h-8 w-full rounded-[5px] border border-subtle bg-surface px-2 font-mono text-[13px] tabular-nums text-ink outline-none focus:border-accent"
                            />
                          </div>
                          <div>
                            <label className="mb-1 block text-[12px] text-dim">SELL threshold</label>
                            <input
                              type="number"
                              step={0.05}
                              value={sellTh}
                              onChange={(e) => setSellTh(parseFloat(e.target.value))}
                              className="h-8 w-full rounded-[5px] border border-subtle bg-surface px-2 font-mono text-[13px] tabular-nums text-ink outline-none focus:border-accent"
                            />
                          </div>
                        </div>
                        {showExplain && (
                          <HelperText>
                            Scores above {fmtSigned(buyTh)} produce BUY. Scores below {fmtSigned(sellTh)} produce SELL.
                            Scores in between produce HOLD.
                          </HelperText>
                        )}
                        <button
                          onClick={() => {
                            setBuyTh(0.3)
                            setSellTh(-0.3)
                          }}
                          className="mt-1.5 text-[11.5px] font-medium text-accent hover:text-accent-hover"
                        >
                          Reset to recommended
                        </button>
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>

            {/* decision preview */}
            <div className="mt-4">
              <DecisionPreview
                members={members}
                weights={weights}
                method={method}
                decision={decision}
                tie={tie}
                buyTh={buyTh}
                showExplain={showExplain}
              />
            </div>
          </div>
        </div>

        <SummaryAside
          selected={members.map((m) => m.id)}
          market={market}
          timeframe={timeframe}
          status={method === 'weighted' && !weightValid ? 'Balance weights' : 'Combination ready'}
        />
      </div>

      <ActionBar
        back={onBack}
        status={method === 'weighted' && !weightValid ? undefined : 'Combination ready'}
        statusTone="pos"
        primary={{
          label: 'Review Strategy',
          onClick: onContinue,
          disabled: method === 'weighted' && !weightValid,
        }}
      />
    </>
  )
}

// ===========================================================================
// STEP 4 — REVIEW & TEST
// ===========================================================================

function StepReview({
  selected,
  single,
  method,
  weights,
  tie,
  buyTh,
  sellTh,
  paramsFor,
  decision,
  showExplain,
  market,
  timeframe,
  onEditMethods,
  onEditCombine,
  onBack,
  onRun,
  onSave,
}: {
  selected: string[]
  single: boolean
  method: 'majority' | 'weighted'
  weights: Record<string, number>
  tie: Sig
  buyTh: number
  sellTh: number
  paramsFor: (id: string) => Record<string, number>
  decision: Decision | null
  showExplain: boolean
  market: { display: string; name: string; quote: string }
  timeframe: string
  onEditMethods: () => void
  onEditCombine: () => void
  onBack: () => void
  onRun: () => void
  onSave: () => void
}) {
  const { byId: stratById } = useStrategyCatalog()
  return (
    <>
      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
        <div className="mx-auto max-w-2xl">
          <h2 className="text-[16px] font-semibold text-ink">Review your strategy</h2>
          {showExplain && (
            <p className="mt-1 text-[12.5px] text-dim">
              Everything looks ready. Check the setup before running a historical simulation.
            </p>
          )}

          {/* market */}
          <ReviewCard title="Market">
            <div className="font-mono text-[13px] text-ink">{market.display}</div>
            <div className="text-[11.5px] text-faint">
              {market.name} priced in {market.quote} · {timeframe}
            </div>
          </ReviewCard>

          {/* methods */}
          <ReviewCard title="Analysis methods" onEdit={onEditMethods}>
            <div className="space-y-2">
              {selected.map((id) => (
                <div key={id} className="flex items-baseline justify-between">
                  <span className="text-[12.5px] text-dim">{STRAT_META[id].friendly}</span>
                  <span className="font-mono text-[12px] tabular-nums text-ink">
                    {stratById(id)
                      .params.map((p) => paramsFor(id)[p.key])
                      .join(' / ')}
                  </span>
                </div>
              ))}
            </div>
          </ReviewCard>

          {/* combination */}
          {!single && (
            <ReviewCard title="Combination" onEdit={onEditCombine}>
              {method === 'majority' ? (
                <div className="text-[12.5px] text-dim">
                  Majority Vote
                  <span className="ml-2 text-faint">Tie → {tie.toUpperCase()}</span>
                </div>
              ) : (
                <div className="space-y-1">
                  {selected.map((id) => (
                    <div key={id} className="flex items-baseline justify-between text-[12.5px]">
                      <span className="text-dim">{STRAT_META[id].friendly}</span>
                      <span className="font-mono tabular-nums text-ink">{weights[id] ?? 0}%</span>
                    </div>
                  ))}
                  <div className="pt-1 text-[11.5px] text-faint">
                    BUY ≥ {fmtSigned(buyTh)} · SELL ≤ {fmtSigned(sellTh)}
                  </div>
                </div>
              )}
            </ReviewCard>
          )}

          {/* current final signal */}
          {decision && (
            <div className="mt-3 flex items-center justify-between rounded-[10px] border border-line bg-workspace px-4 py-3">
              <span className="text-[12px] text-faint">Current signal on live data</span>
              <SignalTag side={decision.side} />
            </div>
          )}

          {/* what will happen */}
          <div className="mt-4 rounded-[10px] border border-info/25 bg-info/5 p-4">
            <div className="mb-1.5 flex items-center gap-1.5 text-[12.5px] font-semibold text-info">
              <Info size={14} /> What will happen?
            </div>
            <p className="text-[12.5px] leading-relaxed text-dim">
              Crypto Strategy Lab will apply this strategy to historical {market.display} {timeframe} market data and
              simulate its BUY, SELL and HOLD decisions.{' '}
              <span className="font-medium text-ink">No real trades will be placed.</span>
            </p>
          </div>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-3 border-t border-line bg-surface px-5 py-3">
        <button
          onClick={onBack}
          className="inline-flex items-center gap-1.5 rounded-[6px] border border-subtle bg-workspace px-3 py-1.5 text-[12.5px] text-dim hover:bg-surface-hover hover:text-ink"
        >
          <ArrowLeft size={14} /> Back
        </button>
        <div className="ml-auto flex items-center gap-2.5">
          <Button variant="default" onClick={onSave}>
            Save Strategy
          </Button>
          <Button variant="primary" onClick={onRun}>
            Run Backtest
          </Button>
        </div>
      </div>
    </>
  )
}

function ReviewCard({
  title,
  onEdit,
  children,
}: {
  title: string
  onEdit?: () => void
  children: React.ReactNode
}) {
  return (
    <div className="mt-3 rounded-[10px] border border-subtle bg-surface p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-wide text-faint">{title}</span>
        {onEdit && (
          <button onClick={onEdit} className="text-[11.5px] font-medium text-accent hover:text-accent-hover">
            Edit
          </button>
        )}
      </div>
      {children}
    </div>
  )
}

// ===========================================================================
// Decision preview
// ===========================================================================

type Decision =
  | { side: Sig; kind: 'single' }
  | { side: Sig; kind: 'weighted'; score: number }
  | { side: Sig; kind: 'majority'; buys: number; sells: number; tied: boolean }

function DecisionPreview({
  members,
  weights,
  method,
  decision,
  tie,
  buyTh,
  showExplain,
}: {
  members: (StratMeta & { id: string })[]
  weights: Record<string, number>
  method: 'majority' | 'weighted'
  decision: Decision | null
  tie: Sig
  buyTh: number
  showExplain: boolean
}) {
  if (!decision) return null

  const reason =
    decision.kind === 'single'
      ? `${members[0].friendly} currently signals ${decision.side.toUpperCase()}.`
      : decision.kind === 'weighted'
        ? `The weighted score ${fmtSigned(decision.score)} is ${
            decision.side === 'buy'
              ? `above the BUY threshold ${fmtSigned(buyTh)}`
              : decision.side === 'sell'
                ? `below the SELL threshold ${fmtSigned(-buyTh)}`
                : 'between the thresholds'
          }, so the final signal is ${decision.side.toUpperCase()}.`
        : decision.tied
          ? `The vote is tied, so the tie-break rule applies and the signal is ${tie.toUpperCase()}.`
          : `${Math.max(decision.buys, decision.sells)} of ${members.length} methods currently agree on ${decision.side.toUpperCase()}.`

  return (
    <div className="rounded-[10px] border border-line bg-workspace p-4">
      <div className="mb-2.5 text-[11px] font-semibold uppercase tracking-wide text-faint">Decision preview</div>

      <div className="space-y-1.5">
        {members.map((m) => (
          <div key={m.id} className="flex items-center justify-between">
            <span className="font-mono text-[12px] text-dim">
              {m.friendly}
              {method === 'weighted' && <span className="text-faint"> · {weights[m.id] ?? 0}%</span>}
            </span>
            <SignalTag side={m.signal} />
          </div>
        ))}
      </div>

      {decision.kind !== 'single' && (
        <div className="mt-3 border-t border-subtle pt-3">
          <div className="mb-1 text-[11px] text-faint">Combination · {method === 'majority' ? 'Majority Vote' : 'Weighted'}</div>
          {decision.kind === 'majority' ? (
            <div className="font-mono text-[12.5px] text-ink">
              BUY {decision.buys} · SELL {decision.sells}
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <span className="text-[12px] text-dim">Weighted score</span>
              <span className="font-mono text-[14px] font-semibold tabular-nums text-ml">
                {fmtSigned(decision.score)}
              </span>
            </div>
          )}
        </div>
      )}

      <div className="mt-3 border-t border-subtle pt-3">
        <div className="mb-1.5 text-[11px] text-faint">Final signal</div>
        <SignalTag side={decision.side} />
        {showExplain && <p className="mt-1.5 text-[11.5px] leading-relaxed text-dim">{reason}</p>}
      </div>
    </div>
  )
}
