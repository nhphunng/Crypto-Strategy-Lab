import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { useStore } from "../../lib/store";
import { ChartGrid } from "../../features/market-chart/components/ChartGrid";
import { MarketGuide } from "../../features/market-chart/components/MarketGuide";
import {
  createMarketDataApi,
  createMarketDimensionsQueryOptions,
} from "../../features/market-chart/api/marketDataApi";
import {
  type ChartMarketDataLifecycle,
  useChartSlots,
} from "../../features/market-chart/hooks/useChartSlot";
import { createMarketDataSocket } from "../../features/market-chart/realtime/marketDataSocket";
import {
  MARKET_DATA_TIMEFRAMES,
  type MarketDimensions,
  type MarketSelection,
  type Provider,
  type TimeRange,
  type Timeframe,
} from "../../features/market-chart/types";

export type MarketRouteProps = {
  initialTimeframes?: readonly Timeframe[];
  createSlotId?: () => string;
  marketData?: ChartMarketDataLifecycle;
  pair?: string;
  pairs?: readonly string[];
  provider?: Provider;
  timeframes?: readonly Timeframe[];
  onPairChange?: (pair: string) => void;
  capabilityError?: string;
  onRetryCapabilities?: () => void;
};

const DEFAULT_MARKET_PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"] as const;

type MarketDimensionsQueryState = {
  isSuccess: boolean;
  isError: boolean;
  isFetching: boolean;
};

export function isMarketDataConnectionReady(
  provider: Provider,
  pair: string,
  selectedTimeframes: readonly Timeframe[],
  capabilities: MarketDimensions | undefined,
  state: MarketDimensionsQueryState,
): boolean {
  return (
    state.isSuccess &&
    !state.isError &&
    capabilities !== undefined &&
    capabilities.providers.includes(provider) &&
    capabilities.pairs.length > 0 &&
    capabilities.pairs.includes(pair) &&
    capabilities.timeframes.length > 0 &&
    selectedTimeframes.every((timeframe) => capabilities.timeframes.includes(timeframe))
  );
}

export function isMarketPairConfirmed(
  pair: string,
  confirmedPairs: readonly string[] | undefined,
): boolean {
  return confirmedPairs?.includes(pair) ?? false;
}

export function reconcileMarketPair(
  pair: string,
  confirmedPairs: readonly string[],
): string {
  return confirmedPairs.includes(pair) ? pair : (confirmedPairs[0] ?? pair);
}

export function MarketRoute({
  initialTimeframes = ["5m"],
  createSlotId,
  marketData,
  pair = "BTCUSDT",
  pairs = DEFAULT_MARKET_PAIRS,
  provider = "BINANCE",
  timeframes = MARKET_DATA_TIMEFRAMES,
  onPairChange,
  capabilityError,
  onRetryCapabilities,
}: MarketRouteProps) {
  const model = useChartSlots({
    provider,
    pair,
    defaultTimeframe: initialTimeframes[0] ?? "5m",
    initialTimeframes,
    createSlotId,
    marketData,
  });

  return (
    <main
      data-testid="market-workspace"
      className="flex h-full min-w-0 flex-col overflow-x-hidden overflow-y-auto p-2.5 md:p-3 xl:overflow-y-hidden"
    >
      {capabilityError !== undefined && (
        <div
          id="market-capability-error"
          role="alert"
          className="mb-2 flex shrink-0 items-center justify-between gap-3 rounded-md border border-warn/40 bg-warn/10 px-3 py-2 text-xs text-warn"
        >
          <span>{capabilityError}</span>
          {onRetryCapabilities !== undefined && (
            <button
              type="button"
              onClick={onRetryCapabilities}
              className="shrink-0 rounded border border-warn/50 px-2 py-1 font-semibold hover:bg-warn/10"
            >
              Retry market capabilities
            </button>
          )}
        </div>
      )}
      <div
        data-testid="market-content"
        className="grid min-h-0 min-w-0 flex-1 grid-cols-1 gap-2 xl:grid-cols-[minmax(0,1fr)_15rem]"
      >
        <ChartGrid
          heading="Multi-chart market data"
          pair={model.pair}
          pairs={pairs}
          slots={model.slots}
          timeframes={timeframes}
          limitMessage={model.limitMessage}
          announcement={model.announcement}
          onAdd={model.addSlot}
          onSetCount={model.setSlotCount}
          onRemove={model.removeSlot}
          onTimeframeChange={model.changeTimeframe}
          onRetry={model.retrySlot}
          onPairChange={onPairChange}
        />
        <MarketGuide />
      </div>
      <footer className="mt-2 shrink-0 text-[10px] leading-4 text-faint">
        <a
          href="https://www.tradingview.com/"
          target="_blank"
          rel="noreferrer"
          className="inline-flex flex-wrap gap-x-2 underline decoration-transparent underline-offset-2 transition-colors hover:text-dim hover:decoration-current focus-visible:text-dim focus-visible:decoration-current"
        >
          <span>TradingView Lightweight Charts™</span>
          <span>
            Copyright (с) 2025 TradingView, Inc. https://www.tradingview.com/
          </span>
        </a>
      </footer>
    </main>
  );
}

