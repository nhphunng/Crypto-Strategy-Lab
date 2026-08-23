import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
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
}

describe('generated strategy review', () => {
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
})
