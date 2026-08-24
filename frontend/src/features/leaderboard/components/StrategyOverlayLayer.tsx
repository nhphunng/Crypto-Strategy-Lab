/**
 * Renders strategy overlays by primitive kind only.
 *
 * Adding MACD, a Sentiment Strategy, or any future Strategy requires no change
 * here: the renderer dispatches on LINE / BAND / ZONE, never on a strategy name.
 */

import type { ChartScale } from './RankedResultChart'
import type { Overlay, OverlayPoint } from '../types'

export type StrategyOverlayLayerProps = {
  overlays: Overlay[]
  scale: ChartScale
}

const STYLE_TOKENS: Record<string, string> = {
  PRIMARY_INDICATOR: '#5B8DEF',
  SECONDARY_INDICATOR: '#B07CE8',
  BOUNDARY: '#E8B54D',
  DEFAULT: '#7A8CA3',
}

function stroke(styleToken: string): string {
  return STYLE_TOKENS[styleToken] ?? STYLE_TOKENS.DEFAULT
}

function linePath(points: OverlayPoint[], scale: ChartScale, key: 'value' | 'upper' | 'lower') {
  const segments: string[] = []
  for (const point of points) {
    const value = point[key]
    if (!point.time || value === null || value === undefined) continue
    const x = scale.x(point.time)
    if (x === null) continue
    segments.push(`${segments.length === 0 ? 'M' : 'L'}${x},${scale.y(value)}`)
  }
  return segments.join(' ')
}

export function StrategyOverlayLayer({ overlays, scale }: StrategyOverlayLayerProps) {
  return (
    <g data-testid="overlay-layer">
      {overlays.map((overlay) => {
        const color = stroke(overlay.styleToken)
        if (overlay.kind === 'LINE') {
          return (
            <path
              key={overlay.id}
              data-testid={`overlay-${overlay.id}`}
              data-kind="LINE"
              aria-label={overlay.label}
              d={linePath(overlay.points, scale, 'value')}
              fill="none"
              stroke={color}
              strokeWidth={1.5}
            />
          )
        }
        if (overlay.kind === 'BAND') {
          return (
            <g key={overlay.id} data-testid={`overlay-${overlay.id}`} data-kind="BAND">
              <path
                d={linePath(overlay.points, scale, 'upper')}
                fill="none"
                stroke={color}
                strokeWidth={1}
                strokeDasharray="4 3"
                aria-label={`${overlay.label} upper`}
              />
              <path
                d={linePath(overlay.points, scale, 'lower')}
                fill="none"
                stroke={color}
                strokeWidth={1}
                strokeDasharray="4 3"
                aria-label={`${overlay.label} lower`}
              />
            </g>
          )
        }
        return (
          <g key={overlay.id} data-testid={`overlay-${overlay.id}`} data-kind="ZONE">
            {overlay.points.map((point, index) => {
              if (!point.startTime || !point.endTime) return null
              if (point.upper === null || point.lower === null) return null
              const start = scale.x(point.startTime)
              const end = scale.x(point.endTime)
              if (start === null || end === null) return null
              const top = scale.y(point.upper ?? '0')
              const bottom = scale.y(point.lower ?? '0')
              return (
                <rect
                  key={`${overlay.id}-${index}`}
                  x={Math.min(start, end)}
                  y={Math.min(top, bottom)}
                  width={Math.max(1, Math.abs(end - start))}
                  height={Math.max(1, Math.abs(bottom - top))}
                  fill={color}
                  opacity={0.14}
                  stroke={color}
                  strokeWidth={0.75}
                  aria-label={overlay.label}
                />
              )
            })}
          </g>
        )
      })}
    </g>
  )
}
