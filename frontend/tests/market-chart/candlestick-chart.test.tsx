import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CandlestickChart } from "../../src/features/market-chart/components/CandlestickChart";
import type { Candle } from "../../src/features/market-chart/types";

type LightweightCandle = {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
};

type ResizeObserverDouble = {
  callback: ResizeObserverCallback;
  disconnect: ReturnType<typeof vi.fn>;
  observe: ReturnType<typeof vi.fn>;
  target?: Element;
};

const lightweightCharts = vi.hoisted(() => {
  const CandlestickSeries = Symbol("CandlestickSeries");
  const instances: Array<{
    chart: {
      addSeries: ReturnType<typeof vi.fn>;
      remove: ReturnType<typeof vi.fn>;
      resize: ReturnType<typeof vi.fn>;
      timeScale: ReturnType<typeof vi.fn>;
    };
    container: HTMLElement;
    options: unknown;
    series: {
      setData: ReturnType<typeof vi.fn>;
      update: ReturnType<typeof vi.fn>;
    };
    timeScale: {
      getVisibleLogicalRange: ReturnType<typeof vi.fn>;
      setVisibleLogicalRange: ReturnType<typeof vi.fn>;
    };
  }> = [];

  const createChart = vi.fn((container: HTMLElement, options?: unknown) => {
    const series = {
      setData: vi.fn(),
      update: vi.fn(),
    };
    const timeScale = {
      getVisibleLogicalRange: vi.fn(() => null),
      setVisibleLogicalRange: vi.fn(),
    };
    const chart = {
      addSeries: vi.fn(() => series),
      remove: vi.fn(),
      resize: vi.fn(),
      timeScale: vi.fn(() => timeScale),
    };

    instances.push({ chart, container, options, series, timeScale });
    return chart;
  });

  return { CandlestickSeries, createChart, instances };
});

vi.mock("lightweight-charts", () => ({
  CandlestickSeries: lightweightCharts.CandlestickSeries,
  ColorType: { Solid: "solid" },
  createChart: lightweightCharts.createChart,
}));

const resizeObservers: ResizeObserverDouble[] = [];

class ControllableResizeObserver implements ResizeObserver {
  readonly callback: ResizeObserverCallback;
  readonly disconnect = vi.fn();
  readonly observe = vi.fn((target: Element) => {
    this.target = target;
  });
  readonly unobserve = vi.fn();
  target?: Element;

  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
    resizeObservers.push(this);
  }
}

function emitResize(observer: ResizeObserverDouble, width: number, height: number) {
  const target = observer.target;
  if (target === undefined) throw new Error("ResizeObserver did not observe a chart container");

  observer.callback(
    [
      {
        target,
        contentRect: {
          bottom: height,
          height,
          left: 0,
          right: width,
          top: 0,
          width,
          x: 0,
          y: 0,
          toJSON: () => ({}),
        },
      } as ResizeObserverEntry,
    ],
    observer as unknown as ResizeObserver,
  );
}

function value(index: number): Candle {
  const openTime = new Date(Date.UTC(2026, 7, 13, 10, index)).toISOString();
  const closeTime = new Date(Date.UTC(2026, 7, 13, 10, index, 59, 999)).toISOString();
  return {
    provider: "BINANCE",
    pair: "BTCUSDT",
    timeframe: "1m",
    openTime,
    closeTime,
    open: "100",
    high: "103",
    low: "99",
    close: String(101 + index),
    volume: "12.5",
    closed: index < 2,
    receivedAt: openTime,
  };
}

function chartPoint(candle: Candle): LightweightCandle {
  return {
    time: Date.parse(candle.openTime) / 1_000,
    open: Number(candle.open),
    high: Number(candle.high),
    low: Number(candle.low),
    close: Number(candle.close),
  };
}

