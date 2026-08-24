import { QueryClient } from "@tanstack/react-query";
import { act, render, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ChartGrid } from "../../src/features/market-chart/components/ChartGrid";
import {
  useChartSlots,
  type ChartSlotState,
  type UseChartSlotsOptions,
} from "../../src/features/market-chart/hooks/useChartSlot";
import type { HistoricalCandleRequest } from "../../src/features/market-chart/api/marketDataApi";
import type {
  MarketDataSlotSnapshot,
  MarketDataSlotSubscription,
  SubscribeMarketDataSlot,
} from "../../src/features/market-chart/realtime/marketDataSocket";
import type {
  Candle,
  CandleRange,
  MarketSelection,
  TimeRange,
} from "../../src/features/market-chart/types";

const lightweightCharts = vi.hoisted(() => {
  const instances: Array<{
    chart: {
      addSeries: ReturnType<typeof vi.fn>;
      remove: ReturnType<typeof vi.fn>;
      removeSeries: ReturnType<typeof vi.fn>;
      resize: ReturnType<typeof vi.fn>;
      timeScale: ReturnType<typeof vi.fn>;
    };
    series: {
      applyOptions: ReturnType<typeof vi.fn>;
      setData: ReturnType<typeof vi.fn>;
      update: ReturnType<typeof vi.fn>;
    };
    timeScale: {
      getVisibleLogicalRange: ReturnType<typeof vi.fn>;
      setVisibleLogicalRange: ReturnType<typeof vi.fn>;
    };
  }> = [];
  const createChart = vi.fn(() => {
    const series = {
      applyOptions: vi.fn(),
      setData: vi.fn(),
      update: vi.fn(),
    };
    const timeScale = {
      getVisibleLogicalRange: vi.fn(() => ({ from: 12, to: 42 })),
      setVisibleLogicalRange: vi.fn(),
    };
    const chart = {
      addSeries: vi.fn(() => series),
      remove: vi.fn(),
      removeSeries: vi.fn(),
      resize: vi.fn(),
      timeScale: vi.fn(() => timeScale),
    };
    instances.push({ chart, series, timeScale });
    return chart;
  });

  return { createChart, instances };
});

vi.mock("lightweight-charts", () => ({
  CandlestickSeries: Symbol("CandlestickSeries"),
  LineSeries: Symbol("LineSeries"),
  LineStyle: { Dashed: 2, Solid: 0 },
  createChart: lightweightCharts.createChart,
  createSeriesMarkers: vi.fn(() => ({ detach: vi.fn(), setMarkers: vi.fn() })),
}));

const HISTORY_RANGE: TimeRange = {
  startTime: "2026-08-13T09:00:00Z",
  endTime: "2026-08-13T10:00:00Z",
};

type MarketDataLifecycle = {
  api: {
    getCandles(request: HistoricalCandleRequest): Promise<CandleRange>;
  };
  socket: {
    subscribe(options: SubscribeMarketDataSlot): MarketDataSlotSubscription;
    retry(slotId: string): void;
  };
  queryClient: QueryClient;
  historyRange: TimeRange;
  historyLimit: number;
};

type UseChartSlotsWithLifecycle = (
  options: UseChartSlotsOptions & { marketData: MarketDataLifecycle },
) => ReturnType<typeof useChartSlots>;

const useChartSlotsWithLifecycle =
  useChartSlots as unknown as UseChartSlotsWithLifecycle;

function selection(timeframe: "5m" | "1h"): MarketSelection {
  return { provider: "BINANCE", pair: "BTCUSDT", timeframe };
}

function candle(timeframe: "5m" | "1h", hour = 9): Candle {
  const openTime = `2026-08-13T${String(hour).padStart(2, "0")}:00:00Z`;
  return {
    ...selection(timeframe),
    openTime,
    closeTime: `2026-08-13T${String(hour).padStart(2, "0")}:59:59.999Z`,
    open: "100.00",
    high: "103.00",
    low: "99.00",
    close: "101.00",
    volume: "12.50",
    closed: true,
    receivedAt: "2026-08-13T10:00:01Z",
  };
}

