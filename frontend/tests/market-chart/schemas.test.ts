import { describe, expect, it } from "vitest";

import {
  MarketDataSchemaError,
  candleRangeEnvelopeSchema,
  marketDataCommandSchema,
  marketDataEventSchema,
  marketDataRestErrorEnvelopeSchema,
  parseCandle,
  parseMarketSelection,
} from "../../src/features/market-chart/schemas";

const selection = {
  provider: "BINANCE",
  pair: "BTCUSDT",
  timeframe: "5m",
} as const;

const candle = {
  ...selection,
  openTime: "2026-08-13T10:00:00Z",
  closeTime: "2026-08-13T10:04:59.999Z",
  open: "67234.12",
  high: "67250.00",
  low: "67220.50",
  close: "67241.30",
  volume: "12.50",
  closed: false,
  receivedAt: "2026-08-13T10:00:01Z",
} as const;

describe("market chart REST contract schemas", () => {
  it("parses the accepted provider-neutral selection and Candle", () => {
    expect(parseMarketSelection(selection)).toEqual(selection);
    expect(parseCandle(candle)).toEqual(candle);
  });

  it.each([
    [{ ...candle, open: 67234.12 }, "$.open"],
    [{ ...candle, close: "0" }, "$.close"],
    [{ ...candle, high: "67200" }, "$.high"],
    [{ ...candle, receivedAt: "2026-08-13T17:00:01+07:00" }, "$.receivedAt"],
    [{ ...candle, providerChannel: "btcusdt@kline_5m" }, "$"],
  ])("rejects invalid or provider-specific Candle data", (value, path) => {
    expect(() => parseCandle(value)).toThrow(MarketDataSchemaError);
    expect(() => parseCandle(value)).toThrow(path);
  });

  it("validates bounded chronological history and its success envelope", () => {
    const result = candleRangeEnvelopeSchema.parse({
      success: true,
      message: "Historical candles loaded.",
      timestamp: "2026-08-13T10:05:00Z",
      requestId: "req-history-1",
      data: {
        schemaVersion: "1",
        selection,
        range: {
          startTime: "2026-08-13T10:00:00Z",
          endTime: "2026-08-13T10:05:00Z",
        },
        completeness: "COMPLETE",
        missingRanges: [],
        candles: [candle],
      },
    });

    expect(result.data.candles).toHaveLength(1);
    expect(result.data.completeness).toBe("COMPLETE");
  });

  it("rejects an undocumented or lowercase REST error code", () => {
    expect(() =>
      marketDataRestErrorEnvelopeSchema.parse({
        success: false,
        message: "Selection is invalid.",
        error: { code: "market_pair_unsupported", retryable: false, details: null },
        timestamp: "2026-08-13T10:05:00Z",
        requestId: "req-error-1",
      }),
    ).toThrow("$.error.code");
  });
});

describe("market chart WebSocket contract schemas", () => {
  it("parses each slot-scoped command and rejects unsupported versions", () => {
    expect(
      marketDataCommandSchema.parse({
        eventType: "SUBSCRIBE_MARKET_DATA",
        version: "1",
        requestId: "req-01",
        occurredAt: "2026-08-13T10:00:00Z",
        payload: { slotId: "slot-1", selection },
      }).eventType,
    ).toBe("SUBSCRIBE_MARKET_DATA");

    expect(() =>
      marketDataCommandSchema.parse({
        eventType: "RETRY_MARKET_DATA",
        version: "2",
        requestId: "req-02",
        occurredAt: "2026-08-13T10:00:00Z",
        payload: { slotId: "slot-1" },
      }),
    ).toThrow("$.version");
  });

  it("parses typed Candle events and rejects RELEASED as a wire state", () => {
    const update = marketDataEventSchema.parse({
      eventType: "CANDLE_UPDATED",
      version: "1",
      eventId: "evt-201",
      occurredAt: "2026-08-13T10:00:01Z",
      payload: { selection, revision: 7, candle },
    });

    expect(update.eventType).toBe("CANDLE_UPDATED");

    expect(() =>
      marketDataEventSchema.parse({
        eventType: "SUBSCRIPTION_STATE_CHANGED",
        version: "1",
        eventId: "evt-202",
        occurredAt: "2026-08-13T10:00:02Z",
        payload: { slotIds: ["slot-1"], selection, state: "RELEASED", attempt: 0 },
      }),
    ).toThrow("$.payload.state");
  });

  it("requires the documented reconnect attempt and permits connection-level errors", () => {
    expect(() =>
      marketDataEventSchema.parse({
        eventType: "SUBSCRIPTION_STATE_CHANGED",
        version: "1",
        eventId: "evt-state-missing-attempt",
        occurredAt: "2026-08-13T10:00:02Z",
        payload: { slotIds: ["slot-1"], selection, state: "LIVE" },
      }),
    ).toThrow("$.payload.attempt");

    const connectionError = marketDataEventSchema.parse({
      eventType: "MARKET_DATA_ERROR",
      version: "1",
      eventId: "evt-connection-error",
      occurredAt: "2026-08-13T10:00:03Z",
      payload: {
        code: "MARKET_EVENT_VERSION_UNSUPPORTED",
        message: "Unsupported realtime contract version.",
        retryable: false,
      },
    });

    expect(connectionError.eventType).toBe("MARKET_DATA_ERROR");
    expect(connectionError.payload.slotId).toBeUndefined();
  });

  it("accepts only documented uppercase realtime error codes", () => {
    const event = marketDataEventSchema.parse({
      eventType: "MARKET_DATA_ERROR",
      version: "1",
      eventId: "evt-203",
      requestId: "req-03",
      occurredAt: "2026-08-13T10:00:03Z",
      payload: {
        slotId: "slot-5",
        code: "MARKET_SUBSCRIPTION_LIMIT_REACHED",
        message: "A dashboard can use at most four chart slots.",
        retryable: false,
      },
    });

    expect(event.payload.code).toBe("MARKET_SUBSCRIPTION_LIMIT_REACHED");
    expect(() =>
      marketDataEventSchema.parse({
        ...event,
        payload: { ...event.payload, code: "INTERNAL_STACK_TRACE" },
      }),
    ).toThrow("$.payload.code");
  });
});
