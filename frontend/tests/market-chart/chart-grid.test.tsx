import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StrictMode } from "react";
import { describe, expect, it, vi } from "vitest";

import { MarketRoute } from "../../src/app/routes/market";
import { ChartGrid } from "../../src/features/market-chart/components/ChartGrid";
import { ChartSlot } from "../../src/features/market-chart/components/ChartSlot";
import { ConnectionStatus } from "../../src/features/market-chart/components/ConnectionStatus";
import { useChartSlots } from "../../src/features/market-chart/hooks/useChartSlot";
import {
  MARKET_DATA_TIMEFRAMES,
  type Timeframe,
} from "../../src/features/market-chart/types";

const LIMIT_MESSAGE = "A dashboard can use at most four chart slots.";
const INITIAL_TIMEFRAMES = ["5m", "15m", "1h", "4h"] as const;

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

function chartRegions() {
  return screen.getAllByRole("region", { name: /BTCUSDT .* chart/i });
}

describe("one-to-four stable chart slots", () => {
  it.each([1, 2, 3, 4])("renders exactly %i labelled chart slot(s)", (count) => {
    render(
      <ChartGridHarness initialTimeframes={INITIAL_TIMEFRAMES.slice(0, count)} />,
    );

    expect(chartRegions()).toHaveLength(count);
    for (const [index, timeframe] of INITIAL_TIMEFRAMES.slice(0, count).entries()) {
      const slotId = `slot-${index + 1}`;
      expect(
        document.getElementById(`chart-btcusdt-${timeframe}-${slotId}`),
      ).toBe(chartRegions()[index]);
      expect(document.getElementById(`select-timeframe-${slotId}`)).toBeVisible();
      expect(document.getElementById(`status-chart-${slotId}`)).toBeVisible();
    }
  });

  it("allocates each slot ID once under React StrictMode", async () => {
    const user = userEvent.setup();
    render(
      <StrictMode>
        <ChartGridHarness initialTimeframes={["5m"]} />
      </StrictMode>,
    );

    await user.click(document.getElementById("btn-add-chart") as HTMLButtonElement);

    expect(document.getElementById("chart-btcusdt-5m-slot-2")).toBeVisible();
    expect(document.getElementById("chart-btcusdt-5m-slot-3")).toBeNull();
  });

  it("keeps stable identities when a middle slot is removed and a new slot is added", async () => {
    const user = userEvent.setup();
    render(<ChartGridHarness initialTimeframes={INITIAL_TIMEFRAMES.slice(0, 3)} />);

    const firstSlot = document.getElementById("chart-btcusdt-5m-slot-1");
    const thirdSlot = document.getElementById("chart-btcusdt-1h-slot-3");
    const removeSecond = document.getElementById(
      "btn-remove-chart-slot-2",
    ) as HTMLButtonElement;
    removeSecond.focus();
    await user.keyboard("{Enter}");

    expect(document.getElementById("chart-btcusdt-15m-slot-2")).toBeNull();
    expect(document.getElementById("chart-btcusdt-5m-slot-1")).toBe(firstSlot);
    expect(document.getElementById("chart-btcusdt-1h-slot-3")).toBe(thirdSlot);

    const add = document.getElementById("btn-add-chart") as HTMLButtonElement;
    add.focus();
    await user.keyboard("{Enter}");

    expect(document.getElementById("chart-btcusdt-5m-slot-4")).toBeVisible();
    expect(document.getElementById("chart-btcusdt-5m-slot-1")).toBe(firstSlot);
    expect(document.getElementById("chart-btcusdt-1h-slot-3")).toBe(thirdSlot);
  });

  it("rejects a fifth request, preserves four slots, and explains the limit", async () => {
    const user = userEvent.setup();
    render(<ChartGridHarness initialTimeframes={INITIAL_TIMEFRAMES} />);

    const existing = chartRegions();
    const add = document.getElementById("btn-add-chart") as HTMLButtonElement;
    add.focus();
    await user.keyboard("{Enter}");

    expect(chartRegions()).toHaveLength(4);
    chartRegions().forEach((region, index) => expect(region).toBe(existing[index]));
    const explanation = screen.getByRole("alert");
    expect(explanation).toHaveAttribute("id", "message-chart-limit");
    expect(explanation).toHaveTextContent(LIMIT_MESSAGE);
  });
});

