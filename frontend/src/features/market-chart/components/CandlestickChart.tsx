import {
  CandlestickSeries,
  LineSeries,
  LineStyle,
  createChart,
  createSeriesMarkers,
  type CandlestickData,
  type IChartApi,
  type ISeriesApi,
  type ISeriesMarkersPluginApi,
  type LineData,
  type SeriesMarker,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";
import { useEffect, useMemo, useRef } from "react";

import type { Candle } from "../types";

export type ChartOverlayPoint = {
  openTime: string;
  value: number;
};

export type ChartOverlaySeries = {
  id: string;
  points: readonly ChartOverlayPoint[];
  color?: string;
  dashed?: boolean;
};

export type ChartMarker = {
  id: string;
  openTime: string;
  value: number;
  label: string;
  color?: string;
};

export type CandlestickChartProps = {
  candles: readonly Candle[];
  maxCandles?: number;
  height?: number;
  overlays?: readonly ChartOverlaySeries[];
  markers?: readonly ChartMarker[];
  className?: string;
  onEventRendered?: (eventId: string) => void;
  renderedEventId?: string;
};

const CANDLE_SERIES_OPTIONS = {
  upColor: "#21c58b",
  downColor: "#f05b64",
  borderVisible: false,
  wickUpColor: "#21c58b",
  wickDownColor: "#f05b64",
} as const;

export function CandlestickChart({
  candles,
  maxCandles = 1_000,
  height = 280,
  overlays = [],
  markers = [],
  className,
  onEventRendered,
  renderedEventId,
}: CandlestickChartProps) {
  if (!Number.isInteger(maxCandles) || maxCandles < 1 || maxCandles > 1_000) {
    throw new Error("maxCandles must be between one and 1,000");
  }

  const boundedCandles = useMemo(
    () =>
      [...candles]
        .sort((left, right) => left.openTime.localeCompare(right.openTime))
        .slice(-maxCandles),
    [candles, maxCandles],
  );
  const chartData = useMemo(
    () => boundedCandles.map(toCandlestickData),
    [boundedCandles],
  );
  const latest = boundedCandles.at(-1);
  const hasCandles = latest !== undefined;

  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const overlaySeriesRef = useRef(new Map<string, ISeriesApi<"Line">>());
  const markersPluginRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null);
  const previousDataRef = useRef<CandlestickData<Time>[]>([]);
  const bootstrapDataRef = useRef(chartData);
  const heightRef = useRef(height);

  bootstrapDataRef.current = chartData;
  heightRef.current = height;

  useEffect(() => {
    if (!hasCandles) return;
    const container = containerRef.current;
    if (container === null) return;

    const chart = createChart(container, {
      height: heightRef.current,
      layout: {
        attributionLogo: true,
      },
    });
    const candleSeries = chart.addSeries(CandlestickSeries, CANDLE_SERIES_OPTIONS);
    const initialData = [...bootstrapDataRef.current];

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    previousDataRef.current = initialData;
    candleSeries.setData(initialData);

    const resizeObserver =
      typeof ResizeObserver === "undefined"
        ? undefined
        : new ResizeObserver((entries) => {
            const entry = entries[0];
            if (entry === undefined) return;
            chart.resize(Math.max(1, Math.round(entry.contentRect.width)), heightRef.current);
          });
    resizeObserver?.observe(container);

    return () => {
      resizeObserver?.disconnect();
      markersPluginRef.current?.detach();
      markersPluginRef.current = null;
      overlaySeriesRef.current.clear();
      previousDataRef.current = [];
      candleSeriesRef.current = null;
      chartRef.current = null;
      chart.remove();
    };
  }, [hasCandles]);

  useEffect(() => {
    const candleSeries = candleSeriesRef.current;
    if (candleSeries === null) return;

    const previousData = previousDataRef.current;
    if (sameData(previousData, chartData)) return;

    const tail = chartData.at(-1);
    if (tail !== undefined && supportsTailUpdate(previousData, chartData)) {
      candleSeries.update(tail);
    } else {
      candleSeries.setData([...chartData]);
    }
    previousDataRef.current = chartData;
  }, [chartData]);

  useEffect(() => {
    const chart = chartRef.current;
    if (chart === null) return;

    const activeIds = new Set(overlays.map((overlay) => overlay.id));
    for (const [id, overlaySeries] of overlaySeriesRef.current) {
      if (activeIds.has(id)) continue;
      chart.removeSeries(overlaySeries);
      overlaySeriesRef.current.delete(id);
    }

    const visibleTimes = new Set(boundedCandles.map((candle) => candle.openTime));
    for (const overlay of overlays) {
      let overlaySeries = overlaySeriesRef.current.get(overlay.id);
      const options = {
        color: overlay.color ?? "#4f7cff",
        lineStyle: overlay.dashed ? LineStyle.Dashed : LineStyle.Solid,
      };
      if (overlaySeries === undefined) {
        overlaySeries = chart.addSeries(LineSeries, options);
        overlaySeriesRef.current.set(overlay.id, overlaySeries);
      } else {
        overlaySeries.applyOptions(options);
      }
      const points: LineData<Time>[] = overlay.points
        .filter((point) => visibleTimes.has(point.openTime))
        .sort((left, right) => left.openTime.localeCompare(right.openTime))
        .map((point) => ({
          time: toUtcTimestamp(point.openTime),
          value: point.value,
        }));
      overlaySeries.setData(points);
    }
  }, [boundedCandles, overlays]);

  useEffect(() => {
    const candleSeries = candleSeriesRef.current;
    if (candleSeries === null) return;

    const visibleTimes = new Set(boundedCandles.map((candle) => candle.openTime));
    const visibleMarkers: SeriesMarker<Time>[] = markers
      .filter((marker) => visibleTimes.has(marker.openTime))
      .sort((left, right) => left.openTime.localeCompare(right.openTime))
      .map((marker) => ({
        id: marker.id,
        time: toUtcTimestamp(marker.openTime),
        position: "atPriceMiddle",
        price: marker.value,
        shape: "circle",
        color: marker.color ?? "#e6b94a",
        text: marker.label,
      }));

    if (markersPluginRef.current === null) {
      if (visibleMarkers.length === 0) return;
      markersPluginRef.current = createSeriesMarkers(candleSeries, visibleMarkers);
      return;
    }
    markersPluginRef.current.setMarkers(visibleMarkers);
  }, [boundedCandles, markers]);

  useEffect(() => {
    if (renderedEventId !== undefined) onEventRendered?.(renderedEventId);
  }, [onEventRendered, renderedEventId]);

  if (latest === undefined) {
    return (
      <div className={className} role="note">
        No Candles are available for this range.
      </div>
    );
  }

  return (
    <figure className={className}>
      <div
        ref={containerRef}
        data-testid="candlestick-series"
        data-series-length={boundedCandles.length}
        role="img"
        aria-label={`${latest.pair} ${latest.timeframe} Candlestick chart`}
        style={{ height, width: "100%" }}
      />
      <figcaption aria-label="Latest Candle summary" className="font-mono text-xs">
        {latest.pair} {latest.timeframe} at {latest.openTime} · O {latest.open} H {latest.high} L{" "}
        {latest.low} C {latest.close} V {latest.volume}
      </figcaption>
    </figure>
  );
}

