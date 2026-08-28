import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen } from "@testing-library/react";
import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";

import { AppProviders } from "../../src/app/providers/AppProviders";
import { MarketRoute } from "../../src/app/routes/market";
import * as marketDataApiModule from "../../src/features/market-chart/api/marketDataApi";
import type {
  CandleRange,
  MarketSelection,
  TimeRange,
} from "../../src/features/market-chart/types";

type HistoryQueryInput = {
  selection: MarketSelection;
  range: TimeRange;
  limit: number;
  generation: number;
};

type HistoryQueryOptions = {
  queryKey: readonly unknown[];
  queryFn(context: { signal: AbortSignal }): Promise<CandleRange>;
};

type ExpectedHistoryQueryExports = {
  marketHistoryQueryKey(input: HistoryQueryInput): readonly unknown[];
  createMarketHistoryQueryOptions(
    input: HistoryQueryInput & {
      api: {
        getCandles(request: {
          selection: MarketSelection;
          range: TimeRange;
          limit: number;
          signal: AbortSignal;
        }): Promise<CandleRange>;
      };
    },
  ): HistoryQueryOptions;
};

const selection: MarketSelection = {
  provider: "BINANCE",
  pair: "BTCUSDT",
  timeframe: "5m",
};

const range: TimeRange = {
  startTime: "2026-08-13T09:00:00Z",
  endTime: "2026-08-13T10:00:00Z",
};

const historyInput: HistoryQueryInput = {
  selection,
  range,
  limit: 500,
  generation: 7,
};

const emptyRange: CandleRange = {
  schemaVersion: "1",
  selection,
  range,
  completeness: "EMPTY",
  missingRanges: [range],
  candles: [],
};

function expectedHistoryQueryExports(): ExpectedHistoryQueryExports {
  const candidate = marketDataApiModule as unknown as Partial<ExpectedHistoryQueryExports>;
  if (
    typeof candidate.marketHistoryQueryKey !== "function" ||
    typeof candidate.createMarketHistoryQueryOptions !== "function"
  ) {
    throw new Error(
      "Expected marketDataApi to export marketHistoryQueryKey and createMarketHistoryQueryOptions.",
    );
  }

  return candidate as ExpectedHistoryQueryExports;
}

describe("TanStack Query history seam", () => {
  it("builds a stable versioned key from selection, range, limit, and generation", () => {
    const { marketHistoryQueryKey } = expectedHistoryQueryExports();

    const first = marketHistoryQueryKey(historyInput);
    const equalValues = marketHistoryQueryKey({
      selection: { ...selection },
      range: { ...range },
      limit: 500,
      generation: 7,
    });

    expect(first).toEqual([
      "market-data",
      "history",
      "1",
      { provider: "BINANCE", pair: "BTCUSDT", timeframe: "5m" },
      {
        startTime: "2026-08-13T09:00:00Z",
        endTime: "2026-08-13T10:00:00Z",
      },
      500,
      7,
    ]);
    expect(equalValues).toEqual(first);
    expect(
      marketHistoryQueryKey({ ...historyInput, generation: 8 }),
    ).not.toEqual(first);
  });

  it("forwards TanStack Query's AbortSignal to MarketDataApi", async () => {
    const { createMarketHistoryQueryOptions } = expectedHistoryQueryExports();
    const getCandles = vi.fn(async () => emptyRange);
    const options = createMarketHistoryQueryOptions({
      api: { getCandles },
      ...historyInput,
    });
    const signal = new AbortController().signal;

    await expect(options.queryFn({ signal })).resolves.toEqual(emptyRange);
    expect(options.queryKey).toEqual(
      expectedHistoryQueryExports().marketHistoryQueryKey(historyInput),
    );
    expect(getCandles).toHaveBeenCalledOnce();
    expect(getCandles).toHaveBeenCalledWith({
      selection,
      range,
      limit: 500,
      signal,
    });
  });

  it("deduplicates concurrent equal requests but isolates pair and generation changes", async () => {
    const { createMarketHistoryQueryOptions } = expectedHistoryQueryExports();
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    let release!: () => void;
    const pending = new Promise<void>((resolve) => {
      release = resolve;
    });
    const getCandles = vi.fn(async (request: HistoryQueryInput) => {
      await pending;
      return { ...emptyRange, selection: request.selection };
    });
    const equalInput = { api: { getCandles }, ...historyInput };
    const first = queryClient.fetchQuery(createMarketHistoryQueryOptions(equalInput));
    const second = queryClient.fetchQuery(
      createMarketHistoryQueryOptions({
        ...equalInput,
        selection: { ...selection },
        range: { ...range },
      }),
    );

    expect(getCandles).toHaveBeenCalledOnce();
    release();
    await Promise.all([first, second]);

    await queryClient.fetchQuery(
      createMarketHistoryQueryOptions({
        ...historyInput,
        selection: { ...selection, pair: "ETHUSDT" },
        api: { getCandles },
      }),
    );
    await queryClient.fetchQuery(
      createMarketHistoryQueryOptions({
        ...historyInput,
        generation: historyInput.generation + 1,
        api: { getCandles },
      }),
    );

    expect(getCandles).toHaveBeenCalledTimes(3);
    expect(getCandles.mock.calls.map(([request]) => request.selection.pair)).toEqual([
      "BTCUSDT",
      "ETHUSDT",
      "BTCUSDT",
    ]);
  });
});

describe("app query-provider composition", () => {
  it("composes AppProviders with TanStack Query's QueryClientProvider", () => {
    const providersSource = readFileSync(
      resolve("src/app/providers/AppProviders.tsx"),
      "utf8",
    );

    expect(providersSource).toMatch(
      /from\s+["']@tanstack\/react-query["']/,
    );
    expect(providersSource).toMatch(/<QueryClientProvider(?:\s|>)/);
  });

  it("preserves the accepted MarketRoute chart contract inside AppProviders", () => {
    render(
      <AppProviders>
        <MarketRoute
          initialTimeframes={["5m"]}
          createSlotId={() => "slot-query"}
        />
      </AppProviders>,
    );

    expect(screen.getByTestId("chart-grid")).toBeVisible();
    expect(document.getElementById("chart-btcusdt-5m-slot-query")).toBeVisible();
    expect(document.getElementById("select-pair")).toHaveValue("BTCUSDT");
  });
});
