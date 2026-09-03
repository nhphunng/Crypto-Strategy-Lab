import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RankedResultDetail } from '../../src/features/leaderboard/components/RankedResultDetail'
import { parseVisualization } from '../../src/features/leaderboard/schemas'
import type { TradePage, VisualizationData } from '../../src/features/leaderboard/types'
import { detailFixture, tradePageFixture, visualizationFixture } from './fixtures'

function renderDetail(
  overrides: {
    visualization?: VisualizationData
    trades?: TradePage
    detail?: ReturnType<typeof detailFixture>
  } = {},
) {
  const loadDetail = vi.fn().mockResolvedValue(overrides.detail ?? detailFixture())
  const loadVisualization = vi
    .fn()
    .mockResolvedValue(overrides.visualization ?? visualizationFixture())
  const loadTrades = vi.fn().mockResolvedValue(overrides.trades ?? tradePageFixture())
  render(
    <RankedResultDetail
      leaderboardId="board-1"
      evaluationResultId="eval-1"
      loadDetail={loadDetail}
      loadVisualization={loadVisualization}
      loadTrades={loadTrades}
    />,
  )
  return { loadDetail, loadVisualization, loadTrades }
}

describe('RankedResultDetail', () => {
  it('shows the exact market, timeframe, range, and version context', async () => {
    renderDetail()

    const context = await screen.findByTestId('detail-context')
    expect(context).toHaveTextContent('BTCUSDT')
    expect(context).toHaveTextContent('15m')
    expect(context).toHaveTextContent('2026-07-01')
    expect(context).toHaveTextContent('strategy v3')
    expect(context).toHaveTextContent('policy balanced v2')
  })

  it('requests visualization for the ranked result range', async () => {
    const { loadVisualization } = renderDetail()

    await screen.findByTestId('detail-context')

    expect(loadVisualization).toHaveBeenCalledWith('board-1', 'eval-1', {
      startTime: '2026-07-01T00:00:00.000Z',
      endTime: '2026-07-03T00:00:00.000Z',
    })
  })

  it('renders Buy, Entry, and Exit markers with a label and a distinct shape', async () => {
    renderDetail()

    await screen.findByTestId('marker-layer')
    const buy = screen.getByTestId('marker-signal-1')
    const entry = screen.getByTestId('marker-trade-1-entry')
    const exit = screen.getByTestId('marker-trade-1-exit')

    expect(buy).toHaveAttribute('data-marker-type', 'BUY')
    expect(buy).toHaveAttribute('aria-label', 'BUY')
    expect(entry).toHaveAttribute('data-marker-shape', 'ENTRY_OUTLINED')
    expect(exit).toHaveAttribute('data-marker-shape', 'EXIT_OUTLINED')
    expect(entry.getAttribute('data-marker-shape')).not.toBe(exit.getAttribute('data-marker-shape'))
    expect(within(entry).getByText('ENTRY #1')).toBeInTheDocument()
  })

  it('hides HOLD markers until the explicit control is enabled', async () => {
    renderDetail()

    await screen.findByTestId('marker-layer')
    expect(screen.queryByTestId('marker-signal-hold')).toBeNull()

    await userEvent.click(screen.getByTestId('control-show-hold'))

    expect(screen.getByTestId('marker-signal-hold')).toHaveAttribute('data-marker-type', 'HOLD')
  })

  it('places a candle-close exit on its candle and keeps the recorded time in trade details', async () => {
    const visualization = visualizationFixture()
    const exit = visualization.markers.find((marker) => marker.id === 'trade-1-exit')!
    exit.time = '2026-07-01T00:44:59.999Z'
    exit.candleTime = '2026-07-01T00:30:00.000Z'
    visualization.unalignedMarkers = []
    const trades = tradePageFixture()
    trades.items[0].exitTime = exit.time
    renderDetail({ visualization: parseVisualization(visualization), trades })

    const marker = await screen.findByTestId('marker-trade-1-exit')
    expect(marker.querySelector('title')).toHaveTextContent(exit.time)
    expect(marker.querySelector('title')).toHaveTextContent(exit.price!)
    expect(screen.queryByTestId('state-unaligned-markers')).toBeNull()
    await userEvent.click(await screen.findByTestId('row-trade-trade-1'))
    expect(screen.getByTestId('chart-highlight')).toBeInTheDocument()
    expect(screen.getByTestId('marker-trade-1-exit-selected')).toBeInTheDocument()
    expect(screen.getByTestId('detail-selected-trade')).toHaveTextContent(exit.time)
  })

  it('reports an unaligned marker instead of placing it on a guessed Candle', async () => {
    renderDetail()

    const note = await screen.findByTestId('state-unaligned-markers')
    expect(note).toHaveTextContent('could not be aligned')
    expect(note).toHaveTextContent('2026-07-01T00:07:00.000Z')
    expect(screen.queryByTestId('marker-signal-unaligned')).toBeNull()
  })

  it('renders generic overlays by primitive kind for an unknown strategy', async () => {
    renderDetail()

    const overlay = await screen.findByTestId('overlay-overlay-1')
    expect(overlay).toHaveAttribute('data-kind', 'LINE')
    expect(overlay).toHaveAttribute('aria-label', 'Trend line')
  })

  it('renders BAND and ZONE overlays through the same contract', async () => {
    const visualization = visualizationFixture()
    visualization.overlays = [
      {
        id: 'band-1',
        kind: 'BAND',
        label: 'Volatility band',
        styleToken: 'SECONDARY_INDICATOR',
        sourceStrategyId: 'brand-new-strategy',
        sourceStrategyVersion: '1',
        points: [
          { time: '2026-07-01T00:00:00.000Z', upper: '100200', middle: '100050', lower: '99900' },
          { time: '2026-07-01T00:15:00.000Z', upper: '100300', middle: '100150', lower: '100000' },
        ],
      },
      {
        id: 'zone-1',
        kind: 'ZONE',
        label: 'Support zone',
        styleToken: 'BOUNDARY',
        sourceStrategyId: 'brand-new-strategy',
        sourceStrategyVersion: '1',
        points: [
          {
            startTime: '2026-07-01T00:00:00.000Z',
            endTime: '2026-07-01T00:30:00.000Z',
            upper: '100100',
            lower: '99950',
          },
        ],
      },
    ]
    renderDetail({ visualization })

    expect(await screen.findByTestId('overlay-band-1')).toHaveAttribute('data-kind', 'BAND')
    expect(screen.getByTestId('overlay-zone-1')).toHaveAttribute('data-kind', 'ZONE')
  })

  it('states clearly when no overlay descriptor is published', async () => {
    renderDetail()

    expect(await screen.findByTestId('state-overlays-unavailable')).toHaveTextContent(
      'No overlay descriptor is published.',
    )
  })

  it('highlights both endpoints when a trade is selected by keyboard', async () => {
    renderDetail()

    const row = await screen.findByTestId('row-trade-trade-1')
    row.focus()
    await userEvent.keyboard('{Enter}')

    expect(screen.getByTestId('marker-trade-1-entry')).toHaveAttribute('data-selected', 'true')
    expect(screen.getByTestId('marker-trade-1-exit')).toHaveAttribute('data-selected', 'true')
    expect(screen.getByTestId('marker-trade-1-entry-selected')).toBeInTheDocument()
    expect(screen.getByTestId('chart-highlight')).toBeInTheDocument()
  })

  it('exposes full trade detail for the selected row', async () => {
    renderDetail()

    await userEvent.click(await screen.findByTestId('row-trade-trade-3'))

    const detail = screen.getByTestId('detail-selected-trade')
    expect(detail).toHaveTextContent('LONG')
    expect(detail).toHaveTextContent('0.05')
    expect(detail).toHaveTextContent('7.5')
    expect(detail).toHaveTextContent('trade-3-entry-signal')
    expect(detail).toHaveTextContent('trade-3-exit-signal')
  })

  it('sorts and pages the trade list through the backend query', async () => {
    const { loadTrades } = renderDetail()
    await screen.findByTestId('table-trades')

    await userEvent.click(screen.getByTestId('control-trade-sort-RETURN_PERCENT'))

    await waitFor(() =>
      expect(loadTrades).toHaveBeenLastCalledWith(
        'board-1',
        'eval-1',
        expect.objectContaining({ sortBy: 'RETURN_PERCENT', page: 1 }),
      ),
    )
  })

  it('shows an explicit no-trade state instead of an empty table', async () => {
    const detail = detailFixture()
    detail.trades = { state: 'EMPTY', count: 0, reason: 'The result produced no simulated Trade.' }
    renderDetail({ detail, trades: { items: [], pagination: { page: 1, pageSize: 25, total: 0 } } })

    expect(await screen.findByTestId('state-trades-empty')).toHaveTextContent(
      'no simulated Trade',
    )
    expect(screen.queryByTestId('table-trades')).toBeNull()
  })

  it('keeps Candles inspectable when the chart has no marker at all', async () => {
    const visualization = visualizationFixture()
    visualization.markers = []
    visualization.unalignedMarkers = []
    renderDetail({ visualization })

    expect(await screen.findByTestId('chart-candles')).toBeInTheDocument()
    expect(screen.getByTestId('marker-layer')).toBeEmptyDOMElement()
  })

  it('shows an empty-chart state when no Candle is available', async () => {
    const visualization = visualizationFixture()
    visualization.candles = []
    renderDetail({ visualization })

    expect(await screen.findByTestId('chart-candles-empty')).toBeInTheDocument()
  })

  it('displays availability for candles, overlays, signals, and trades', async () => {
    renderDetail()

    expect(await screen.findByTestId('availability-candles')).toHaveAttribute(
      'data-state',
      'AVAILABLE',
    )
    expect(screen.getByTestId('availability-overlays')).toHaveAttribute('data-state', 'UNAVAILABLE')
  })

  it('exposes complete provenance in one drill-down', async () => {
    renderDetail()

    const provenance = await screen.findByTestId('detail-provenance')
    expect(provenance).toHaveTextContent('eval-1')
    expect(provenance).toHaveTextContent('result-1')
    expect(provenance).toHaveTextContent('run-1')
    expect(provenance).toHaveTextContent('job-1')
    expect(provenance).toHaveTextContent('strategy-1 v3')
    expect(provenance).toHaveTextContent('dataset-1')
    expect(provenance).toHaveTextContent('checksum-1')
    expect(provenance).toHaveTextContent('balanced v2')
    expect(provenance).toHaveTextContent('initialCapital=10000')
  })

  it('repeats the simulated-analysis disclaimer without a profit claim', async () => {
    renderDetail()

    const disclaimer = (await screen.findByTestId('disclaimer-ranked-result')).textContent ?? ''
    expect(disclaimer.toLowerCase()).toContain('simulated historical analysis')
    expect(disclaimer.toLowerCase()).toContain('not investment advice')
    expect(disclaimer.toLowerCase()).not.toContain('guaranteed profit')
  })

  it('surfaces a failed detail load without inventing chart data', async () => {
    const loadDetail = vi.fn().mockRejectedValue(new Error('LEADERBOARD_ENTRY_NOT_FOUND'))
    render(
      <RankedResultDetail
        leaderboardId="board-1"
        evaluationResultId="missing"
        loadDetail={loadDetail}
        loadVisualization={vi.fn()}
        loadTrades={vi.fn().mockResolvedValue(tradePageFixture())}
      />,
    )

    expect(await screen.findByTestId('state-detail-error')).toHaveTextContent(
      'LEADERBOARD_ENTRY_NOT_FOUND',
    )
    expect(screen.queryByTestId('chart-candles')).toBeNull()
  })
})
