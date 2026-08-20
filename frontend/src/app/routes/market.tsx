import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { ChartGrid } from "../../features/market-chart/components/ChartGrid";
import { createMarketDataApi } from "../../features/market-chart/api/marketDataApi";
import {
  type ChartMarketDataLifecycle,
  useChartSlots,
} from "../../features/market-chart/hooks/useChartSlot";
import { createMarketDataSocket } from "../../features/market-chart/realtime/marketDataSocket";
import {
  MARKET_DATA_TIMEFRAMES,
  type MarketSelection,
  type TimeRange,
  type Timeframe,
} from "../../features/market-chart/types";

export type MarketRouteProps = {
  initialTimeframes?: readonly Timeframe[];
  createSlotId?: () => string;
  marketData?: ChartMarketDataLifecycle;
};

export function MarketRoute({
  initialTimeframes = ["5m"],
  createSlotId,
  marketData,
}: MarketRouteProps) {
  const model = useChartSlots({
    provider: "BINANCE",
    pair: "BTCUSDT",
    defaultTimeframe: "5m",
    initialTimeframes,
    createSlotId,
    marketData,
  });

  return (
    <main className="min-w-0 p-3 md:p-4">
      <div className="mb-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-faint">
          Realtime market workspace
        </p>
        <h1 className="text-xl font-semibold text-ink">Multi-chart market data</h1>
        <p className="mt-1 max-w-2xl text-sm text-dim">
          Compare one dashboard pair across independent timeframes. Each chart keeps its own
          status and controls.
        </p>
      </div>
      <ChartGrid
        pair={model.pair}
        slots={model.slots}
        timeframes={MARKET_DATA_TIMEFRAMES}
        limitMessage={model.limitMessage}
        announcement={model.announcement}
        onAdd={model.addSlot}
        onRemove={model.removeSlot}
        onTimeframeChange={model.changeTimeframe}
        onRetry={model.retrySlot}
      />
      <footer className="mt-4 text-[11px] text-faint">
        <a
          href="https://www.tradingview.com/"
          target="_blank"
          rel="noreferrer"
          className="inline-block underline decoration-transparent underline-offset-2 transition-colors hover:text-dim hover:decoration-current focus-visible:text-dim focus-visible:decoration-current"
        >
          <span className="block">TradingView Lightweight Charts™</span>
          <span className="block">
            Copyright (с) 2025 TradingView, Inc. https://www.tradingview.com/
          </span>
        </a>
      </footer>
    </main>
  );
}

/** Production route adapter. Tests can render MarketRoute without opening network I/O. */
export function ConnectedMarketRoute() {
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

  useEffect(() => {
    socket.connect();
    return () => socket.close();
  }, [socket]);

  return <MarketRoute marketData={marketData} />;
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