/** Production route adapter. Tests can render MarketRoute without opening network I/O. */
export function ConnectedMarketRoute() {
  const { market, setMarket } = useStore();
  const queryClient = useQueryClient();
  const [api] = useState(() => createMarketDataApi());
  const [socket] = useState(() =>
    createMarketDataSocket({
      url: marketDataWebSocketUrl(),
      maxCandles: 1_000,
    }),
  );
  const marketData = useMemo<ChartMarketDataLifecycle>(
    () => ({
      api,
      socket,
      queryClient,
      historyRange: recentHistoryRange,
      historyLimit: 500,
    }),
    [api, queryClient, socket],
  );
  const dimensions = useQuery(createMarketDimensionsQueryOptions(api));
  const confirmedPairs = dimensions.data?.pairs;
  const confirmedTimeframes = dimensions.data?.timeframes;
  const pairs = confirmedPairs ?? [market.pair];
  const provider: Provider = "BINANCE";
  const initialTimeframe: Timeframe =
    confirmedTimeframes?.includes("5m") ? "5m" : (confirmedTimeframes?.[0] ?? "5m");
  const initialTimeframes = [initialTimeframe] as const;
  const timeframes = confirmedTimeframes ?? [initialTimeframe];
  const marketDataReady = isMarketDataConnectionReady(
    provider,
    market.pair,
    initialTimeframes,
    dimensions.data,
    dimensions,
  );
  const capabilityError = dimensions.isError
    ? "Market capabilities could not be loaded. Current selection is paused."
    : dimensions.isSuccess &&
        !isMarketDataConnectionReady(
          provider,
          market.pair,
          initialTimeframes,
          dimensions.data,
          dimensions,
        )
      ? "Backend capabilities do not include the current provider, pair, or timeframe. Retry to continue."
      : undefined;

  useEffect(() => {
    if (confirmedPairs === undefined) return;
    const reconciledPair = reconcileMarketPair(market.pair, confirmedPairs);
    if (reconciledPair !== market.pair) setMarket(reconciledPair);
  }, [confirmedPairs, market.pair, setMarket]);

  useEffect(() => {
    if (!marketDataReady) {
      socket.close();
      return;
    }
    socket.connect();
    return () => socket.close();
  }, [marketDataReady, socket]);

  return (
    <MarketRoute
      key={`market-${initialTimeframe}`}
      marketData={marketDataReady ? marketData : undefined}
      pair={market.pair}
      pairs={pairs}
      provider={provider}
      initialTimeframes={initialTimeframes}
      timeframes={timeframes}
      onPairChange={setMarket}
      capabilityError={capabilityError}
      onRetryCapabilities={() => {
        void dimensions.refetch();
      }}
    />
  );
}

const TIMEFRAME_MILLISECONDS: Record<Timeframe, number> = {
  "1m": 60_000,
  "5m": 5 * 60_000,
  "15m": 15 * 60_000,
  "30m": 30 * 60_000,
  "1h": 60 * 60_000,
  "2h": 2 * 60 * 60_000,
  "4h": 4 * 60 * 60_000,
  "1d": 24 * 60 * 60_000,
};

function recentHistoryRange(selection: MarketSelection): TimeRange {
  const interval = TIMEFRAME_MILLISECONDS[selection.timeframe];
  const end = Math.floor(Date.now() / interval) * interval;
  return {
    startTime: new Date(end - interval * 500).toISOString(),
    endTime: new Date(end).toISOString(),
  };
}

function marketDataWebSocketUrl(): string {
  const origin = globalThis.location?.origin ?? "http://localhost";
  const url = new URL("/ws/v1/market-data", origin);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}
