import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { GeneratedStrategyReview } from '../../features/strategies/components/GeneratedStrategyReview'
import type { GeneratedDraft } from '../../features/strategies/types'

const draft: GeneratedDraft = {
  id: '00000000-0000-0000-0000-000000000001',
  candidateIndex: 0,
  normalizedName: 'breakout',
  displayName: 'Breakout',
  status: 'READY_FOR_CONFIRMATION',
  draftFingerprint: 'draft-fingerprint',
  description: 'Strict prior-high breakout.',
  structuredRules: { entry: 'close > prior high' },
  parameterDefinition: [],
  assumptions: ['Closed candles only'],
  evidence: [{ rulePath: 'entry', evidenceType: 'SOURCE', sourceLocator: 'paragraph 1', summary: 'Buy above high' }],
  sourceProvenance: {
    sourceType: 'NATURAL_LANGUAGE',
    submittedUrl: null,
    canonicalUrl: null,
    title: null,
    attribution: null,
    contentFingerprint: 'source-fingerprint',
    accessPolicyVersion: 'source-access-v1',
    retrievedAt: null,
  },
  validationReport: {
    id: '00000000-0000-0000-0000-000000000002',
    artifactFingerprint: 'artifact-fingerprint',
    policyVersion: 'generated-strategy-validation-v1',
    status: 'PASSED',
    checks: [{ name: 'CONTRACT', status: 'PASSED', findings: [] }],
  },
  failureIssues: [],
}

describe('generated strategy review', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows exact evidence and requires explicit confirmation before activation', async () => {
    const user = userEvent.setup()
    render(<GeneratedStrategyReview draft={draft} onActivated={vi.fn()} />)
    expect(screen.getByText(/draft-fingerprint/)).toBeVisible()
    expect(screen.getByText(/source-fingerprint/)).toBeVisible()
    expect(screen.getByText(/artifact-fingerprint/)).toBeVisible()
    const activate = screen.getByRole('button', { name: 'Activate reusable version' })
    expect(activate).toBeDisabled()
    await user.click(screen.getByRole('checkbox'))
    expect(activate).toBeEnabled()
  })

  it('passes the canonical activated identity to the catalog refresh callback', async () => {
    const user = userEvent.setup()
    const onActivated = vi.fn()
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            success: true,
            message: 'Activated.',
            data: { strategyId: 'breakout', strategyVersion: '1.0.0', provenanceId: 'provenance-1' },
            requestId: 'request-1',
          }),
        ),
      ),
    )
    render(<GeneratedStrategyReview draft={draft} onActivated={onActivated} />)
    await user.click(screen.getByRole('checkbox'))
    await user.click(screen.getByRole('button', { name: 'Activate reusable version' }))
    await waitFor(() =>
      expect(onActivated).toHaveBeenCalledWith({
        strategyId: 'breakout',
        strategyVersion: '1.0.0',
        provenanceId: 'provenance-1',
      }),
    )
  })

  it('shows structured draft and validation failures', () => {
    render(
      <GeneratedStrategyReview
        draft={{
          ...draft,
          status: 'VALIDATION_FAILED',
          failureIssues: [{ field: 'rules.exit', code: 'MISSING_RULE', message: 'Exit rule is required' }],
          validationReport: {
            ...draft.validationReport!,
            status: 'FAILED',
            checks: [{ name: 'CONTRACT', status: 'FAILED', findings: [{ message: 'Contract mismatch' }] }],
          },
        }}
        onActivated={vi.fn()}
      />,
    )
    expect(screen.getByText('Validation findings')).toBeVisible()
    expect(screen.getByText(/Exit rule is required/)).toBeVisible()
    expect(screen.getByRole('button', { name: 'Activate reusable version' })).toBeDisabled()
  })
})
