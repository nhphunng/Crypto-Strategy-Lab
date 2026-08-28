import { QueryClient } from "@tanstack/react-query";
import { act, fireEvent, render, renderHook, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { marketDataCommandSchema } from "../../src/features/market-chart/schemas";
import { ChartSlot } from "../../src/features/market-chart/components/ChartSlot";
import type { HistoricalCandleRequest } from "../../src/features/market-chart/api/marketDataApi";
import {
  createMarketDataSocket,
  type MarketDataSlotSubscription,
  type SubscribeMarketDataSlot,
} from "../../src/features/market-chart/realtime/marketDataSocket";
import {
  useChartSlots,
  type ChartSlotState,
  type UseChartSlotsOptions,
} from "../../src/features/market-chart/hooks/useChartSlot";
import type {
  Candle,
  CandleRange,
  CandleUpdatedEvent,
  MarketDataWireState,
  MarketSelection,
  SubscriptionStateChangedPayload,
  TimeRange,
  Timeframe,
} from "../../src/features/market-chart/types";

const lightweightCharts = vi.hoisted(() => {
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
    return {
      addSeries: vi.fn(() => series),
      remove: vi.fn(),
      removeSeries: vi.fn(),
      resize: vi.fn(),
      timeScale: vi.fn(() => timeScale),
    };
  });
  return { createChart };
});

vi.mock("lightweight-charts", () => ({
  CandlestickSeries: Symbol("CandlestickSeries"),
  LineSeries: Symbol("LineSeries"),
  LineStyle: { Dashed: 2, Solid: 0 },
  createChart: lightweightCharts.createChart,
  createSeriesMarkers: vi.fn(() => ({ detach: vi.fn(), setMarkers: vi.fn() })),
}));

const FIVE_MINUTES = {
  provider: "BINANCE",
  pair: "BTCUSDT",
  timeframe: "5m",
} as const satisfies MarketSelection;

const ONE_HOUR = {
  provider: "BINANCE",
  pair: "BTCUSDT",
  timeframe: "1h",
} as const satisfies MarketSelection;

const HISTORY_RANGE: TimeRange = {
  startTime: "2026-08-13T09:00:00Z",
  endTime: "2026-08-13T10:00:00Z",
};

function candle(
  selection: MarketSelection,
  openTime: string,
  options: Partial<Pick<Candle, "close" | "closed" | "receivedAt">> = {},
): Candle {
  const close = options.close ?? "101.00";
  return {
    ...selection,
    openTime,
    closeTime: `2026-08-13T${openTime.slice(11, 13)}:${openTime.slice(14, 16)}:59.999Z`,
    open: "100.00",
    high: "103.00",
    low: "99.00",
    close,
    volume: "12.50",
    closed: options.closed ?? false,
    receivedAt: options.receivedAt ?? "2026-08-13T10:00:01Z",
  };
}

function fiveMinuteCandle(hour: number, minute: number, options: Parameters<typeof candle>[2] = {}): Candle {
  const openTime = `2026-08-13T${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}:00Z`;
  return candle(FIVE_MINUTES, openTime, options);
}

function candleEvent(
  eventId: string,
  selection: MarketSelection,
  revision: number,
  value: Candle,
): CandleUpdatedEvent {
  return {
    eventType: "CANDLE_UPDATED",
    version: "1",
    eventId,
    occurredAt: value.receivedAt,
    payload: {
      slotGenerations: { "slot-1": 1, "slot-2": 1, "slot-3": 1 },
      selection,
      revision,
      candle: value,
    },
  };
}