function toUtcTimestamp(value: string): UTCTimestamp {
  return Math.floor(Date.parse(value) / 1_000) as UTCTimestamp;
}

function toCandlestickData(candle: Candle): CandlestickData<Time> {
  return {
    time: toUtcTimestamp(candle.openTime),
    open: Number(candle.open),
    high: Number(candle.high),
    low: Number(candle.low),
    close: Number(candle.close),
  };
}

function samePoint(left: CandlestickData<Time>, right: CandlestickData<Time>) {
  return (
    left.time === right.time &&
    left.open === right.open &&
    left.high === right.high &&
    left.low === right.low &&
    left.close === right.close
  );
}

function sameData(
  left: readonly CandlestickData<Time>[],
  right: readonly CandlestickData<Time>[],
) {
  return left.length === right.length && left.every((point, index) => samePoint(point, right[index]));
}

function supportsTailUpdate(
  previous: readonly CandlestickData<Time>[],
  next: readonly CandlestickData<Time>[],
) {
  if (previous.length === 0 || next.length === 0) return false;

  if (next.length === previous.length + 1) {
    return previous.every((point, index) => samePoint(point, next[index]));
  }

  if (next.length !== previous.length) return false;
  if (previous.at(-1)?.time !== next.at(-1)?.time) return false;
  return previous
    .slice(0, -1)
    .every((point, index) => samePoint(point, next[index]));
}
