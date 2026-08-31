import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  isMarketDataConnectionReady,
  isMarketPairConfirmed,
  MarketRoute,
  reconcileMarketPair,
} from "../../src/app/routes/market";
import type { MarketDimensions } from "../../src/features/market-chart/types";

describe("connected market capability gate", () => {
  it("does not treat an unconfirmed pair as safe for market data", () => {
    expect(isMarketPairConfirmed("BNBUSDT", undefined)).toBe(false);
    expect(isMarketPairConfirmed("BNBUSDT", ["BTCUSDT", "ETHUSDT", "SOLUSDT"])).toBe(
      false,
    );
    expect(isMarketPairConfirmed("ETHUSDT", ["BTCUSDT", "ETHUSDT", "SOLUSDT"])).toBe(
      true,
    );
  });

  it("opens the realtime connection only after non-empty capability confirmation", () => {
    const capabilities: MarketDimensions = {
      schemaVersion: "1",
      providers: ["BINANCE"],
      pairs: ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
      timeframes: ["5m"],
    };

    expect(
      isMarketDataConnectionReady("BINANCE", "ETHUSDT", ["5m"], capabilities, {
        isSuccess: true,
        isError: false,
        isFetching: false,
      }),
    ).toBe(true);
    expect(
      isMarketDataConnectionReady("COINBASE", "ETHUSDT", ["5m"], capabilities, {
        isSuccess: true,
        isError: false,
        isFetching: true,
      }),
    ).toBe(false);
    expect(
      isMarketDataConnectionReady("BINANCE", "ETHUSDT", ["5m"], capabilities, {
        isSuccess: true,
        isError: false,
        isFetching: true,
      }),
    ).toBe(true);
    expect(
      isMarketDataConnectionReady("BINANCE", "ETHUSDT", ["1h"], capabilities, {
        isSuccess: true,
        isError: false,
        isFetching: false,
      }),
    ).toBe(false);
    expect(
      isMarketDataConnectionReady("BINANCE", "ETHUSDT", ["5m"], {
        ...capabilities,
        pairs: [],
      }, {
        isSuccess: true,
        isError: false,
        isFetching: false,
      }),
    ).toBe(false);
    expect(
      isMarketDataConnectionReady(
        "BINANCE",
        "ETHUSDT",
        ["1h"],
        { ...capabilities, timeframes: ["1h"] },
        { isSuccess: true, isError: false, isFetching: false },
      ),
    ).toBe(true);
  });

  it("reconciles a persisted unsupported pair only after confirmation", () => {
    const confirmed = ["BTCUSDT", "ETHUSDT", "SOLUSDT"] as const;

    expect(reconcileMarketPair("BNBUSDT", confirmed)).toBe("BTCUSDT");
    expect(reconcileMarketPair("ETHUSDT", confirmed)).toBe("ETHUSDT");
    expect(reconcileMarketPair("BNBUSDT", [])).toBe("BNBUSDT");
  });

  it("shows a retryable capability error without opening market data", () => {
    const onRetry = vi.fn();

    render(
      <MarketRoute
        capabilityError="Market capabilities could not be loaded."
        onRetryCapabilities={onRetry}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Market capabilities could not be loaded.",
    );
    fireEvent.click(screen.getByRole("button", { name: "Retry market capabilities" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