function stateEvent(
  eventId: string,
  selection: MarketSelection,
  state: MarketDataWireState,
  extra: Partial<SubscriptionStateChangedPayload> = {},
): {
  eventType: "SUBSCRIPTION_STATE_CHANGED";
  version: "1";
  eventId: string;
  occurredAt: string;
  payload: SubscriptionStateChangedPayload;
} {
  const slotIds = extra.slotIds ?? ["slot-1"];
  const slotGenerations =
    extra.slotGenerations ?? Object.fromEntries(slotIds.map((slotId) => [slotId, 1]));
  return {
    eventType: "SUBSCRIPTION_STATE_CHANGED",
    version: "1",
    eventId,
    occurredAt: "2026-08-13T10:00:00Z",
    payload: {
      slotIds,
      slotGenerations,
      selection,
      state,
      attempt: 0,
      ...extra,
    },
  };
}

type Listener = (event: Event) => void;

class FakeWebSocket {
  readonly sent: string[] = [];
  readyState = WebSocket.CONNECTING;

  private readonly listeners = new Map<string, Set<Listener>>();

  addEventListener(type: string, listener: EventListener): void {
    const listeners = this.listeners.get(type) ?? new Set<Listener>();
    listeners.add(listener as Listener);
    this.listeners.set(type, listeners);
  }

  removeEventListener(type: string, listener: EventListener): void {
    this.listeners.get(type)?.delete(listener as Listener);
  }

  send(data: string): void {
    this.sent.push(data);
  }

  close(): void {
    this.readyState = WebSocket.CLOSED;
    this.emit("close", new CloseEvent("close"));
  }

  open(): void {
    this.readyState = WebSocket.OPEN;
    this.emit("open", new Event("open"));
  }

  receive(message: unknown): void {
    this.emit(
      "message",
      new MessageEvent("message", { data: JSON.stringify(message) }),
    );
  }

  private emit(type: string, event: Event): void {
    for (const listener of this.listeners.get(type) ?? []) {
      listener(event);
    }
  }
}

function stableIds() {
  let sequence = 0;
  return () => `slot-${++sequence}`;
}

function candleRange(timeframe: "5m" | "1h"): CandleRange {
  return {
    schemaVersion: "1",
    selection: timeframe === "5m" ? FIVE_MINUTES : ONE_HOUR,
    range: HISTORY_RANGE,
    completeness: "COMPLETE",
    missingRanges: [],
    candles: [fiveMinuteCandle(10, 0, { closed: true })],
  };
}

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

function socketHarness(maxCandles = 4) {
  const socket = new FakeWebSocket();
  let requestSequence = 0;
  const connection = createMarketDataSocket({
    url: "ws://localhost/ws/v1/market-data",
    createSocket: () => socket as unknown as WebSocket,
    maxCandles,
    now: () => "2026-08-13T10:00:00Z",
    createRequestId: () => `req-${++requestSequence}`,
  });
  connection.connect();
  return { connection, socket };
}

function hookHarness(initialTimeframes: readonly Timeframe[]) {
  const { connection, socket } = socketHarness(500);
  const retry = vi.spyOn(connection, "retry");
  const getCandles = vi.fn(async (request: HistoricalCandleRequest) =>
    candleRange(request.selection.timeframe as "5m" | "1h"),
  );
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const hook = renderHook(() =>
    useChartSlotsWithLifecycle({
      provider: "BINANCE",
      pair: "BTCUSDT",
      defaultTimeframe: "5m",
      initialTimeframes,
      createSlotId: stableIds(),
      marketData: {
        api: { getCandles },
        socket: connection,
        queryClient,
        historyRange: HISTORY_RANGE,
        historyLimit: 500,
      },
    }),
  );
  socket.open();
  return { hook, socket, connection, retry, getCandles, queryClient };
}

async function settle() {
  await act(async () => {
    await Promise.resolve();
  });
}

function receive(socket: FakeWebSocket, event: unknown) {
  act(() => socket.receive(event));
}

