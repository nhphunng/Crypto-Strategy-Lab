import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { StoreProvider } from '../../lib/store'
import { ServiceProvider } from '../../services/registry'
import { Strategies } from '../../screens/Strategies'
import type { ActivatedStrategy, GeneratedDraft } from '../../features/strategies/types'

vi.mock('../../features/strategies/components/StrategyGenerationForm', () => ({
  StrategyGenerationForm: ({ onDrafts }: { onDrafts: (drafts: GeneratedDraft[]) => void }) => (
    <button onClick={() => onDrafts([{ id: 'draft-1', displayName: 'Breakout' } as GeneratedDraft])}>
      Create draft fixture
    </button>
  ),
}))

vi.mock('../../features/strategies/components/GeneratedStrategyReview', () => ({
  GeneratedStrategyReview: ({
    onActivated,
  }: {
    onActivated: (strategy: ActivatedStrategy) => void | Promise<void>
  }) => (
    <button onClick={() => void onActivated({ strategyId: 'breakout', strategyVersion: '1.0.0', provenanceId: 'p-1' })}>
      Activate fixture
    </button>
  ),
}))

const builtIn = metadata('ma', 'Moving Average', 'BUILT_IN')
const generated = metadata('breakout', 'Breakout', 'LLM_GENERATED')

afterEach(() => vi.unstubAllGlobals())

describe('strategy catalog reuse workflow', () => {
  it('refreshes, selects, and configures an activated generated strategy, then rediscovers it after remount', async () => {
    const user = userEvent.setup()
    let discoveryCount = 0
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes('/api/v1/strategy-configurations')) {
          return Promise.resolve(listResponse([]))
        }
        discoveryCount += 1
        return Promise.resolve(response(discoveryCount === 1 ? [builtIn] : [builtIn, generated]))
      }),
    )

    const first = renderScreen()
    expect((await screen.findAllByText('Moving Average')).length).toBeGreaterThan(0)
    await user.click(screen.getByRole('button', { name: 'Generate Strategy' }))
    await user.click(screen.getByRole('button', { name: 'Create draft fixture' }))
    await user.click(screen.getByRole('button', { name: 'Activate fixture' }))

    expect(await screen.findByRole('heading', { name: 'Set the parameters' })).toBeVisible()
    expect(screen.getAllByText('Breakout').length).toBeGreaterThan(0)
    expect(discoveryCount).toBeGreaterThanOrEqual(2)

    first.unmount()
    renderScreen()
    expect(await screen.findByText('How does Breakout interpret this market?')).toBeVisible()
    expect(screen.getByText('Generated')).toBeVisible()
  })

  it('shows discovery failure and retries through the backend boundary', async () => {
    const user = userEvent.setup()
    let catalogCalls = 0
    const fetchMock = vi
      .fn()
      .mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes('/api/v1/strategy-configurations')) {
          return Promise.resolve(listResponse([]))
        }
        catalogCalls += 1
        if (catalogCalls === 1) {
          return Promise.resolve(
            new Response(JSON.stringify({ message: 'Catalog unavailable' }), { status: 503 }),
          )
        }
        return Promise.resolve(response([builtIn]))
      })
    vi.stubGlobal('fetch', fetchMock)
    renderScreen()

    expect(await screen.findByText('Catalog unavailable')).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Retry' }))
    expect((await screen.findAllByText('Moving Average')).length).toBeGreaterThan(0)
    await waitFor(() => expect(catalogCalls).toBe(2))
  })
})

function renderScreen() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ServiceProvider>
          <StoreProvider>
            <Strategies />
          </StoreProvider>
        </ServiceProvider>
      </BrowserRouter>
    </QueryClientProvider>,
  )
}

function metadata(strategyId: string, displayName: string, origin: 'BUILT_IN' | 'LLM_GENERATED') {
  return {
    strategyId,
    strategyType: strategyId === 'ma' ? 'MA' : 'BREAKOUT',
    displayName,
    strategyVersion: '1.0.0',
    contractVersion: '1.0.0',
    status: 'AVAILABLE',
    capabilities: ['REASON'],
    origin,
    generationProvenanceId: origin === 'LLM_GENERATED' ? 'p-1' : null,
    generatedArtifactFingerprint: origin === 'LLM_GENERATED' ? 'artifact-1' : null,
    parameters: [
      {
        name: 'period',
        description: 'Lookback period',
        valueType: 'INTEGER',
        defaultValue: 20,
        minimum: 2,
        maximum: 500,
        required: true,
      },
    ],
  }
}

function response(strategies: ReturnType<typeof metadata>[]) {
  return new Response(
    JSON.stringify({
      success: true,
      message: 'Strategies loaded.',
      data: { strategies },
      timestamp: '2026-08-23T00:00:00Z',
      requestId: 'request-1',
    }),
  )
}

function listResponse(configurations: unknown[]) {
  return new Response(
    JSON.stringify({
      success: true,
      message: 'Configurations loaded.',
      data: { configurations },
      timestamp: '2026-08-23T00:00:00Z',
      requestId: 'request-1',
    }),
  )
}
