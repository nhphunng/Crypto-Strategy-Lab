import { useState } from 'react'
import { Button } from '../../../components/ui'
import { activateGeneratedDraft } from '../../../services/strategyGeneration'
import type { ActivatedStrategy, GeneratedDraft } from '../types'

export function GeneratedStrategyReview({
  draft,
  onActivated,
}: {
  draft: GeneratedDraft
  onActivated: (strategy: ActivatedStrategy) => void | Promise<void>
}) {
  const [confirmed, setConfirmed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const report = draft.validationReport

  async function activate() {
    setBusy(true)
    setError(null)
    try {
      const result = await activateGeneratedDraft(draft)
      await onActivated(result)
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
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 font-mono">
          <span>Draft <code className="text-ink">{draft.draftFingerprint}</code></span>
          <span>Source <code className="text-ink">{draft.sourceProvenance.contentFingerprint}</code></span>
        </div>
        <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 font-mono">
          <span>Policy <code className="text-ink">{report?.policyVersion ?? 'pending'}</code></span>
          <span>Artifact <code className="text-ink">{report?.artifactFingerprint ?? 'not available'}</code></span>
        </div>
        {report?.checks && report.checks.length > 0 && (
          <div className="mt-1.5 font-mono">
            Checks: {report.checks.map((check) => `${check.name}: ${check.status}`).join(' · ')}
          </div>
        )}
      </div>
      {(draft.failureIssues.length > 0 || report?.checks.some((check) => check.findings.length > 0)) && (
        <ReviewBlock
          title="Validation findings"
          value={{ failureIssues: draft.failureIssues, checks: report?.checks ?? [] }}
        />
      )}
      <label className="mt-3 flex items-start gap-2 text-[12px] text-dim">
        <input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />
        I reviewed the rules, evidence, assumptions and passing validation report above.
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
