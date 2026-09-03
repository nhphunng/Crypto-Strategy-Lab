import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'

import {
  createMarketDataApi,
  createMarketDimensionsQueryOptions,
} from '../api/marketDataApi'
import { createMarketDataSocket } from '../realtime/marketDataSocket'
import type { Candle, ConnectionState, MarketSelection, TimeRange } from '../types'
import { useChartSlots, type ChartMarketDataLifecycle } from './useChartSlot'

const TOP_BAR_TIMEFRAME = '5m' as const
const FIVE_MINUTES_MS = 5 * 60 * 1_000
const SUMMARY_WINDOW_MS = 24 * 60 * 60 * 1_000

export type TopBarMarketSummary = {
  pairs: readonly string[]
  price: number | null
  change24h: number | null
  connectionState: ConnectionState
  pairsLoading: boolean
  retry: () => void
}

export function summarizeCandles(candles: readonly Candle[]): {
  price: number | null
  change24h: number | null
} {
  if (candles.length === 0) return { price: null, change24h: null }
  const latestCandle = candles[candles.length - 1]
  const cutoff = Date.parse(latestCandle.closeTime) - SUMMARY_WINDOW_MS
  const baselineCandle = candles.find((candle) => Date.parse(candle.openTime) >= cutoff) ?? candles[0]
  const latest = Number(latestCandle.close)
  const baseline = Number(baselineCandle.open)
  if (!Number.isFinite(latest)) return { price: null, change24h: null }
  if (!Number.isFinite(baseline) || baseline <= 0) return { price: latest, change24h: null }
  return {
    price: latest,
    change24h: ((latest - baseline) / baseline) * 100,
  }
}

export function topBarHistoryRange(_selection: MarketSelection): TimeRange {
  const end = Math.floor(Date.now() / FIVE_MINUTES_MS) * FIVE_MINUTES_MS
  return {
    startTime: new Date(end - SUMMARY_WINDOW_MS).toISOString(),
    endTime: new Date(end).toISOString(),
  }
}

export function useTopBarMarketData(pair: string): TopBarMarketSummary {
  const queryClient = useQueryClient()
  const [api] = useState(() => createMarketDataApi())
  const [socket] = useState(() =>
    createMarketDataSocket({
      url: marketDataWebSocketUrl(),
      maxCandles: 300,
    }),
  )
  const dimensions = useQuery(createMarketDimensionsQueryOptions(api))
  const supported = dimensions.data?.pairs.includes(pair) ?? false
  const lifecycle = useMemo<ChartMarketDataLifecycle>(
    () => ({
      api,
      socket,
      queryClient,
      historyRange: topBarHistoryRange,
      historyLimit: 300,
    }),
    [api, queryClient, socket],
  )
  const model = useChartSlots({
    provider: 'BINANCE',
    pair,
    defaultTimeframe: TOP_BAR_TIMEFRAME,
    initialTimeframes: [TOP_BAR_TIMEFRAME],
    createSlotId: () => 'topbar-market',
    marketData: supported ? lifecycle : undefined,
  })
  const slot = model.slots[0]
  const values = summarizeCandles(slot?.candles ?? [])

  useEffect(() => {
    if (!supported) {
      socket.close()
      return
    }
    socket.connect()
    return () => socket.close()
  }, [socket, supported])

  const connectionState: ConnectionState = dimensions.isError
    ? 'ERROR'
    : !supported
      ? 'LOADING'
      : (slot?.connectionState ?? 'LOADING')

  return {
    pairs: dimensions.data?.pairs ?? [],
    ...values,
    connectionState,
    pairsLoading: dimensions.isPending,
    retry: () => {
      if (dimensions.isError) void dimensions.refetch()
      if (slot !== undefined) model.retrySlot(slot.slotId)
    },
  }
}

function marketDataWebSocketUrl(): string {
  const origin = globalThis.location?.origin ?? 'http://localhost'
  const url = new URL('/ws/v1/market-data', origin)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  return url.toString()
}
