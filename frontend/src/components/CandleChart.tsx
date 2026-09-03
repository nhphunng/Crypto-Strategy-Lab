import { useEffect, useMemo, useRef, useState } from 'react'
import {
  formatChartPrice,
  simpleMovingAverage,
  supportResistance,
  type Candle,
  type Marker,
} from './candleChartModel'
import { cn } from './ui'

export type { Candle, Marker } from './candleChartModel'

type Overlays = {
  ma20?: boolean
  ma50?: boolean
  bb?: boolean
  sr?: boolean
}

type Props = {
  candles: Candle[]
  overlays?: Overlays
  markers?: Marker[]
  height?: number
  volume?: boolean
  selectedInterval?: [number, number] | null
  compact?: boolean
}

const PAD_R = 52 // price axis gutter
const PAD_B = 18 // time axis gutter

export function CandleChart({
  candles,
  overlays = {},
  markers = [],
  height = 260,
  volume = true,
  selectedInterval = null,
  compact = false,
}: Props) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const [w, setW] = useState(600)
  const [hover, setHover] = useState<number | null>(null)

  // Measure the container width and keep it in sync on resize.
  useEffect(() => {
    const el = wrapRef.current
    if (!el || typeof ResizeObserver === 'undefined') return
    setW(el.clientWidth)
    const ro = new ResizeObserver(() => setW(el.clientWidth))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const volH = volume ? (compact ? 26 : 42) : 0
  const priceH = height - volH - PAD_B
  const plotW = Math.max(120, w - PAD_R)

  const { min, max } = useMemo(() => {
    if (candles.length === 0) return { min: 0, max: 1 }
    let lo = Infinity
    let hi = -Infinity
    for (const c of candles) {
      lo = Math.min(lo, c.l)
      hi = Math.max(hi, c.h)
    }
    const pad = Math.max((hi - lo) * 0.08, Math.abs(hi) * 0.0001, 0.01)
    return { min: lo - pad, max: hi + pad }
  }, [candles])

  const maxVol = useMemo(() => Math.max(...candles.map((c) => c.v), 1), [candles])
  const ma20 = useMemo(() => (overlays.ma20 ? simpleMovingAverage(candles, 20) : null), [candles, overlays.ma20])
  const ma50 = useMemo(() => (overlays.ma50 ? simpleMovingAverage(candles, 50) : null), [candles, overlays.ma50])
  const bb = useMemo(() => {
    if (!overlays.bb) return null
    const period = 20
    const mid = simpleMovingAverage(candles, period)
    const upper: (number | null)[] = []
    const lower: (number | null)[] = []
    for (let i = 0; i < candles.length; i++) {
      if (i < period - 1 || mid[i] == null) {
        upper.push(null)
        lower.push(null)
        continue
      }
      let s = 0
      for (let j = i - period + 1; j <= i; j++) s += (candles[j].c - (mid[i] as number)) ** 2
      const sd = Math.sqrt(s / period)
      upper.push((mid[i] as number) + 2 * sd)
      lower.push((mid[i] as number) - 2 * sd)
    }
    return { mid, upper, lower }
  }, [candles, overlays.bb])
  const sr = useMemo(() => (overlays.sr && candles.length > 0 ? supportResistance(candles) : null), [candles, overlays.sr])

  const n = candles.length
  const slot = plotW / Math.max(n, 1)
  const cw = Math.max(1.5, slot * 0.62)

  const x = (i: number) => i * slot + slot / 2
  const y = (p: number) => ((max - p) / (max - min)) * priceH
  const line = (arr: (number | null)[]) =>
    arr
      .map((v, i) => (v == null ? null : `${x(i).toFixed(1)},${y(v).toFixed(1)}`))
      .filter(Boolean)
      .join(' ')

  const hoverC = hover != null ? candles[hover] : candles[n - 1]

  return (
    <div ref={wrapRef} className="relative h-full w-full">
      <svg
        width={w}
        height={height}
        className="block"
        onMouseMove={(e) => {
          if (n === 0) return
          const rect = e.currentTarget.getBoundingClientRect()
          const px = e.clientX - rect.left
          const i = Math.max(0, Math.min(n - 1, Math.floor(px / slot)))
          setHover(i)
        }}
        onMouseLeave={() => setHover(null)}
      >
        {n === 0 && (
          <text x={plotW / 2} y={priceH / 2} textAnchor="middle" fill="var(--color-faint)" fontSize={12}>
            No Candles
          </text>
        )}
        {/* grid */}
        {[0, 0.25, 0.5, 0.75, 1].map((g) => (
          <line
            key={g}
            x1={0}
            x2={plotW}
            y1={g * priceH}
            y2={g * priceH}
            stroke="var(--color-grid)"
            strokeWidth={1}
          />
        ))}
        {[0.25, 0.5, 0.75, 1].map((g) => {
          const p = max - g * (max - min)
          return (
            <text
              key={g}
              x={plotW + 6}
              y={g * priceH + 3}
              fill="var(--color-faint)"
              fontSize={10}
              className="font-mono"
            >
              {formatChartPrice(p)}
            </text>
          )
        })}

        {/* support / resistance zones */}
        {sr && (
          <>
            <rect
              x={0}
              y={y(sr.resistance[1])}
              width={plotW}
              height={Math.abs(y(sr.resistance[0]) - y(sr.resistance[1]))}
              fill="var(--color-chart-resistance, #F05B6433)"
              style={{ fill: '#F05B6422' }}
            />
            <rect
              x={0}
              y={y(sr.support[1])}
              width={plotW}
              height={Math.abs(y(sr.support[0]) - y(sr.support[1]))}
              style={{ fill: '#22C98A22' }}
            />
          </>
        )}

        {/* selected trade interval */}
        {selectedInterval && (
          <rect
            x={x(selectedInterval[0]) - cw / 2}
            y={0}
            width={Math.max(cw, x(selectedInterval[1]) - x(selectedInterval[0]))}
            height={priceH}
            style={{ fill: '#4F7CFF1f' }}
            stroke="#4F7CFF66"
            strokeDasharray="3 3"
          />
        )}

        {/* bollinger */}
        {bb && (
          <>
            <polyline points={line(bb.upper)} fill="none" stroke="#59A8FF66" strokeWidth={1} />
            <polyline points={line(bb.lower)} fill="none" stroke="#59A8FF66" strokeWidth={1} />
            <polyline points={line(bb.mid)} fill="none" stroke="#59A8FFaa" strokeWidth={1} strokeDasharray="2 2" />
          </>
        )}

        {/* candles */}
        {candles.map((c, i) => {
          const up = c.c >= c.o
          const col = up ? '#21C58B' : '#F05B64'
          const xc = x(i)
          const yh = y(c.h)
          const yl = y(c.l)
          const yo = y(c.o)
          const yclose = y(c.c)
          const top = Math.min(yo, yclose)
          const bh = Math.max(1, Math.abs(yclose - yo))
          return (
            <g key={i}>
              <line x1={xc} x2={xc} y1={yh} y2={yl} stroke={col} strokeWidth={1} />
              <rect x={xc - cw / 2} y={top} width={cw} height={bh} fill={col} />
            </g>
          )
        })}

        {/* MA overlays */}
        {ma20 && <polyline points={line(ma20)} fill="none" stroke="#4F7CFF" strokeWidth={1.4} />}
        {ma50 && <polyline points={line(ma50)} fill="none" stroke="#E6B94A" strokeWidth={1.4} />}

        {/* signal markers */}
        {markers.map((m, k) => {
          const xc = x(m.index)
          const c = candles[m.index]
          if (!c) return null
          if (m.kind === 'buy') {
            const yy = y(c.l) + 10
            return (
              <polygon
                key={k}
                points={`${xc},${yy} ${xc - 4},${yy + 7} ${xc + 4},${yy + 7}`}
                fill="#21C58B"
              />
            )
          }
          if (m.kind === 'sell') {
            const yy = y(c.h) - 10
            return (
              <polygon
                key={k}
                points={`${xc},${yy} ${xc - 4},${yy - 7} ${xc + 4},${yy - 7}`}
                fill="#F05B64"
              />
            )
          }
          const yy = y(c.c)
          return (
            <g key={k}>
              <circle cx={xc} cy={yy} r={5} fill="var(--color-surface)" stroke="#9AA7B6" strokeWidth={1} />
              <text x={xc} y={yy + 3} fontSize={7} textAnchor="middle" fill="#E7ECF3" className="font-mono">
                {m.kind === 'entry' ? 'E' : 'X'}
              </text>
            </g>
          )
        })}

        {/* volume */}
        {volume &&
          candles.map((c, i) => {
            const up = c.c >= c.o
            const vh = (c.v / maxVol) * volH
            return (
              <rect
                key={i}
                x={x(i) - cw / 2}
                y={priceH + PAD_B + (volH - vh)}
                width={cw}
                height={vh}
                fill={up ? '#21C58B44' : '#F05B6444'}
              />
            )
          })}

        {/* crosshair */}
        {hover != null && candles[hover] && (
          <>
            <line
              x1={x(hover)}
              x2={x(hover)}
              y1={0}
              y2={priceH + PAD_B + volH}
              stroke="var(--color-crosshair)"
              strokeWidth={1}
              strokeDasharray="3 3"
            />
            <rect x={plotW} y={y(candles[hover].c) - 8} width={PAD_R} height={16} fill="#1D2632" />
            <text
              x={plotW + 6}
              y={y(candles[hover].c) + 3}
              fill="#E7ECF3"
              fontSize={10}
              className="font-mono"
            >
              {formatChartPrice(candles[hover].c)}
            </text>
          </>
        )}
      </svg>

      {/* OHLC readout */}
      {!compact && hoverC && (
        <div className="pointer-events-none absolute left-2 top-2 flex gap-3 font-mono text-[10px] tabular-nums">
          {(['o', 'h', 'l', 'c'] as const).map((k) => (
            <span key={k} className="text-faint">
              {k.toUpperCase()}{' '}
              <span className={hoverC.c >= hoverC.o ? 'text-pos' : 'text-neg'}>{formatChartPrice(hoverC[k])}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
