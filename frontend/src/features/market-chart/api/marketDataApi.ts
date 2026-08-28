import { queryOptions } from "@tanstack/react-query";

import {
  candleRangeEnvelopeSchema,
  marketDimensionsEnvelopeSchema,
  marketDataRestErrorEnvelopeSchema,
} from "../schemas";
import {
  MARKET_DATA_SCHEMA_VERSION,
  type CandleRange,
  type MarketDimensions,
  type MarketDataRestErrorCode,
  type MarketSelection,
  type TimeRange,
} from "../types";

export type HistoricalCandleRequest = {
  selection: MarketSelection;
  range: TimeRange;
  limit?: number;
  signal?: AbortSignal;
};

export type MarketHistoryQueryInput = {
  selection: MarketSelection;
  range: TimeRange;
  limit: number;
  generation: number;
};

export function marketDimensionsQueryKey() {
  return ["market-data", "dimensions", MARKET_DATA_SCHEMA_VERSION] as const;
}

export function marketHistoryQueryKey(input: MarketHistoryQueryInput) {
  return [
    "market-data",
    "history",
    MARKET_DATA_SCHEMA_VERSION,
    input.selection,
    input.range,
    input.limit,
    input.generation,
  ] as const;
}

export type CreateMarketDataApiOptions = {
  baseUrl?: string;
  fetcher?: typeof fetch;
};

export class MarketDataApiError extends Error {
  readonly code: MarketDataRestErrorCode;
  readonly retryable: boolean;
  readonly requestId: string;
  readonly details?: Record<string, unknown>;

  constructor(options: {
    code: MarketDataRestErrorCode;
    message: string;
    retryable: boolean;
    requestId: string;
    details?: Record<string, unknown>;
  }) {
    super(options.message);
    this.name = "MarketDataApiError";
    this.code = options.code;
    this.retryable = options.retryable;
    this.requestId = options.requestId;
    this.details = options.details;
  }
}

export class MarketDataApi {
  private readonly baseUrl: string;
  private readonly fetcher: typeof fetch;

  constructor(options: CreateMarketDataApiOptions = {}) {
    this.baseUrl = options.baseUrl ?? globalThis.location?.origin ?? "http://localhost";
    this.fetcher = options.fetcher ?? globalThis.fetch.bind(globalThis);
  }

  async getDimensions(signal?: AbortSignal): Promise<MarketDimensions> {
    const url = new URL("/api/v1/market-data/dimensions", this.baseUrl);
    const response = await this.fetcher(url, {
      method: "GET",
      headers: { Accept: "application/json" },
      signal,
    });
    const payload = (await response.json()) as unknown;
    if (response.ok) {
      return marketDimensionsEnvelopeSchema.parse(payload).data;
    }

    throwMarketDataApiError(payload);
  }

  async getCandles(request: HistoricalCandleRequest): Promise<CandleRange> {
    const limit = request.limit ?? 500;
    if (!Number.isInteger(limit) || limit < 1 || limit > 1_000) {
      throw new Error("limit must be between one and 1,000 Candles");
    }
    const url = new URL("/api/v1/market-data/candles", this.baseUrl);
    url.search = new URLSearchParams({
      provider: request.selection.provider,
      pair: request.selection.pair,
      timeframe: request.selection.timeframe,
      startTime: request.range.startTime,
      endTime: request.range.endTime,
      limit: String(limit),
      schemaVersion: MARKET_DATA_SCHEMA_VERSION,
    }).toString();

    const response = await this.fetcher(url, {
      method: "GET",
      headers: { Accept: "application/json" },
      signal: request.signal,
    });
    const payload = (await response.json()) as unknown;
    if (response.ok) {
      return candleRangeEnvelopeSchema.parse(payload).data;
    }

    throwMarketDataApiError(payload);
  }
}

export type CreateMarketHistoryQueryOptionsInput = MarketHistoryQueryInput & {
  api: Pick<MarketDataApi, "getCandles">;
};

export function createMarketHistoryQueryOptions(
  input: CreateMarketHistoryQueryOptionsInput,
) {
  return queryOptions({
    queryKey: marketHistoryQueryKey(input),
    queryFn: ({ signal }) =>
      input.api.getCandles({
        selection: input.selection,
        range: input.range,
        limit: input.limit,
        signal,
      }),
  });
}

export function createMarketDimensionsQueryOptions(
  api: Pick<MarketDataApi, "getDimensions">,
) {
  return queryOptions({
    queryKey: marketDimensionsQueryKey(),
    queryFn: ({ signal }) => api.getDimensions(signal),
  });
}

export function createMarketDataApi(
  options: CreateMarketDataApiOptions = {},
): MarketDataApi {
  return new MarketDataApi(options);
}

function throwMarketDataApiError(payload: unknown): never {
  const error = marketDataRestErrorEnvelopeSchema.parse(payload);
  throw new MarketDataApiError({
    code: error.error.code,
    message: error.message,
    retryable: error.error.retryable ?? false,
    requestId: error.requestId,
    ...(error.error.details === undefined || error.error.details === null
      ? {}
      : { details: error.error.details }),
  });
}
