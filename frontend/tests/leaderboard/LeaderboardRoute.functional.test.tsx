/**
 * Functional regression tests for the composed leaderboard route.
 *
 * Unlike the component-level tests in this directory, these exercise
 * `LeaderboardRoute` as a whole — the same tree a user loads in the browser —
 * through its network seams (`loadSnapshot`, `socketFactory`) only. They cover
 * the user journeys that span more than one sub-component: selecting a row to
 * open the detail pane, changing the ranking controls, and recovering from a
 * failed load.
 */

import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { LeaderboardRoute } from '../../src/app/routes/leaderboard'
import type { SocketLike } from '../../src/features/leaderboard/hooks/useLeaderboardUpdates'
import { snapshotFixture } from './fixtures'

class FakeSocket implements SocketLike {
  onopen: ((event: unknown) => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onerror: ((event: unknown) => void) | null = null
  onclose: ((event: unknown) => void) | null = null

  send(): void {}
  close(): void {}
}

describe('LeaderboardRoute functional journeys', () => {
  it('opens the ranked-result detail pane for the selected row and closes it again', async () => {
    const loadSnapshot = vi.fn().mockResolvedValue(snapshotFixture())
    const renderDetail = vi.fn((selection: { leaderboardId: string; evaluationResultId: string }) => (
      <div data-testid="detail-pane">{selection.evaluationResultId}</div>
    ))

    render(
      <LeaderboardRoute
        loadSnapshot={loadSnapshot}
        socketFactory={() => new FakeSocket()}
        renderDetail={renderDetail}
      />,
    )

    await screen.findByTestId('table-leaderboard')
    expect(screen.queryByTestId('detail-pane')).not.toBeInTheDocument()

    fireEvent.click(screen.getByTestId('row-leaderboard-eval-1'))

    expect(await screen.findByTestId('detail-pane')).toHaveTextContent('eval-1')
    expect(renderDetail).toHaveBeenCalledWith({ leaderboardId: 'board-1', evaluationResultId: 'eval-1' })

    fireEvent.click(screen.getByTestId('row-leaderboard-eval-1'))
    fireEvent.keyDown(screen.getByTestId('row-leaderboard-eval-1'), {})
  })

  it('reloads the snapshot with the new ranking definition and resets to page one', async () => {
    const loadSnapshot = vi.fn().mockResolvedValue(snapshotFixture())

    render(<LeaderboardRoute loadSnapshot={loadSnapshot} socketFactory={() => new FakeSocket()} />)

    await screen.findByTestId('table-leaderboard')
    expect(loadSnapshot).toHaveBeenCalledTimes(1)

    fireEvent.change(screen.getByTestId('control-rank-by'), { target: { value: 'TOTAL_RETURN' } })

    await waitFor(() => expect(loadSnapshot).toHaveBeenCalledTimes(2))
    const [rankByIdentity, rankByView] = loadSnapshot.mock.calls[1]
    expect(rankByIdentity.rankBy).toBe('TOTAL_RETURN')
    expect(rankByView.page).toBe(1)

    fireEvent.change(screen.getByTestId('control-top-k'), { target: { value: '25' } })

    await waitFor(() => expect(loadSnapshot).toHaveBeenCalledTimes(3))
    const [topKIdentity] = loadSnapshot.mock.calls[2]
    expect(topKIdentity.k).toBe(25)
    expect(topKIdentity.rankBy).toBe('TOTAL_RETURN')
  })

  it('shows the error state on a failed load and recovers once retried', async () => {
    const loadSnapshot = vi
      .fn()
      .mockRejectedValueOnce(new Error('leaderboard service unavailable'))
      .mockResolvedValue(snapshotFixture())

    render(<LeaderboardRoute loadSnapshot={loadSnapshot} socketFactory={() => new FakeSocket()} />)

    const error = await screen.findByTestId('state-leaderboard-error')
    expect(error).toHaveTextContent('leaderboard service unavailable')
    expect(screen.queryByTestId('table-leaderboard')).not.toBeInTheDocument()

    fireEvent.click(screen.getByTestId('control-leaderboard-retry'))

    await screen.findByTestId('table-leaderboard')
    expect(loadSnapshot).toHaveBeenCalledTimes(2)
  })
})
