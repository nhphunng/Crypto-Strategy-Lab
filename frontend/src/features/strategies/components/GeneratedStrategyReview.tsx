import { useState } from 'react'
import { Button } from '../../../components/ui'
import { activateGeneratedDraft } from '../../../services/strategyGeneration'
import type { GeneratedDraft } from '../types'

export function GeneratedStrategyReview({ draft, onActivated }: { draft: GeneratedDraft; onActivated: (label: string) => void }) {
  const [confirmed, setConfirmed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const report = draft.validationReport

  async function activate() {
    setBusy(true)
    setError(null)
    try {
      const result = await activateGeneratedDraft(draft)
      onActivated(`${result.strategyId}@${result.strategyVersion}`)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Activation failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <article className="border-b border-subtle bg-workspace px-5 py-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-[14px] font-semibold text-ink">{draft.displayName}</h3>
          <p className="mt-1 text-[12px] text-dim">{draft.description}</p>
        </div>
        <span className="rounded bg-surface-active px-2 py-1 font-mono text-[10px] text-dim">{draft.status}</span>
      </div>
      <div className="mt-3 grid gap-3 lg:grid-cols-3">
        <ReviewBlock title="Exact structured rules" value={draft.structuredRules} />
        <ReviewBlock title="Evidence" value={draft.evidence} />
        <ReviewBlock title="Assumptions" value={draft.assumptions} />
      </div>
      <div className="mt-3 rounded border border-subtle bg-surface p-3 text-[11px] text-dim">
        <div>Draft fingerprint: <code>{draft.draftFingerprint}</code></div>
        <div>Source fingerprint: <code>{draft.sourceProvenance.contentFingerprint}</code></div>
        <div>Validation policy: <code>{report?.policyVersion ?? 'not validated'}</code></div>
        <div>Artifact fingerprint: <code>{report?.artifactFingerprint ?? 'not available'}</code></div>
        <div className="mt-2">Checks: {report?.checks.map((check) => `${check.name}: ${check.status}`).join(' · ') ?? 'none'}</div>
      </div>
      <label className="mt-3 flex items-start gap-2 text-[12px] text-dim">
        <input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />
        I reviewed these exact rules, evidence, assumptions, fingerprints and the passing validation report.
      </label>
      <div className="mt-3 flex items-center gap-3">
        <Button variant="primary" disabled={!confirmed || report?.status !== 'PASSED' || busy} onClick={activate}>
          {busy ? 'Activating…' : 'Activate reusable version'}
        </Button>
        {error && <span className="text-[12px] text-neg">{error}</span>}
      </div>
    </article>
  )
}

function ReviewBlock({ title, value }: { title: string; value: unknown }) {
  return (
    <div className="rounded border border-subtle bg-surface p-3">
      <div className="text-[10px] font-semibold uppercase tracking-wide text-faint">{title}</div>
      <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap text-[11px] text-dim">{JSON.stringify(value, null, 2)}</pre>
    </div>
  )
}
