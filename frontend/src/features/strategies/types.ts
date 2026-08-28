export type GenerationSourceType = 'STRATEGY_NAME' | 'NATURAL_LANGUAGE' | 'WEBPAGE_URL'

export interface GeneratedDraftSummary {
  id: string
  candidateIndex: number
  normalizedName: string
  displayName: string
  status: string
  draftFingerprint: string
}

export interface GenerationRequest {
  id: string
  sourceType: GenerationSourceType
  status: string
  requestedAt: string
  failure: { code: string; message: string } | null
  drafts: GeneratedDraftSummary[]
}

export interface GeneratedDraft extends GeneratedDraftSummary {
  description: string
  structuredRules: Record<string, unknown>
  parameterDefinition: Array<Record<string, unknown>>
  assumptions: string[]
  evidence: Array<{
    rulePath: string
    evidenceType: 'SOURCE' | 'ASSUMPTION'
    sourceLocator: string | null
    summary: string
  }>
  sourceProvenance: {
    sourceType: GenerationSourceType
    submittedUrl: string | null
    canonicalUrl: string | null
    title: string | null
    attribution: string | null
    contentFingerprint: string
    accessPolicyVersion: string
    retrievedAt: string | null
  }
  validationReport: null | {
    id: string
    artifactFingerprint: string
    policyVersion: string
    status: string
    checks: Array<{ name: string; status: string; findings: unknown[] }>
  }
  failureIssues: Array<{ field: string; code: string; message: string }>
}

export interface ActivatedStrategy {
  strategyId: string
  strategyVersion: string
  provenanceId: string
}
