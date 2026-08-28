import { describe, expect, it, vi } from "vitest";

import { marketDataCommandSchema } from "../../src/features/market-chart/schemas";
import type {
  Candle,
  CandleUpdatedEvent,
  MarketSelection,
} from "../../src/features/market-chart/types";
import {
  createMarketDataSocket,
  parseMarketDataSocketMessage,
} from "../../src/features/market-chart/realtime/marketDataSocket";

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

function candle(
  selection: MarketSelection,
  openTime: string,
  closeTime: string,
  options: Partial<Pick<Candle, "close" | "closed" | "receivedAt">> = {},
): Candle {
  const close = options.close ?? "101.00";
  return {
    ...selection,
    openTime,
    closeTime,
    open: "100.00",
    high: "103.00",
    low: "99.00",
    close,
    volume: "12.50",
    closed: options.closed ?? false,
    receivedAt: options.receivedAt ?? "2026-08-13T10:00:01Z",
  };
}

function candleEvent(
  eventId: string,
  selection: MarketSelection,
  revision: number,
  value: Candle,
  slotGenerations: Record<string, number> = {
    "slot-1": 1,
    "slot-2": 1,
    "slot-3": 1,
  },
): CandleUpdatedEvent {
  return {
    eventType: "CANDLE_UPDATED",
    version: "1",
    eventId,
    occurredAt: value.receivedAt,
    payload: { selection, revision, candle: value, slotGenerations },
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

function setup(maxCandles = 3) {
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

describe("realtime market-data boundary", () => {
  it("parses a typed event and rejects malformed JSON or unsupported versions", () => {
    const value = candle(
      FIVE_MINUTES,
      "2026-08-13T10:00:00Z",
      "2026-08-13T10:04:59.999Z",
    );

    expect(
      parseMarketDataSocketMessage(
        JSON.stringify(candleEvent("evt-1", FIVE_MINUTES, 1, value)),
      ),
    ).toMatchObject({ eventType: "CANDLE_UPDATED", eventId: "evt-1" });
    expect(() => parseMarketDataSocketMessage("not-json")).toThrow();
    expect(() =>
      parseMarketDataSocketMessage(
        JSON.stringify({
          ...candleEvent("evt-version", FIVE_MINUTES, 1, value),
          version: "2",
        }),
      ),
    ).toThrow("$.version");
  });

  it("routes a selection update to every matching slot and not to unrelated slots", () => {
    const { connection, socket } = setup();
    const firstSlot = vi.fn();
    const sharedSelectionSlot = vi.fn();
    const otherSelectionSlot = vi.fn();

    const firstSubscription = connection.subscribe({
      slotId: "slot-1",
      generation: 1,
      selection: FIVE_MINUTES,
      onSnapshot: firstSlot,
    });
    const sharedSubscription = connection.subscribe({
      slotId: "slot-2",
      generation: 1,
      selection: FIVE_MINUTES,
      onSnapshot: sharedSelectionSlot,
    });
    const otherSubscription = connection.subscribe({
      slotId: "slot-3",
      generation: 1,
      selection: ONE_HOUR,
      onSnapshot: otherSelectionSlot,
    });
    socket.open();
    firstSubscription.acceptHistory([]);
    sharedSubscription.acceptHistory([]);
    otherSubscription.acceptHistory([]);

    const commands = socket.sent.map((message) =>
      marketDataCommandSchema.parse(JSON.parse(message) as unknown),
    );
    expect(commands).toHaveLength(3);
    expect(commands.map((command) => command.payload.slotId)).toEqual([
      "slot-1",
      "slot-2",
      "slot-3",
    ]);

    const callsBefore = {
      first: firstSlot.mock.calls.length,
      shared: sharedSelectionSlot.mock.calls.length,
      other: otherSelectionSlot.mock.calls.length,
    };
    socket.receive(
      candleEvent(
        "evt-shared",
        FIVE_MINUTES,
        1,
        candle(
          FIVE_MINUTES,
          "2026-08-13T10:00:00Z",
          "2026-08-13T10:04:59.999Z",
        ),
      ),
    );

    expect(firstSlot).toHaveBeenCalledTimes(callsBefore.first + 1);
    expect(sharedSelectionSlot).toHaveBeenCalledTimes(callsBefore.shared + 1);
    expect(otherSelectionSlot).toHaveBeenCalledTimes(callsBefore.other);
    expect(connection.getSlotSnapshot("slot-1")?.candles).toHaveLength(1);
    expect(connection.getSlotSnapshot("slot-2")?.candles).toHaveLength(1);
    expect(connection.getSlotSnapshot("slot-3")?.candles).toEqual([]);
  });

  it("rejects a late same-selection event from an older subscription generation", () => {
    const { connection, socket } = setup();
    const onSnapshot = vi.fn();
    const first = connection.subscribe({
      slotId: "slot-1",
      generation: 1,
      selection: FIVE_MINUTES,
      onSnapshot,
    });
    first.acceptHistory([]);
    const current = connection.subscribe({
      slotId: "slot-1",
      generation: 3,
      selection: FIVE_MINUTES,
      onSnapshot,
    });
    current.acceptHistory([]);
    socket.open();

    socket.receive(
      candleEvent(
        "evt-old-generation",
        FIVE_MINUTES,
        1,
        candle(
          FIVE_MINUTES,
          "2026-08-13T10:00:00Z",
          "2026-08-13T10:04:59.999Z",
        ),
        { "slot-1": 1 },
      ),
    );
    expect(connection.getSlotSnapshot("slot-1")?.candles).toEqual([]);

    socket.receive(
      candleEvent(
        "evt-current-generation",
        FIVE_MINUTES,
        1,
        candle(
          FIVE_MINUTES,
          "2026-08-13T10:05:00Z",
          "2026-08-13T10:09:59.999Z",
        ),
        { "slot-1": 3 },
      ),
    );
    expect(connection.getSlotSnapshot("slot-1")?.candles).toHaveLength(1);
  });
});

describe("bounded realtime Candle merge", () => {
  it("buffers live events until history arrives, then deduplicates and closes in place", () => {
    const { connection, socket } = setup(3);
    const onSnapshot = vi.fn();
    const subscription = connection.subscribe({
      slotId: "slot-1",
      generation: 4,
      selection: FIVE_MINUTES,
      onSnapshot,
    });
    socket.open();

    const currentOpen = candle(
      FIVE_MINUTES,
      "2026-08-13T10:05:00Z",
      "2026-08-13T10:09:59.999Z",
      { close: "101.00" },
    );
    socket.receive(
      candleEvent("evt-open", FIVE_MINUTES, 1, currentOpen, { "slot-1": 4 }),
    );
    expect(connection.getSlotSnapshot("slot-1")?.candles).toEqual([]);

    const historical = candle(
      FIVE_MINUTES,
      "2026-08-13T10:00:00Z",
      "2026-08-13T10:04:59.999Z",
      { closed: true },
    );
    expect(subscription.acceptHistory([historical])).toBe(true);
    expect(
      connection.getSlotSnapshot("slot-1")?.candles.map((item) => item.openTime),
    ).toEqual([historical.openTime, currentOpen.openTime]);

    const callsAfterBootstrap = onSnapshot.mock.calls.length;
    socket.receive(
      candleEvent("evt-open", FIVE_MINUTES, 1, currentOpen, { "slot-1": 4 }),
    );
    expect(onSnapshot).toHaveBeenCalledTimes(callsAfterBootstrap);

    const closed = {
      ...currentOpen,
      close: "102.00",
      closed: true,
      receivedAt: "2026-08-13T10:10:00Z",
    } satisfies Candle;
    socket.receive(
      candleEvent("evt-closed", FIVE_MINUTES, 2, closed, { "slot-1": 4 }),
    );

    const snapshot = connection.getSlotSnapshot("slot-1");
    expect(snapshot?.candles).toHaveLength(2);
    expect(snapshot?.candles.at(-1)).toMatchObject({
      openTime: currentOpen.openTime,
      close: "102.00",
      closed: true,
    });

    socket.receive(
      candleEvent("evt-regression", FIVE_MINUTES, 3, {
        ...currentOpen,
        close: "99.50",
        closed: false,
        receivedAt: "2026-08-13T10:10:01Z",
      }, { "slot-1": 4 }),
    );
    expect(connection.getSlotSnapshot("slot-1")?.candles.at(-1)).toEqual(closed);
  });

  it("keeps the newest bounded chronological series and ignores older live identities", () => {
    const { connection, socket } = setup(2);
    const subscription = connection.subscribe({
      slotId: "slot-1",
      generation: 1,
      selection: FIVE_MINUTES,
      onSnapshot: vi.fn(),
    });
    socket.open();

    const first = candle(
      FIVE_MINUTES,
      "2026-08-13T10:00:00Z",
      "2026-08-13T10:04:59.999Z",
      { closed: true },
    );
    const second = candle(
      FIVE_MINUTES,
      "2026-08-13T10:05:00Z",
      "2026-08-13T10:09:59.999Z",
      { closed: true },
    );
    const third = candle(
      FIVE_MINUTES,
      "2026-08-13T10:10:00Z",
      "2026-08-13T10:14:59.999Z",
    );
    subscription.acceptHistory([first, second]);
    socket.receive(candleEvent("evt-third", FIVE_MINUTES, 1, third));

    expect(
      connection.getSlotSnapshot("slot-1")?.candles.map((item) => item.openTime),
    ).toEqual([second.openTime, third.openTime]);

    socket.receive(candleEvent("evt-old", FIVE_MINUTES, 99, first));
    expect(
      connection.getSlotSnapshot("slot-1")?.candles.map((item) => item.openTime),
    ).toEqual([second.openTime, third.openTime]);
  });
});

describe("slot generation safety", () => {
  it("rejects late history and live events from a replaced generation", () => {
    const { connection, socket } = setup();
    const oldSnapshots = vi.fn();
    const currentSnapshots = vi.fn();
    const oldSubscription = connection.subscribe({
      slotId: "slot-1",
      generation: 1,
      selection: FIVE_MINUTES,
      onSnapshot: oldSnapshots,
    });
    socket.open();

    const currentSubscription = connection.subscribe({
      slotId: "slot-1",
      generation: 2,
      selection: ONE_HOUR,
      onSnapshot: currentSnapshots,
    });
    expect(currentSubscription.acceptHistory([])).toBe(true);

    const lateHistory = candle(
      FIVE_MINUTES,
      "2026-08-13T10:00:00Z",
      "2026-08-13T10:04:59.999Z",
      { closed: true },
    );
    expect(oldSubscription.acceptHistory([lateHistory])).toBe(false);
    oldSubscription.release();

    socket.receive(candleEvent("evt-old-generation", FIVE_MINUTES, 1, lateHistory));
    expect(connection.getSlotSnapshot("slot-1")).toMatchObject({
      slotId: "slot-1",
      generation: 2,
      selection: ONE_HOUR,
      candles: [],
    });

    const current = candle(
      ONE_HOUR,
      "2026-08-13T10:00:00Z",
      "2026-08-13T10:59:59.999Z",
    );
    socket.receive(
      candleEvent("evt-current-generation", ONE_HOUR, 1, current, { "slot-1": 2 }),
    );
    expect(connection.getSlotSnapshot("slot-1")?.candles).toEqual([current]);
    expect(currentSnapshots).toHaveBeenCalled();
  });
});