describe("recovery state dispatch", () => {
  it("carries attempt, retryAfterMs, lastEventAt, and reasonCode into the slot snapshot", () => {
    const { connection, socket } = socketHarness();
    const subscription = connection.subscribe({
      slotId: "slot-1",
      generation: 1,
      selection: FIVE_MINUTES,
      onSnapshot: vi.fn(),
    });
    socket.open();
    subscription.acceptHistory([
      fiveMinuteCandle(10, 0, { closed: true }),
    ]);

    socket.receive(
      stateEvent("evt-stale", FIVE_MINUTES, "STALE", {
        attempt: 1,
        reasonCode: "PROVIDER_DISCONNECTED",
        lastEventAt: "2026-08-13T09:59:30Z",
      }),
    );
    expect(connection.getSlotSnapshot("slot-1")).toMatchObject({
      connectionState: "STALE",
      attempt: 1,
      reasonCode: "PROVIDER_DISCONNECTED",
      lastEventAt: "2026-08-13T09:59:30Z",
      candles: [fiveMinuteCandle(10, 0, { closed: true })],
    });

    socket.receive(
      stateEvent("evt-reconnecting", FIVE_MINUTES, "RECONNECTING", {
        attempt: 2,
        retryAfterMs: 2034,
        lastEventAt: "2026-08-13T09:59:30Z",
      }),
    );
    expect(connection.getSlotSnapshot("slot-1")).toMatchObject({
      connectionState: "RECONNECTING",
      attempt: 2,
      retryAfterMs: 2034,
    });

    socket.receive(stateEvent("evt-live", FIVE_MINUTES, "LIVE", { attempt: 3 }));
    expect(connection.getSlotSnapshot("slot-1")).toMatchObject({
      connectionState: "LIVE",
      attempt: 3,
    });
  });

  it("merges recovered gap candles in order while reconnecting and drops older identities after LIVE", () => {
    const { connection, socket } = socketHarness(4);
    const subscription = connection.subscribe({
      slotId: "slot-1",
      generation: 1,
      selection: FIVE_MINUTES,
      onSnapshot: vi.fn(),
    });
    socket.open();
    subscription.acceptHistory([
      fiveMinuteCandle(10, 0, { closed: true }),
      fiveMinuteCandle(10, 30, { closed: true }),
      fiveMinuteCandle(10, 35),
    ]);
    const openTimes = () =>
      connection
        .getSlotSnapshot("slot-1")
        ?.candles.map((item) => item.openTime);

    socket.receive(
      stateEvent("evt-stale", FIVE_MINUTES, "STALE", {
        attempt: 1,
        reasonCode: "PROVIDER_DISCONNECTED",
      }),
    );
    socket.receive(
      candleEvent(
        "evt-recovered",
        FIVE_MINUTES,
        1,
        fiveMinuteCandle(10, 25, { closed: true }),
      ),
    );
    expect(openTimes()).toEqual([
      "2026-08-13T10:00:00Z",
      "2026-08-13T10:25:00Z",
      "2026-08-13T10:30:00Z",
      "2026-08-13T10:35:00Z",
    ]);

    socket.receive(
      candleEvent(
        "evt-regression",
        FIVE_MINUTES,
        2,
        fiveMinuteCandle(10, 30, { closed: false }),
      ),
    );
    expect(
      connection
        .getSlotSnapshot("slot-1")
        ?.candles.find((item) => item.openTime === "2026-08-13T10:30:00Z"),
    ).toMatchObject({ closed: true });

    socket.receive(stateEvent("evt-live", FIVE_MINUTES, "LIVE", { attempt: 2 }));
    socket.receive(
      candleEvent(
        "evt-old-after-live",
        FIVE_MINUTES,
        3,
        fiveMinuteCandle(10, 20, { closed: true }),
      ),
    );
    expect(openTimes()).toEqual([
      "2026-08-13T10:00:00Z",
      "2026-08-13T10:25:00Z",
      "2026-08-13T10:30:00Z",
      "2026-08-13T10:35:00Z",
    ]);
  });
});