describe("base CandlestickChart", () => {
  beforeEach(() => {
    lightweightCharts.createChart.mockClear();
    lightweightCharts.instances.length = 0;
    resizeObservers.length = 0;
    vi.stubGlobal("ResizeObserver", ControllableResizeObserver);
  });

  it("creates a v5 Candlestick series with the bounded newest tail and keeps a semantic summary", () => {
    const oldest = value(0);
    const middle = value(1);
    const latest = value(2);

    render(
      <CandlestickChart
        candles={[latest, oldest, middle]}
        maxCandles={2}
      />,
    );

    expect(lightweightCharts.createChart).toHaveBeenCalledTimes(1);
    const instance = lightweightCharts.instances[0];
    expect(instance).toBeDefined();
    expect(instance.chart.addSeries).toHaveBeenCalledTimes(1);
    expect(instance.chart.addSeries.mock.calls[0]?.[0]).toBe(
      lightweightCharts.CandlestickSeries,
    );
    expect(instance.series.setData).toHaveBeenCalledTimes(1);
    expect(instance.series.setData.mock.calls[0]?.[0]).toEqual([
      chartPoint(middle),
      chartPoint(latest),
    ]);
    expect(instance.options).toMatchObject({
      layout: {
        background: { type: "solid", color: "#0b111a" },
        textColor: "#94a3b8",
      },
      grid: {
        vertLines: { color: "#1c2735" },
        horzLines: { color: "#1c2735" },
      },
    });

    expect(screen.getByTestId("candlestick-series")).toHaveAttribute(
      "data-series-length",
      "2",
    );
    expect(screen.getByLabelText("Latest Candle summary")).toHaveTextContent(
      "BTCUSDT 1m at 2026-08-13T10:02:00.000Z",
    );
    expect(screen.getByLabelText("Latest Candle summary")).toHaveTextContent(
      "O 100 H 103 L 99 C 103 V 12.5",
    );
  });

  it("updates a revised tail incrementally without recreating or resetting the chart", () => {
    const initial = [value(0), value(1)];
    const revisedTail: Candle = {
      ...value(1),
      close: "107.5",
      high: "108",
      receivedAt: "2026-08-13T10:02:01.000Z",
    };
    const { rerender, unmount } = render(
      <CandlestickChart candles={initial} height={320} />,
    );
    const instance = lightweightCharts.instances[0];
    const observer = resizeObservers[0];

    expect(instance).toBeDefined();
    expect(observer).toBeDefined();
    expect(instance.series.setData).toHaveBeenCalledTimes(1);

    rerender(<CandlestickChart candles={[value(0), revisedTail]} height={320} />);

    expect(lightweightCharts.createChart).toHaveBeenCalledTimes(1);
    expect(instance.series.setData).toHaveBeenCalledTimes(1);
    expect(instance.series.update).toHaveBeenCalledTimes(1);
    expect(instance.series.update).toHaveBeenLastCalledWith(chartPoint(revisedTail));
    expect(screen.getByLabelText("Latest Candle summary")).toHaveTextContent(
      "H 108 L 99 C 107.5",
    );

    act(() => emitResize(observer, 640, 320));
    expect(instance.chart.resize).toHaveBeenLastCalledWith(640, 320);

    unmount();
    expect(instance.chart.remove).toHaveBeenCalledTimes(1);
    expect(observer.disconnect).toHaveBeenCalledTimes(1);
  });

  it("replaces the bounded dataset when a same-length tail changes identity", () => {
    const { rerender } = render(
      <CandlestickChart candles={[value(0), value(1)]} />,
    );
    const instance = lightweightCharts.instances[0];

    rerender(<CandlestickChart candles={[value(0), value(2)]} />);

    expect(instance.series.update).not.toHaveBeenCalled();
    expect(instance.series.setData).toHaveBeenCalledTimes(2);
    expect(instance.series.setData).toHaveBeenLastCalledWith([
      chartPoint(value(0)),
      chartPoint(value(2)),
    ]);
  });

  it("keeps separate chart instances and resize-driven viewports for sibling slots", () => {
    const leftCandles = [value(0), value(1)];
    const rightCandles = [
      { ...value(0), timeframe: "5m" as const },
      { ...value(1), timeframe: "5m" as const },
    ];

    const { rerender } = render(
      <>
        <CandlestickChart candles={leftCandles} height={240} />
        <CandlestickChart candles={rightCandles} height={360} />
      </>,
    );

    expect(lightweightCharts.createChart).toHaveBeenCalledTimes(2);
    const [left, right] = lightweightCharts.instances;
    const [leftObserver, rightObserver] = resizeObservers;
    expect(left).toBeDefined();
    expect(right).toBeDefined();
    expect(left.chart).not.toBe(right.chart);
    expect(left.container).not.toBe(right.container);
    expect(left.chart.timeScale()).not.toBe(right.chart.timeScale());

    act(() => emitResize(leftObserver, 420, 240));
    expect(left.chart.resize).toHaveBeenLastCalledWith(420, 240);
    expect(right.chart.resize).not.toHaveBeenCalled();

    act(() => emitResize(rightObserver, 860, 360));
    expect(right.chart.resize).toHaveBeenLastCalledWith(860, 360);

    const revisedLeft: Candle = { ...value(1), close: "109" };
    rerender(
      <>
        <CandlestickChart candles={[value(0), revisedLeft]} height={240} />
        <CandlestickChart candles={rightCandles} height={360} />
      </>,
    );

    expect(lightweightCharts.createChart).toHaveBeenCalledTimes(2);
    expect(left.series.update).toHaveBeenLastCalledWith(chartPoint(revisedLeft));
    expect(right.series.update).not.toHaveBeenCalled();
    expect(right.series.setData).toHaveBeenCalledTimes(1);
  });

  it("states that no Candles are available without creating an invalid chart", () => {
    render(<CandlestickChart candles={[]} />);

    expect(screen.getByText("No Candles are available for this range.")).toBeInTheDocument();
    expect(screen.queryByTestId("candlestick-series")).not.toBeInTheDocument();
    expect(lightweightCharts.createChart).not.toHaveBeenCalled();
  });
});
