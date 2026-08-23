import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CandlestickChart } from "../../src/features/market-chart/components/CandlestickChart";
import { ChartGrid } from "../../src/features/market-chart/components/ChartGrid";
import { ChartSlot } from "../../src/features/market-chart/components/ChartSlot";
import { ConnectionStatus } from "../../src/features/market-chart/components/ConnectionStatus";
import { useChartSlots } from "../../src/features/market-chart/hooks/useChartSlot";
import {
  MARKET_DATA_TIMEFRAMES,
  CONNECTION_STATES,
  type Candle,
  type ConnectionState,
  type Timeframe,
} from "../../src/features/market-chart/types";

vi.mock("lightweight-charts", () => {
  const CandlestickSeries = Symbol("CandlestickSeries");
  return {
    CandlestickSeries,
    createChart: vi.fn(() => ({
      addSeries: vi.fn(() => ({ setData: vi.fn(), update: vi.fn() })),
      remove: vi.fn(),
      resize: vi.fn(),
    })),
    createSeriesMarkers: vi.fn(() => ({ attach: vi.fn(), detach: vi.fn(), setMarkers: vi.fn() })),
  };
});

function createStableSlotId() {
  let sequence = 0;
  return () => `slot-${++sequence}`;
}

function ChartGridHarness({
  initialTimeframes,
}: {
  initialTimeframes: readonly Timeframe[];
}) {
  const model = useChartSlots({
    provider: "BINANCE",
    pair: "BTCUSDT",
    defaultTimeframe: "5m",
    initialTimeframes,
    createSlotId: createStableSlotId(),
  });

  return (
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
  );
}

function candle(openTime: string, close: string): Candle {
  return {
    provider: "BINANCE",
    pair: "BTCUSDT",
    timeframe: "5m",
    openTime,
    closeTime: new Date(Date.parse(openTime) + 5 * 60_000 - 1).toISOString(),
    open: "100",
    high: "104",
    low: "99",
    close,
    volume: "12.5",
    closed: true,
    revision: 1,
  };
}

describe("accessible names for every required control", () => {
  it("labels the dashboard pair selector and add action", () => {
    render(<ChartGridHarness initialTimeframes={["5m"]} />);

    expect(screen.getByRole("combobox", { name: "Dashboard pair" })).toHaveAttribute(
      "id",
      "select-pair",
    );
    expect(screen.getByRole("button", { name: "Add chart" })).toHaveAttribute(
      "id",
      "btn-add-chart",
    );
  });

  it("names each slot section, timeframe control, and remove action with the slot identity", () => {
    render(<ChartGridHarness initialTimeframes={["5m", "1h"]} />);

    const first = screen.getByRole("region", { name: "BTCUSDT 5m chart" });
    expect(first).toHaveAttribute("id", "chart-btcusdt-5m-slot-1");
    const second = screen.getByRole("region", { name: "BTCUSDT 1h chart" });
    expect(second).toHaveAttribute("id", "chart-btcusdt-1h-slot-2");

    const timeframe = within(first).getByRole("combobox", {
      name: "Timeframe for BTCUSDT chart slot-1",
    });
    expect(timeframe).toHaveAttribute("id", "select-timeframe-slot-1");
    expect(
      within(second).getByRole("combobox", { name: "Timeframe for BTCUSDT chart slot-2" }),
    ).toHaveAttribute("id", "select-timeframe-slot-2");

    expect(
      within(first).getByRole("button", { name: "Remove chart slot-1" }),
    ).toHaveAttribute("id", "btn-remove-chart-slot-1");
    expect(
      within(second).getByRole("button", { name: "Remove chart slot-2" }),
    ).toHaveAttribute("id", "btn-remove-chart-slot-2");
  });

  it("names the retry action and status by slot", () => {
    render(
      <ChartSlot
        slot={{
          slotId: "slot-1",
          pair: "BTCUSDT",
          timeframe: "5m",
          generation: 1,
          candles: [],
          connectionState: "ERROR",
          error: {
            code: "MARKET_RECOVERY_EXHAUSTED",
            message: "Market data recovery was exhausted.",
            retryable: true,
          },
        }}
        timeframes={MARKET_DATA_TIMEFRAMES}
        onTimeframeChange={vi.fn()}
        onRemove={vi.fn()}
        onRetry={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "Retry market data" })).toHaveAttribute(
      "id",
      "btn-retry-chart-slot-1",
    );
    expect(screen.getByRole("status")).toHaveAttribute("id", "status-chart-slot-1");
  });
});

