/**
 * Buy / Sell / Hold / Entry / Exit markers.
 *
 * Every marker carries its own label and shape, so the categories stay
 * distinguishable in grayscale and for colour-vision deficiencies. Recorded
 * coordinates are used as-is; an unaligned marker is reported, never moved.
 */

import type { ChartScale } from './RankedResultChart'
import type { Marker, MarkerShape, MarkerType } from '../types'

export type TradeSignalMarkersProps = {
  markers: Marker[]
  scale: ChartScale
  showHold?: boolean
  selectedTradeId?: string | null
}

const TONE_COLORS: Record<string, string> = {
  POSITIVE: '#26A69A',
  NEGATIVE: '#EF5350',
  NEUTRAL: '#8A94A6',
  INFO: '#5B8DEF',
}

function shapePath(shape: MarkerShape, x: number, y: number): string {
  const size = 6
  switch (shape) {
    case 'ARROW_UP':
    case 'TRIANGLE_UP':
    case 'ENTRY_OUTLINED':
      return `M${x},${y - size} L${x + size},${y + size} L${x - size},${y + size} Z`
    case 'ARROW_DOWN':
    case 'TRIANGLE_DOWN':
    case 'EXIT_OUTLINED':
      return `M${x},${y + size} L${x + size},${y - size} L${x - size},${y - size} Z`
    case 'DIAMOND':
      return `M${x},${y - size} L${x + size},${y} L${x},${y + size} L${x - size},${y} Z`
    default:
      return `M${x - size / 2},${y} a${size / 2},${size / 2} 0 1,0 ${size},0 a${size / 2},${size / 2} 0 1,0 -${size},0`
  }
}

/** Outlined shapes distinguish trade endpoints from raw signals without colour. */
const OUTLINED: MarkerShape[] = ['ENTRY_OUTLINED', 'EXIT_OUTLINED']

function verticalOffset(type: MarkerType): number {
  if (type === 'ENTRY') return -14
  if (type === 'EXIT') return 14
  if (type === 'HOLD') return 0
  return type === 'BUY' ? 18 : -18
}

export function TradeSignalMarkers({
  markers,
  scale,
  showHold = false,
  selectedTradeId = null,
}: TradeSignalMarkersProps) {
  const visible = markers.filter((marker) => showHold || marker.type !== 'HOLD')
  const seen = new Map<string, number>()

  return (
    <g data-testid="marker-layer">
      {visible.map((marker) => {
        const x = scale.x(marker.time)
        if (x === null || marker.price === null) return null
        const baseY = scale.y(marker.price)
        // Overlapping markers keep separate ids and are offset, never merged.
        const key = `${Math.round(x)}:${Math.round(baseY)}`
        const overlap = seen.get(key) ?? 0
        seen.set(key, overlap + 1)
        const y = baseY + verticalOffset(marker.type) + overlap * 12
        const color = TONE_COLORS[marker.tone ?? 'NEUTRAL'] ?? TONE_COLORS.NEUTRAL
        const selected = selectedTradeId !== null && marker.tradeId === selectedTradeId
        return (
          <g
            key={marker.id}
            data-testid={`marker-${marker.id}`}
            data-marker-type={marker.type}
            data-marker-shape={marker.shape}
            data-selected={selected ? 'true' : 'false'}
            aria-label={marker.label}
          >
            <title>{`${marker.label} · ${marker.time} · ${marker.price}`}</title>
            <path
              d={shapePath(marker.shape, x, y)}
              fill={OUTLINED.includes(marker.shape) ? 'none' : color}
              stroke={color}
              strokeWidth={selected ? 2.5 : 1.25}
            />
            <text
              x={x}
              y={y - 9}
              textAnchor="middle"
              fontSize={9}
              fill="currentColor"
              className="font-mono"
            >
              {marker.label}
            </text>
            {selected && (
              <circle
                data-testid={`marker-${marker.id}-selected`}
                cx={x}
                cy={y}
                r={11}
                fill="none"
                stroke={color}
                strokeDasharray="3 2"
              />
            )}
          </g>
        )
      })}
    </g>
  )
}