describe("connection recovery lifecycle", () => {
  it("marks only the affected slot stale while a healthy sibling stays live", async () => {
    const { hook, socket } = hookHarness(["5m", "1h"]);
    await settle();
    receive(socket, stateEvent("evt-live-5m", FIVE_MINUTES, "LIVE", { attempt: 1 }));
    receive(
      socket,
      stateEvent("evt-live-1h", ONE_HOUR, "LIVE", { attempt: 1, slotIds: ["slot-2"] }),
    );

    const siblingBefore = hook.result.current.slots[1];
    receive(
      socket,
      stateEvent("evt-stale", FIVE_MINUTES, "STALE", {
        attempt: 1,
        reasonCode: "PROVIDER_DISCONNECTED",
        lastEventAt: "2026-08-13T09:59:30Z",
      }),
    );

    expect(hook.result.current.slots[0]).toMatchObject({
      slotId: "slot-1",
      timeframe: "5m",
      connectionState: "STALE",
      attempt: 1,
      lastEventAt: "2026-08-13T09:59:30Z",
    });
    expect(hook.result.current.slots[1]).toBe(siblingBefore);
    expect(hook.result.current.slots[1]).toMatchObject({
      slotId: "slot-2",
      timeframe: "1h",
      connectionState: "LIVE",
    });
  });

  it("shows reconnecting feedback, merges recovered candles, and never marks LIVE itself", async () => {
    const { hook, socket } = hookHarness(["5m"]);
    await settle();
    receive(socket, stateEvent("evt-live", FIVE_MINUTES, "LIVE", { attempt: 1 }));

    receive(
      socket,
      stateEvent("evt-reconnecting", FIVE_MINUTES, "RECONNECTING", {
        attempt: 2,
        retryAfterMs: 2034,
        lastEventAt: "2026-08-13T09:59:30Z",
        reasonCode: "PROVIDER_DISCONNECTED",
      }),
    );
    expect(hook.result.current.slots[0]).toMatchObject({
      connectionState: "RECONNECTING",
      attempt: 2,
      retryAfterMs: 2034,
      lastEventAt: "2026-08-13T09:59:30Z",
    });

    receive(
      socket,
      candleEvent(
        "evt-recovered-later",
        FIVE_MINUTES,
        1,
        fiveMinuteCandle(10, 10, { closed: true }),
      ),
    );
    receive(
      socket,
      candleEvent(
        "evt-recovered-gap",
        FIVE_MINUTES,
        2,
        fiveMinuteCandle(10, 5, { closed: true }),
      ),
    );
    expect(
      hook.result.current.slots[0].candles.map((item) => item.openTime),
    ).toEqual([
      "2026-08-13T10:00:00Z",
      "2026-08-13T10:05:00Z",
      "2026-08-13T10:10:00Z",
    ]);
    expect(hook.result.current.slots[0].connectionState).toBe("RECONNECTING");

    receive(
      socket,
      stateEvent("evt-live-again", FIVE_MINUTES, "LIVE", { attempt: 3 }),
    );
    expect(hook.result.current.slots[0]).toMatchObject({
      connectionState: "LIVE",
      attempt: 3,
    });
  });

  it("isolates exhaustion to the affected slot and manual retry resets the cycle", async () => {
    const { hook, socket, retry } = hookHarness(["5m", "1h"]);
    await settle();
    receive(socket, stateEvent("evt-live-5m", FIVE_MINUTES, "LIVE", { attempt: 1 }));
    receive(
      socket,
      stateEvent("evt-live-1h", ONE_HOUR, "LIVE", { attempt: 1, slotIds: ["slot-2"] }),
    );

    receive(
      socket,
      stateEvent("evt-exhausted", FIVE_MINUTES, "ERROR", {
        attempt: 8,
        reasonCode: "MARKET_RECOVERY_EXHAUSTED",
        lastEventAt: "2026-08-13T09:59:30Z",
      }),
    );
    expect(hook.result.current.slots[0]).toMatchObject({
      connectionState: "ERROR",
      attempt: 8,
      error: {
        code: "MARKET_RECOVERY_EXHAUSTED",
        retryable: true,
      },
    });
    expect(hook.result.current.slots[1]).toMatchObject({
      connectionState: "LIVE",
      timeframe: "1h",
    });

    act(() => hook.result.current.retrySlot("slot-1"));
    expect(retry).toHaveBeenCalledWith("slot-1");
    const commands = socket.sent.map((message) =>
      marketDataCommandSchema.parse(JSON.parse(message) as unknown),
    );
    expect(commands.some((command) => command.eventType === "RETRY_MARKET_DATA")).toBe(
      true,
    );
    const retryCommand = commands.find(
      (command) => command.eventType === "RETRY_MARKET_DATA",
    );
    expect(retryCommand?.payload).toMatchObject({ slotId: "slot-1" });
    expect(hook.result.current.slots[0]).toMatchObject({
      connectionState: "RECONNECTING",
      error: undefined,
      retrySequence: 1,
    });

    receive(
      socket,
      stateEvent("evt-retry-stale", FIVE_MINUTES, "STALE", {
        attempt: 1,
        reasonCode: "PROVIDER_DISCONNECTED",
      }),
    );
    receive(socket, stateEvent("evt-retry-live", FIVE_MINUTES, "LIVE", { attempt: 2 }));
    expect(hook.result.current.slots[0]).toMatchObject({
      connectionState: "LIVE",
      error: undefined,
    });
    expect(hook.result.current.slots[1]).toMatchObject({
      connectionState: "LIVE",
    });
  });
});

