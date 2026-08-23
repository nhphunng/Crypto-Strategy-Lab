import type {
  GeneratedDraft,
  GenerationRequest,
  GenerationSourceType,
} from '../features/strategies/types'

interface Envelope<T> {
  success: boolean
  message: string
  data: T
  requestId: string
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  const body = (await response.json()) as Envelope<T> & { error?: { code?: string } }
  if (!response.ok) throw new Error(body.message || body.error?.code || 'Strategy generation failed')
  return body.data
}

export async function generateStrategies(sourceType: GenerationSourceType, value: string) {
  const field =
    sourceType === 'STRATEGY_NAME'
      ? 'strategyName'
      : sourceType === 'WEBPAGE_URL'
        ? 'webpageUrl'
        : 'content'
  return api<GenerationRequest>('/strategy-generation-requests', {
    method: 'POST',
    body: JSON.stringify({ sourceType, [field]: value }),
  })
}

export function getGeneratedDraft(id: string) {
  return api<GeneratedDraft>(`/strategy-generation-drafts/${id}`)
}

export function getGenerationRequest(id: string) {
  return api<GenerationRequest>(`/strategy-generation-requests/${id}`)
}

export function activateGeneratedDraft(draft: GeneratedDraft) {
  if (!draft.validationReport) throw new Error('A passing validation report is required')
  return api<{ strategyId: string; strategyVersion: string; provenanceId: string }>(
    `/strategy-generation-drafts/${draft.id}/activate`,
    {
      method: 'POST',
      body: JSON.stringify({
        draftFingerprint: draft.draftFingerprint,
        artifactFingerprint: draft.validationReport.artifactFingerprint,
        validationReportId: draft.validationReport.id,
        confirmed: true,
      }),
    },
  )
}
