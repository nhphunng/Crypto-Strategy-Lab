import { useState } from 'react'
import { Button } from '../../../components/ui'
import { generateStrategies, getGeneratedDraft, getGenerationRequest } from '../../../services/strategyGeneration'
import type { GeneratedDraft, GenerationSourceType } from '../types'

export function StrategyGenerationForm({ onDrafts }: { onDrafts: (drafts: GeneratedDraft[]) => void }) {
  const [sourceType, setSourceType] = useState<GenerationSourceType>('STRATEGY_NAME')
  const [value, setValue] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit() {
    setBusy(true)
    setError(null)
    try {
      const request = await generateStrategies(sourceType, value.trim())
      let completed = request
      for (let attempt = 0; attempt < 60 && !['COMPLETED', 'FAILED'].includes(completed.status); attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 1000))
        completed = await getGenerationRequest(request.id)
      }
      if (completed.status === 'FAILED') {
        throw new Error(completed.failure?.message ?? 'Generation failed; no strategy was activated')
      }
      if (completed.status !== 'COMPLETED') throw new Error('Generation is still running; reopen the request later')
      onDrafts(await Promise.all(completed.drafts.map((draft) => getGeneratedDraft(draft.id))))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Strategy generation failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="border-b border-subtle bg-surface px-5 py-4" aria-label="Generate reusable strategy">
      <div className="flex flex-wrap items-center gap-2">
        {(['STRATEGY_NAME', 'NATURAL_LANGUAGE', 'WEBPAGE_URL'] as const).map((type) => (
          <button
            key={type}
            onClick={() => setSourceType(type)}
            className={`rounded-[6px] border px-3 py-1.5 text-[12px] ${sourceType === type ? 'border-accent bg-accent/10 text-accent' : 'border-subtle text-dim'}`}
          >
            {type === 'STRATEGY_NAME' ? 'Existing name' : type === 'NATURAL_LANGUAGE' ? 'Description' : 'Webpage URL'}
          </button>
        ))}
      </div>
      <div className="mt-3 flex gap-2">
        {sourceType === 'NATURAL_LANGUAGE' ? (
          <textarea
            aria-label="Strategy description"
            value={value}
            onChange={(event) => setValue(event.target.value)}
            placeholder="Describe entry, exit, HOLD, timing, data and parameters…"
            className="min-h-24 flex-1 rounded-[6px] border border-subtle bg-workspace p-3 text-[13px] text-ink"
          />
        ) : (
          <input
            aria-label={sourceType === 'STRATEGY_NAME' ? 'Existing strategy name' : 'Strategy webpage URL'}
            value={value}
            onChange={(event) => setValue(event.target.value)}
            placeholder={sourceType === 'STRATEGY_NAME' ? 'e.g. Donchian breakout' : 'https://example.com/strategy'}
            className="h-9 flex-1 rounded-[6px] border border-subtle bg-workspace px-3 text-[13px] text-ink"
          />
        )}
        <Button variant="primary" disabled={busy || !value.trim()} onClick={submit}>
          {busy ? 'Generating & validating…' : 'Generate drafts'}
        </Button>
      </div>
      <p className="mt-2 text-[11px] text-faint">
        Analysis only. Each draft is checked for safety before it can be activated.
      </p>
      {error && <p className="mt-2 text-[12px] text-neg">{error}</p>}
    </section>
  )
}
