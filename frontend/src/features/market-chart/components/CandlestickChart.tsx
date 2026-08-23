/**
 * Generic SVG candlestick chart.
 *
 * The chart owns scales and candle rendering only. Features extend it through
 * the `overlays` and `markers` render inputs, so it never imports leaderboard,
 * strategy, or evaluation behaviour.
 */

import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'

export type ChartCandle = {
  openTime: string
  open: string
  high: string
  low: string
  close: string
}

export type ChartScale = {
  /** Pixel x for a UTC instant; null when the instant is outside the range. */
  x: (time: string) => number | null
  /** Pixel y for a decimal price string. */
  y: (price: string) => number
  plotWidth: number
  plotHeight: number
  candleWidth: number
}

export type CandlestickChartProps = {
  candles: ChartCandle[]
  height?: number
  emptyMessage?: string
  overlays?: (scale: ChartScale) => ReactNode
  markers?: (scale: ChartScale) => ReactNode
  highlightRange?: { startTime: string; endTime: string } | null
  testId?: string
}

const PAD_RIGHT = 56
const PAD_BOTTOM = 18

export function CandlestickChart({
  candles,
  height = 320,
  emptyMessage = 'No Candle is available for this range.',
  overlays,
  markers,
  highlightRange = null,
  testId = 'chart-candles',
}: CandlestickChartProps) {
  const wrapper = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(720)

  useEffect(() => {
    const element = wrapper.current
    if (!element || typeof ResizeObserver === 'undefined') return
    if (element.clientWidth) setWidth(element.clientWidth)
    const observer = new ResizeObserver(() => setWidth(element.clientWidth || width))
    observer.observe(element)
    return () => observer.disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const plotWidth = Math.max(160, width - PAD_RIGHT)
  const plotHeight = Math.max(80, height - PAD_BOTTOM)

  const scale = useMemo<ChartScale>(() => {
    const times = candles.map((candle) => candle.openTime)
    const index = new Map(times.map((time, position) => [time, position]))
    let low = Number.POSITIVE_INFINITY
    let high = Number.NEGATIVE_INFINITY
    for (const candle of candles) {
      low = Math.min(low, Number(candle.low))
      high = Math.max(high, Number(candle.high))
    }
    if (!Number.isFinite(low) || !Number.isFinite(high)) {
      low = 0
      high = 1
    }
    const padding = (high - low) * 0.08 || 1
    const min = low - padding
    const max = high + padding
    const step = plotWidth / Math.max(1, candles.length)
    return {
      x: (time: string) => {
        const position = index.get(time)
        if (position === undefined) return null
        return position * step + step / 2
      },
      y: (price: string) => {
        const value = Number(price)
        if (!Number.isFinite(value)) return plotHeight
        return plotHeight - ((value - min) / (max - min)) * plotHeight
      },
      plotWidth,
      plotHeight,
      candleWidth: Math.max(1, step * 0.6),
    }
  }, [candles, plotWidth, plotHeight])

  if (candles.length === 0) {
    return (
      <div
        ref={wrapper}
        data-testid={`${testId}-empty`}
        className="flex items-center justify-center rounded-[6px] border border-subtle bg-workspace p-6 text-[12px] text-dim"
        style={{ height }}
      >
        {emptyMessage}
      </div>
    )
  }

  const highlightStart = highlightRange ? scale.x(highlightRange.startTime) : null
  const highlightEnd = highlightRange ? scale.x(highlightRange.endTime) : null

  return (
    <div ref={wrapper} className="w-full overflow-hidden rounded-[6px] border border-subtle bg-workspace">
      <svg
        data-testid={testId}
        role="img"
        aria-label="Simulated historical Candles with strategy overlays and trade markers"
        width="100%"
        height={height}
        viewBox={`0 0 ${plotWidth + PAD_RIGHT} ${height}`}
        preserveAspectRatio="none"
      >
        {highlightStart !== null && highlightEnd !== null && (
          <rect
            data-testid="chart-highlight"
            x={Math.min(highlightStart, highlightEnd) - scale.candleWidth}
            y={0}
            width={Math.abs(highlightEnd - highlightStart) + scale.candleWidth * 2}
            height={scale.plotHeight}
            fill="currentColor"
            opacity={0.08}
          />
        )}
        {candles.map((candle) => {
          const x = scale.x(candle.openTime) ?? 0
          const openY = scale.y(candle.open)
          const closeY = scale.y(candle.close)
          const rising = Number(candle.close) >= Number(candle.open)
          const top = Math.min(openY, closeY)
          const body = Math.max(1, Math.abs(closeY - openY))
          return (
            <g key={candle.openTime} data-testid={`candle-${candle.openTime}`}>
              <line
                x1={x}
                x2={x}
                y1={scale.y(candle.high)}
                y2={scale.y(candle.low)}
                stroke={rising ? '#26A69A' : '#EF5350'}
                strokeWidth={1}
              />
              <rect
                x={x - scale.candleWidth / 2}
                y={top}
                width={scale.candleWidth}
                height={body}
                fill={rising ? '#26A69A' : '#EF5350'}
              />
            </g>
          )
        })}
        {overlays?.(scale)}
        {markers?.(scale)}
      </svg>
    </div>
  )
}
