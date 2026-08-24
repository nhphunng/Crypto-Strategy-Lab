import { describe, expect, it, vi } from "vitest";

import {
  MarketDataApiError,
  createMarketDataApi,
} from "../../src/features/market-chart/api/marketDataApi";

const response = {
  success: true,
  message: "Historical Candles loaded.",
  timestamp: "2026-08-13T10:05:00Z",
  requestId: "req-history",
  data: {
    schemaVersion: "1",
    selection: { provider: "BINANCE", pair: "BTCUSDT", timeframe: "5m" },
    range: {
      startTime: "2026-08-13T10:00:00Z",
      endTime: "2026-08-13T10:05:00Z",
    },
    completeness: "EMPTY",
    missingRanges: [
      {
        startTime: "2026-08-13T10:00:00Z",
        endTime: "2026-08-13T10:05:00Z",
      },
    ],
    candles: [],
  },
} as const;

describe("bounded market-data history client", () => {
  it("encodes the accepted explicit range and validates the response", async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify(response), { status: 200 }));
    const api = createMarketDataApi({ baseUrl: "http://localhost:8000", fetcher });

    const result = await api.getCandles({
      selection: response.data.selection,
      range: response.data.range,
      limit: 500,
    });

    expect(result).toEqual(response.data);
    const requested = new URL(String(fetcher.mock.calls[0][0]));
    expect(requested.pathname).toBe("/api/v1/market-data/candles");
    expect(Object.fromEntries(requested.searchParams)).toMatchObject({
      provider: "BINANCE",
      pair: "BTCUSDT",
      timeframe: "5m",
      startTime: response.data.range.startTime,
      endTime: response.data.range.endTime,
      limit: "500",
      schemaVersion: "1",
    });
  });

  it("rejects unbounded requests before fetch and exposes typed REST errors", async () => {
    const fetcher = vi.fn(async () =>
      new Response(
        JSON.stringify({
          success: false,
          message: "The requested range is too large.",
          error: { code: "MARKET_RANGE_TOO_LARGE", retryable: false, details: null },
          timestamp: "2026-08-13T10:05:00Z",
          requestId: "req-error",
        }),
        { status: 422 },
      ),
    );
    const api = createMarketDataApi({ fetcher });

    await expect(
      api.getCandles({
        selection: response.data.selection,
        range: response.data.range,
        limit: 1_001,
      }),
    ).rejects.toThrow("between one and 1,000");
    expect(fetcher).not.toHaveBeenCalled();

    await expect(
      api.getCandles({
        selection: response.data.selection,
        range: response.data.range,
        limit: 500,
      }),
    ).rejects.toMatchObject<Partial<MarketDataApiError>>({
      code: "MARKET_RANGE_TOO_LARGE",
      retryable: false,
      requestId: "req-error",
    });
  });
});
