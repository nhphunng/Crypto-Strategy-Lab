import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { CandleChart } from '../../components/CandleChart'

describe('CandleChart render safety', () => {
  it('renders an empty state without invalid SVG coordinates', () => {
    const { container } = render(<CandleChart candles={[]} height={240} />)

    fireEvent.mouseMove(container.querySelector('svg') as SVGElement)
    expect(screen.getByText('No Candles')).toBeVisible()
    expect(container.innerHTML).not.toMatch(/NaN|Infinity/)
  })

  it('adds a non-zero price range for a flat Candle series', () => {
    const { container } = render(
      <CandleChart
        candles={[{ t: 1, o: 100, h: 100, l: 100, c: 100, v: 0 }]}
        overlays={{ sr: true }}
        height={240}
      />,
    )

    expect(container.innerHTML).not.toMatch(/NaN|Infinity/)
  })
})