function candleRange(timeframe: "5m" | "1h"): CandleRange {
  return {
    schemaVersion: "1",
    selection: selection(timeframe),
    range: HISTORY_RANGE,
    completeness: "COMPLETE",
    missingRanges: [],
    candles: [candle(timeframe)],
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((complete) => {
    resolve = complete;
  });
  return { promise, resolve };
}

function stableIds() {
  let sequence = 0;
  return () => `slot-${++sequence}`;
}

function lifecycleHarness(
  marketData: MarketDataLifecycle,
  initialTimeframes: readonly ("5m" | "1h")[] = ["5m"],
) {
  return renderHook(() =>
    useChartSlotsWithLifecycle({
      provider: "BINANCE",
      pair: "BTCUSDT",
      defaultTimeframe: "5m",
      initialTimeframes,
      createSlotId: stableIds(),
      marketData,
    }),
  );
}

function createSocketDouble() {
  const subscriptions: SubscribeMarketDataSlot[] = [];
  const handles: MarketDataSlotSubscription[] = [];
  const subscribe = vi.fn((options: SubscribeMarketDataSlot) => {
    const handle: MarketDataSlotSubscription = {
      acceptHistory: vi.fn(() => true),
      release: vi.fn(),
    };
    subscriptions.push(options);
    handles.push(handle);
    return handle;
  });

  return {
    socket: { subscribe, retry: vi.fn() },
    subscriptions,
    handles,
  };
}

describe("timeframe lifecycle generation and cancellation", () => {
  it("aborts the old TanStack history query and never accepts its late result", async () => {
    const oldHistory = deferred<CandleRange>();
    const currentHistory = deferred<CandleRange>();
    let oldSignal: AbortSignal | undefined;
    const getCandles = vi.fn((request: HistoricalCandleRequest) => {
      if (request.selection.timeframe === "5m") {
        oldSignal = request.signal;
        return oldHistory.promise;
      }
      return currentHistory.promise;
    });
    const { socket, handles } = createSocketDouble();
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const { result } = lifecycleHarness({
      api: { getCandles },
      socket,
      queryClient,
      historyRange: HISTORY_RANGE,
      historyLimit: 500,
    });

    expect(getCandles).toHaveBeenCalledOnce();
    expect(oldSignal).toBeInstanceOf(AbortSignal);

    act(() => result.current.changeTimeframe("slot-1", "1h"));

    expect(oldSignal?.aborted).toBe(true);
    expect(getCandles).toHaveBeenCalledTimes(2);
    oldHistory.resolve(candleRange("5m"));
    await act(async () => Promise.resolve());
    expect(handles[0]?.acceptHistory).not.toHaveBeenCalled();

    currentHistory.resolve(candleRange("1h"));
    await act(async () => Promise.resolve());
    expect(handles[1]?.acceptHistory).toHaveBeenCalledWith(
      candleRange("1h").candles,
    );
  });

  it("releases the old generation, acquires the new selection, and ignores late snapshots", () => {
    const { socket, subscriptions, handles } = createSocketDouble();
    const queryClient = new QueryClient();
    const getCandles = vi.fn(async (request: HistoricalCandleRequest) =>
      candleRange(request.selection.timeframe as "5m" | "1h"),
    );
    const { result } = lifecycleHarness({
      api: { getCandles },
      socket,
      queryClient,
      historyRange: HISTORY_RANGE,
      historyLimit: 500,
    });

    expect(subscriptions[0]).toMatchObject({
      slotId: "slot-1",
      generation: 1,
      selection: selection("5m"),
    });
    act(() => result.current.changeTimeframe("slot-1", "1h"));

    expect(handles[0]?.release).toHaveBeenCalledOnce();
    expect(subscriptions[1]).toMatchObject({
      slotId: "slot-1",
      generation: 2,
      selection: selection("1h"),
    });
    expect(result.current.slots[0]).toMatchObject({
      slotId: "slot-1",
      generation: 2,
      timeframe: "1h",
      connectionState: "LOADING",
      candles: [],
    });

    subscriptions[0]?.onSnapshot({
      slotId: "slot-1",
      generation: 1,
      selection: selection("5m"),
      candles: [candle("5m")],
      connectionState: "LIVE",
    });
    expect(result.current.slots[0]).toMatchObject({
      generation: 2,
      timeframe: "1h",
      candles: [],
    });

    const currentSnapshot: MarketDataSlotSnapshot = {
      slotId: "slot-1",
      generation: 2,
      selection: selection("1h"),
      candles: [candle("1h")],
      connectionState: "LIVE",
    };
    act(() => subscriptions[1]?.onSnapshot(currentSnapshot));
    expect(result.current.slots[0]).toMatchObject({
      generation: 2,
      timeframe: "1h",
      candles: currentSnapshot.candles,
      connectionState: "LIVE",
    });
  });

  it("keeps a same-selection sibling's state and binding untouched", () => {
    const { socket, subscriptions, handles } = createSocketDouble();
    const marketData: MarketDataLifecycle = {
      api: { getCandles: vi.fn(async () => candleRange("5m")) },
      socket,
      queryClient: new QueryClient(),
      historyRange: HISTORY_RANGE,
      historyLimit: 500,
    };
    const { result } = lifecycleHarness(marketData, ["5m", "5m"]);

    expect(subscriptions).toHaveLength(2);
    const siblingBefore = result.current.slots[1];
    act(() => result.current.changeTimeframe("slot-1", "1h"));

    expect(result.current.slots[1]).toBe(siblingBefore);
    expect(result.current.slots[1]).toMatchObject({
      slotId: "slot-2",
      generation: 1,
      timeframe: "5m",
      connectionState: "LOADING",
    });
    expect(handles[1]?.release).not.toHaveBeenCalled();
    expect(subscriptions).toHaveLength(3);
  });
});

function slotState(
  slotId: string,
  timeframe: "5m" | "1h",
  generation: number,
): ChartSlotState {
  return {
    slotId,
    pair: "BTCUSDT",
    timeframe,
    generation,
    candles: [candle(timeframe)],
    connectionState: "LIVE",
    lastEventAt: "2026-08-13T10:00:01Z",
    retrySequence: 0,
  };
}

describe("Lightweight chart isolation", () => {
  beforeEach(() => {
    lightweightCharts.createChart.mockClear();
    lightweightCharts.instances.length = 0;
  });

  it("preserves the sibling instance and viewport when one same-selection slot changes", () => {
    const unchanged = slotState("slot-2", "5m", 1);
    const commonProps = {
      pair: "BTCUSDT",
      timeframes: ["5m", "1h"] as const,
      announcement: "",
      onAdd: vi.fn(),
      onRemove: vi.fn(),
      onTimeframeChange: vi.fn(),
      onRetry: vi.fn(),
    };
    const { rerender } = render(
      <ChartGrid
        {...commonProps}
        slots={[slotState("slot-1", "5m", 1), unchanged]}
      />,
    );

    expect(lightweightCharts.instances).toHaveLength(2);
    const siblingInstance = lightweightCharts.instances[1];
    const siblingViewport = siblingInstance?.timeScale.getVisibleLogicalRange();

    rerender(
      <ChartGrid
        {...commonProps}
        slots={[slotState("slot-1", "1h", 2), unchanged]}
      />,
    );

    expect(lightweightCharts.instances).toHaveLength(3);
    expect(siblingInstance?.chart.remove).not.toHaveBeenCalled();
    expect(siblingInstance?.timeScale.setVisibleLogicalRange).not.toHaveBeenCalled();
    expect(siblingInstance?.timeScale.getVisibleLogicalRange()).toEqual(
      siblingViewport,
    );
  });
});
