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
  pair = "BTCUSDT",
  pairs,
  onPairChange,
}: {
  initialTimeframes: readonly Timeframe[];
  pair?: string;
  pairs?: readonly string[];
  onPairChange?: (pair: string) => void;
}) {
  const model = useChartSlots({
    provider: "BINANCE",
    pair,
    defaultTimeframe: "5m",
    initialTimeframes,
    createSlotId: createStableSlotId(),
  });

  return (
    <ChartGrid
      pair={model.pair}
      pairs={pairs}
      slots={model.slots}
      timeframes={MARKET_DATA_TIMEFRAMES}
      limitMessage={model.limitMessage}
      announcement={model.announcement}
      onAdd={model.addSlot}
      onSetCount={model.setSlotCount}
      onRemove={model.removeSlot}
      onTimeframeChange={model.changeTimeframe}
      onRetry={model.retrySlot}
      onPairChange={onPairChange}
    />
  );
}

function chartRegions() {
  return screen.getAllByRole("region", { name: /BTCUSDT .* chart/i });
}

describe("one-to-four stable chart slots", () => {
  it("offers supported pair options and reports a selected pair", async () => {
    const user = userEvent.setup();
    const onPairChange = vi.fn();
    render(
      <ChartGridHarness
        initialTimeframes={["5m"]}
        pairs={["BTCUSDT", "ETHUSDT", "SOLUSDT"]}
        onPairChange={onPairChange}
      />,
    );

    const selector = screen.getByRole("combobox", { name: "Dashboard pair" });
    expect(selector.querySelectorAll("option")).toHaveLength(3);
    await user.selectOptions(selector, "ETHUSDT");
    expect(onPairChange).toHaveBeenCalledWith("ETHUSDT");
  });

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

  it("switches directly between one, two, and four stable chart slots", async () => {
    const user = userEvent.setup();
    render(<ChartGridHarness initialTimeframes={["5m"]} />);

    const first = document.getElementById("chart-btcusdt-5m-slot-1");
    const one = screen.getByRole("button", { name: "Show 1 chart" });
    const two = screen.getByRole("button", { name: "Show 2 charts" });
    const four = screen.getByRole("button", { name: "Show 4 charts" });
    expect(one).toHaveAttribute("aria-pressed", "true");
    expect(two).toHaveAttribute("aria-pressed", "false");
    expect(four).toHaveAttribute("aria-pressed", "false");

    await user.click(four);
    expect(chartRegions()).toHaveLength(4);
    expect(document.getElementById("chart-btcusdt-5m-slot-1")).toBe(first);
    expect(four).toHaveAttribute("aria-pressed", "true");

    await user.click(two);
    expect(chartRegions()).toHaveLength(2);
    expect(document.getElementById("chart-btcusdt-5m-slot-1")).toBe(first);
    expect(document.getElementById("chart-btcusdt-5m-slot-2")).toBeVisible();
    expect(document.getElementById("chart-btcusdt-5m-slot-3")).toBeNull();

    await user.click(one);
    expect(chartRegions()).toHaveLength(1);
    expect(document.getElementById("chart-btcusdt-5m-slot-1")).toBe(first);
    expect(screen.getByTestId("chart-grid")).toHaveClass("md:grid-cols-1");
    expect(screen.getByTestId("chart-grid")).not.toHaveClass("md:grid-cols-2");
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
  it("switches four charts to a compact two-row workspace density", () => {
    render(<ChartGridHarness initialTimeframes={INITIAL_TIMEFRAMES} />);

    const grid = screen.getByTestId("chart-grid");
    expect(grid).toHaveAttribute("data-density", "compact");
    expect(grid).toHaveClass("xl:grid-rows-2");
    expect(screen.getByRole("group", { name: "Chart workspace controls" })).toBeVisible();
    for (const region of chartRegions()) {
      expect(region).toHaveAttribute("data-layout-density", "compact");
    }
  });

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
    const controls = screen.getByRole("group", { name: "Chart workspace controls" });
    expect(within(controls).getByRole("heading", { name: "Multi-chart market data" })).toBeVisible();
    expect(within(controls).getByRole("combobox", { name: "Dashboard pair" })).toBeVisible();
    expect(within(controls).getByRole("button", { name: "Add chart" })).toBeVisible();
    expect(screen.queryByText("Realtime market workspace")).not.toBeInTheDocument();
    expect(screen.queryByText(/Compare one dashboard pair/i)).not.toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "Beginner candle guide" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "How candles update" })).toBeVisible();
    expect(screen.getByText("The current candle is still forming")).toBeVisible();
    expect(screen.getByText("A new candle starts each period")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Read a candle" })).toBeVisible();
    expect(screen.getByText("O · Open")).toBeVisible();
    expect(screen.getByText("H · High")).toBeVisible();
    expect(screen.getByText("L · Low")).toBeVisible();
    expect(screen.getByText("C · Close")).toBeVisible();
    expect(screen.getByText("V · Volume")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Connection states" })).toBeVisible();
    expect(screen.getByTestId("market-workspace")).toHaveClass("h-full");
    expect(screen.getByTestId("market-workspace")).toHaveClass("overflow-y-auto");
    expect(screen.getByTestId("market-workspace")).toHaveClass("xl:overflow-y-hidden");
    expect(screen.getByTestId("market-content")).toHaveClass(
      "xl:grid-cols-[minmax(0,1fr)_15rem]",
    );
  });

  it("renders the selected non-BTC pair through the Market route", async () => {
    const user = userEvent.setup();
    const onPairChange = vi.fn();

    render(
      <MarketRoute
        pair="SOLUSDT"
        pairs={["BTCUSDT", "ETHUSDT", "SOLUSDT"]}
        onPairChange={onPairChange}
        initialTimeframes={["5m"]}
        createSlotId={() => "slot-sol"}
      />,
    );

    expect(document.getElementById("chart-solusdt-5m-slot-sol")).toBeVisible();
    const selector = screen.getByRole("combobox", { name: "Dashboard pair" });
    expect(selector).toHaveValue("SOLUSDT");
    await user.selectOptions(selector, "ETHUSDT");
    expect(onPairChange).toHaveBeenCalledWith("ETHUSDT");
  });
});
