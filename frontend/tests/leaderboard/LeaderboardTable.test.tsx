import { describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { LeaderboardTable } from '../../src/features/leaderboard/components/LeaderboardTable'
import { LeaderboardRoute, ANALYSIS_DISCLAIMER } from '../../src/app/routes/leaderboard'
import { parseLeaderboardSnapshot, ContractError } from '../../src/features/leaderboard/schemas'
import type {
  LeaderboardSnapshot,
  LeaderboardViewState,
} from '../../src/features/leaderboard/types'
import { snapshotFixture } from './fixtures'

const VIEW: LeaderboardViewState = { sortBy: 'RANK', sortDirection: 'ASC', page: 1, pageSize: 25 }

function renderTable(overrides: Partial<Parameters<typeof LeaderboardTable>[0]> = {}) {
  const onViewChange = vi.fn()
  const props = {
    snapshot: snapshotFixture(),
    view: VIEW,
    status: 'ready' as const,
    onViewChange,
    ...overrides,
  }
  render(<LeaderboardTable {...props} />)
  return { onViewChange }
}

describe('LeaderboardTable', () => {
  it('renders every Top-K row with contiguous ranks and stable ids', () => {
    renderTable()

    const table = screen.getByTestId('table-leaderboard')
    const rows = within(table).getAllByRole('button', { name: /^Open rank/ })
    expect(rows).toHaveLength(3)
    expect(rows[0]).toHaveAttribute('data-testid', 'row-leaderboard-eval-1')
    expect(within(table).getByText('#1')).toBeInTheDocument()
    expect(within(table).getByText('#3')).toBeInTheDocument()
  })

  it('labels metric direction and unit for each ranked metric', () => {
    renderTable()

    expect(screen.getByTestId('control-sort-MAX_DRAWDOWN')).toHaveTextContent('lower is better')
    expect(screen.getByTestId('control-sort-TOTAL_RETURN')).toHaveTextContent('higher is better')
    expect(screen.getByTestId('control-sort-TOTAL_RETURN')).toHaveTextContent('percent')
    expect(screen.getByTestId('metric-direction-legend')).toHaveTextContent('MAX_DRAWDOWN')
  })

  it('requests a presentation sort without recomputing ranks locally', async () => {
    const { onViewChange } = renderTable()

    await userEvent.click(screen.getByTestId('control-sort-TOTAL_RETURN'))

    expect(onViewChange).toHaveBeenCalledWith(
      expect.objectContaining({ sortBy: 'TOTAL_RETURN', sortDirection: 'DESC', page: 1 }),
    )
  })

  it('uses the documented semantic direction first for drawdown', async () => {
    const { onViewChange } = renderTable()

    await userEvent.click(screen.getByTestId('control-sort-MAX_DRAWDOWN'))

    expect(onViewChange).toHaveBeenCalledWith(
      expect.objectContaining({ sortBy: 'MAX_DRAWDOWN', sortDirection: 'ASC' }),
    )
  })

  it('sends metric range filters to the backend query', async () => {
    const { onViewChange } = renderTable()

    await userEvent.type(screen.getByTestId('control-filter-min-score'), '8')

    expect(onViewChange).toHaveBeenCalledWith(expect.objectContaining({ minScore: '8', page: 1 }))
  })

  it('pages through the bounded result set', async () => {
    const snapshot = snapshotFixture()
    snapshot.pagination = { page: 1, pageSize: 2, total: 6 }
    const { onViewChange } = renderTable({ snapshot })

    await userEvent.click(screen.getByTestId('control-page-next'))

    expect(onViewChange).toHaveBeenCalledWith(expect.objectContaining({ page: 2 }))
    expect(screen.getByTestId('label-page')).toHaveTextContent('Page 1 of 3')
  })

  it('marks a no-trade result explicitly instead of showing a misleading value', () => {
    renderTable()

    expect(screen.getByTestId('state-no-trade-eval-3')).toHaveTextContent('No trades')
    expect(screen.getAllByText('n/a').length).toBeGreaterThan(0)
  })

  it('opens a row from the keyboard as well as the pointer', async () => {
    const onSelect = vi.fn()
    renderTable({ onSelect })

    const row = screen.getByTestId('row-leaderboard-eval-2')
    row.focus()
    await userEvent.keyboard('{Enter}')

    expect(onSelect).toHaveBeenCalledWith('eval-2')
  })

  it('shows explicit loading, empty, and error states', () => {
    const { unmount } = render(
      <LeaderboardTable snapshot={null} view={VIEW} status="loading" onViewChange={vi.fn()} />,
    )
    expect(screen.getByTestId('state-leaderboard-loading')).toBeInTheDocument()
    unmount()

    const empty = snapshotFixture()
    empty.entries = []
    empty.pagination = { page: 1, pageSize: 25, total: 0 }
    const second = render(
      <LeaderboardTable snapshot={empty} view={VIEW} status="ready" onViewChange={vi.fn()} />,
    )
    expect(screen.getByTestId('state-leaderboard-empty')).toBeInTheDocument()
    second.unmount()

    render(
      <LeaderboardTable
        snapshot={null}
        view={VIEW}
        status="error"
        errorMessage="dependency unavailable"
        onViewChange={vi.fn()}
      />,
    )
    expect(screen.getByTestId('state-leaderboard-error')).toHaveTextContent(
      'dependency unavailable',
    )
  })

  it('keeps the last snapshot visible while marked stale', () => {
    renderTable({ stale: true })

    expect(screen.getByTestId('state-leaderboard-stale')).toBeInTheDocument()
    expect(screen.getByTestId('table-leaderboard')).toBeInTheDocument()
  })
})

describe('LeaderboardRoute', () => {
  it('loads a snapshot and shows the non-investment-advice disclaimer', async () => {
    const loadSnapshot = vi.fn().mockResolvedValue(snapshotFixture())

    render(<LeaderboardRoute loadSnapshot={loadSnapshot} liveUpdates={false} />)

    expect(await screen.findByTestId('table-leaderboard')).toBeInTheDocument()
    const disclaimer = screen.getByTestId('disclaimer-leaderboard').textContent ?? ''
    expect(disclaimer.toLowerCase()).toContain('not investment advice')
    expect(disclaimer.toLowerCase()).not.toContain('guaranteed profit')
    expect(screen.getByTestId('label-simulated-analysis')).toHaveTextContent(
      'Simulated historical analysis',
    )
    expect(ANALYSIS_DISCLAIMER.toLowerCase()).toContain('simulated')
  })

  it('reloads a separate projection when K or the ranking metric changes', async () => {
    const loadSnapshot = vi.fn().mockResolvedValue(snapshotFixture())
    render(<LeaderboardRoute loadSnapshot={loadSnapshot} liveUpdates={false} />)
    await screen.findByTestId('table-leaderboard')

    await userEvent.selectOptions(screen.getByTestId('control-top-k'), '3')

    expect(loadSnapshot).toHaveBeenLastCalledWith(
      expect.objectContaining({ k: 3 }),
      expect.objectContaining({ page: 1 }),
    )
  })

  it('surfaces a failed load without inventing rows', async () => {
    const loadSnapshot = vi.fn().mockRejectedValue(new Error('LEADERBOARD_DEPENDENCY_UNAVAILABLE'))

    render(<LeaderboardRoute loadSnapshot={loadSnapshot} liveUpdates={false} />)

    expect(await screen.findByTestId('state-leaderboard-error')).toHaveTextContent(
      'LEADERBOARD_DEPENDENCY_UNAVAILABLE',
    )
    expect(screen.queryByTestId('table-leaderboard')).toBeNull()
  })
})

describe('runtime contract validation', () => {
  it('accepts a contract-shaped snapshot', () => {
    const parsed: LeaderboardSnapshot = parseLeaderboardSnapshot(snapshotFixture())

    expect(parsed.entries[0].score).toBe('92.5')
  })

  it('rejects a payload whose decimals arrive as numbers', () => {
    const broken = snapshotFixture() as unknown as Record<string, unknown>
    ;(broken.entries as { score: unknown }[])[0].score = 92.5

    expect(() => parseLeaderboardSnapshot(broken)).toThrow(ContractError)
  })

  it('rejects a projection that returns more rows than K', () => {
    const broken = snapshotFixture()
    broken.k = 2

    expect(() => parseLeaderboardSnapshot(broken)).toThrow(ContractError)
  })
})