describe("accessible slot controls and status", () => {
  it("uses text plus an icon and politely announces meaningful connection state", () => {
    render(
      <ConnectionStatus
        slotId="slot-1"
        connectionState="LIVE"
        lastEventAt="2026-08-13T10:00:01Z"
      />,
    );

    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("id", "status-chart-slot-1");
    expect(status).toHaveAttribute("aria-live", "polite");
    expect(status).toHaveTextContent("Live");
    expect(status).toHaveTextContent("2026-08-13T10:00:01Z");
    expect(status.querySelector("[data-status-icon]")).not.toBeNull();
  });

  it("keeps timeframe, remove, and retry actions native and keyboard-operable", async () => {
    const user = userEvent.setup();
    const onTimeframeChange = vi.fn();
    const onRemove = vi.fn();
    const onRetry = vi.fn();

    render(
      <ChartSlot
        slot={{
          slotId: "slot-error",
          pair: "BTCUSDT",
          timeframe: "5m",
          generation: 3,
          candles: [],
          connectionState: "ERROR",
          error: {
            code: "MARKET_RECOVERY_EXHAUSTED",
            message: "Market data recovery was exhausted.",
            retryable: true,
          },
        }}
        timeframes={MARKET_DATA_TIMEFRAMES}
        onTimeframeChange={onTimeframeChange}
        onRemove={onRemove}
        onRetry={onRetry}
      />,
    );

    const section = screen.getByRole("region", { name: /BTCUSDT 5m chart/i });
    expect(section).toHaveAttribute("id", "chart-btcusdt-5m-slot-error");

    const timeframe = within(section).getByRole("combobox", { name: /timeframe/i });
    expect(timeframe).toHaveAttribute("id", "select-timeframe-slot-error");
    timeframe.focus();
    await user.selectOptions(timeframe, "1h");
    expect(onTimeframeChange).toHaveBeenCalledWith("slot-error", "1h");

    const remove = within(section).getByRole("button", { name: /remove chart/i });
    expect(remove).toHaveAttribute("id", "btn-remove-chart-slot-error");
    remove.focus();
    await user.keyboard("{Enter}");
    expect(onRemove).toHaveBeenCalledWith("slot-error");

    const retry = within(section).getByRole("button", { name: /retry/i });
    expect(retry).toHaveAttribute("id", "btn-retry-chart-slot-error");
    retry.focus();
    await user.keyboard(" ");
    expect(onRetry).toHaveBeenCalledWith("slot-error");

    const status = within(section).getByRole("status");
    expect(status).toHaveTextContent("Error");
    expect(status).toHaveTextContent("Market data recovery was exhausted.");
    expect(status.querySelector("[data-status-icon]")).not.toBeNull();
  });
});

describe("responsive grid and route composition", () => {
  it("declares one narrow column and two columns only when space permits", () => {
    render(<ChartGridHarness initialTimeframes={INITIAL_TIMEFRAMES} />);

    expect(screen.getByTestId("chart-grid")).toHaveClass("grid-cols-1");
    expect(screen.getByTestId("chart-grid")).toHaveClass("md:grid-cols-2");
    for (const slotId of ["slot-1", "slot-2", "slot-3", "slot-4"]) {
      expect(document.getElementById(`select-timeframe-${slotId}`)).toBeVisible();
      expect(document.getElementById(`status-chart-${slotId}`)).toBeVisible();
      expect(document.getElementById(`btn-remove-chart-${slotId}`)).toBeVisible();
    }
  });

  it("composes the Market route around the chart grid contract", () => {
    render(
      <MarketRoute
        initialTimeframes={["5m"]}
        createSlotId={() => "slot-route"}
      />,
    );

    expect(screen.getByTestId("chart-grid")).toBeVisible();
    expect(document.getElementById("chart-btcusdt-5m-slot-route")).toBeVisible();
    expect(document.getElementById("select-pair")).toHaveValue("BTCUSDT");
  });
});