describe("keyboard focus", () => {
  it("keeps every required control focusable and holds focus", async () => {
    render(<ChartGridHarness initialTimeframes={["5m"]} />);

    const controls = [
      document.getElementById("select-pair") as HTMLElement,
      document.getElementById("btn-add-chart") as HTMLElement,
      document.getElementById("select-timeframe-slot-1") as HTMLElement,
      document.getElementById("btn-remove-chart-slot-1") as HTMLElement,
    ];
    for (const control of controls) {
      expect(control).not.toHaveAttribute("tabindex", "-1");
      control.focus();
      expect(control).toHaveFocus();
    }
  });

  it("operates add, timeframe, and remove by keyboard alone", async () => {
    const user = userEvent.setup();
    render(<ChartGridHarness initialTimeframes={["5m"]} />);

    const add = document.getElementById("btn-add-chart") as HTMLButtonElement;
    add.focus();
    await user.keyboard("{Enter}");
    expect(document.getElementById("select-timeframe-slot-2")).toBeVisible();

    const timeframe = document.getElementById("select-timeframe-slot-2") as HTMLSelectElement;
    timeframe.focus();
    await user.selectOptions(timeframe, "1h");
    expect(timeframe).toHaveValue("1h");

    const remove = document.getElementById("btn-remove-chart-slot-2") as HTMLButtonElement;
    remove.focus();
    await user.keyboard("{Enter}");
    expect(document.getElementById("chart-btcusdt-1h-slot-2")).toBeNull();
  });
});

describe("state announcements and non-color status", () => {
  it("announces add, remove, and timeframe changes in a polite live region", async () => {
    const user = userEvent.setup();
    render(<ChartGridHarness initialTimeframes={["5m"]} />);

    const liveRegion = document.querySelector('[aria-live="polite"].sr-only');
    expect(liveRegion).not.toBeNull();
    expect(liveRegion).toHaveAttribute("role", "status");

    const add = document.getElementById("btn-add-chart") as HTMLButtonElement;
    add.focus();
    await user.keyboard("{Enter}");
    expect(liveRegion).toHaveTextContent("Chart slot-2 added.");

    const timeframe = document.getElementById("select-timeframe-slot-2") as HTMLSelectElement;
    timeframe.focus();
    await user.selectOptions(timeframe, "15m");
    expect(liveRegion).toHaveTextContent("Chart slot-2 timeframe changed to 15m.");

    const remove = document.getElementById("btn-remove-chart-slot-2") as HTMLButtonElement;
    remove.focus();
    await user.keyboard("{Enter}");
    expect(liveRegion).toHaveTextContent("Chart slot-2 removed.");
  });

  it.each(CONNECTION_STATES)("conveys %s with text and an icon, never color alone", (state) => {
    const label = {
      LOADING: "Loading",
      LIVE: "Live",
      STALE: "Stale",
      RECONNECTING: "Reconnecting",
      ERROR: "Error",
      RELEASED: "Released",
    }[state] as string;
    render(
      <ConnectionStatus
        slotId="slot-1"
        connectionState={state as ConnectionState}
        attempt={state === "RECONNECTING" ? 2 : undefined}
        lastEventAt="2026-08-13T10:00:01Z"
        error={
          state === "ERROR"
            ? { code: "MARKET_RECOVERY_EXHAUSTED", message: "Recovery exhausted.", retryable: true }
            : undefined
        }
      />,
    );

    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-live", "polite");
    expect(status).toHaveAttribute("aria-atomic", "true");
    expect(status).toHaveTextContent(label);
    const icon = status.querySelector("[data-status-icon]");
    expect(icon).not.toBeNull();
    expect(icon).toHaveAttribute("aria-hidden", "true");
  });

  it("marks a loading slot as busy", () => {
    render(
      <ChartSlot
        slot={{
          slotId: "slot-1",
          pair: "BTCUSDT",
          timeframe: "5m",
          generation: 1,
          candles: [],
          connectionState: "LOADING",
        }}
        timeframes={MARKET_DATA_TIMEFRAMES}
        onTimeframeChange={vi.fn()}
        onRemove={vi.fn()}
        onRetry={vi.fn()}
      />,
    );

    expect(screen.getByRole("region", { name: "BTCUSDT 5m chart" })).toHaveAttribute(
      "aria-busy",
      "true",
    );
  });
});

describe("latest-Candle semantic summary", () => {
  it("names the chart image and exposes a UTC OHLCV summary", () => {
    const latest = candle("2026-08-13T10:05:00.000Z", "103.5");
    render(
      <CandlestickChart candles={[candle("2026-08-13T10:00:00.000Z", "101"), latest]} />,
    );

    expect(screen.getByRole("img", { name: "BTCUSDT 5m Candlestick chart" })).toBeVisible();
    const summary = screen.getByLabelText("Latest Candle summary");
    expect(summary).toHaveTextContent("2026-08-13T10:05:00.000Z");
    expect(summary).toHaveTextContent("O 100");
    expect(summary).toHaveTextContent("H 104");
    expect(summary).toHaveTextContent("L 99");
    expect(summary).toHaveTextContent("C 103.5");
    expect(summary).toHaveTextContent("V 12.5");
  });
});