describe("recovery presentation and retry action", () => {
  function slotState(
    connectionState: ChartSlotState["connectionState"],
    extra: Partial<ChartSlotState> = {},
  ): ChartSlotState {
    return {
      slotId: "slot-1",
      pair: "BTCUSDT",
      timeframe: "5m",
      generation: 1,
      candles: [fiveMinuteCandle(10, 0, { closed: true })],
      connectionState,
      retrySequence: 0,
      ...extra,
    };
  }

  it("marks stale data visibly old with its last event time", () => {
    render(
      <ChartSlot
        slot={slotState("STALE", {
          lastEventAt: "2026-08-13T09:59:30Z",
          attempt: 1,
        })}
        timeframes={["5m", "1h"]}
        onTimeframeChange={vi.fn()}
        onRemove={vi.fn()}
        onRetry={vi.fn()}
      />,
    );
    expect(screen.getByText("Stale")).toBeInTheDocument();
    expect(screen.getByText(/2026-08-13T09:59:30Z/)).toBeInTheDocument();
  });

  it("shows recovery attempt feedback while reconnecting", () => {
    render(
      <ChartSlot
        slot={slotState("RECONNECTING", { attempt: 2 })}
        timeframes={["5m", "1h"]}
        onTimeframeChange={vi.fn()}
        onRemove={vi.fn()}
        onRetry={vi.fn()}
      />,
    );
    expect(screen.getByText("Reconnecting")).toBeInTheDocument();
    expect(screen.getByText(/attempt 2/)).toBeInTheDocument();
  });

  it("exposes the manual retry action for exhausted recovery and wires it to the slot", () => {
    const onRetry = vi.fn();
    render(
      <ChartSlot
        slot={slotState("ERROR", {
          attempt: 8,
          error: {
            code: "MARKET_RECOVERY_EXHAUSTED",
            message: "Automatic recovery exhausted. Retry to resume live data.",
            retryable: true,
          },
        })}
        timeframes={["5m", "1h"]}
        onTimeframeChange={vi.fn()}
        onRemove={vi.fn()}
        onRetry={onRetry}
      />,
    );
    expect(screen.getByText("Error")).toBeInTheDocument();
    expect(
      screen.getByText(/Automatic recovery exhausted/),
    ).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: /retry market data/i }),
    );
    expect(onRetry).toHaveBeenCalledWith("slot-1");
  });
});