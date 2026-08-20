import { Plus } from "lucide-react";

import type { ChartSlotPreset, ChartSlotState } from "../hooks/useChartSlot";
import type { Timeframe } from "../types";
import { ChartSlot } from "./ChartSlot";

export type ChartGridProps = {
  heading?: string;
  pair: string;
  slots: readonly ChartSlotState[];
  timeframes: readonly Timeframe[];
  limitMessage?: string;
  announcement: string;
  onAdd(): void;
  onSetCount(count: ChartSlotPreset): void;
  onRemove(slotId: string): void;
  onTimeframeChange(slotId: string, timeframe: Timeframe): void;
  onRetry(slotId: string): void;
};

export function ChartGrid({
  heading,
  pair,
  slots,
  timeframes,
  limitMessage,
  announcement,
  onAdd,
  onSetCount,
  onRemove,
  onTimeframeChange,
  onRetry,
}: ChartGridProps) {
  const compact = slots.length >= 3;

  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col">
      <div
        role="group"
        aria-label="Chart workspace controls"
        className="mb-2 flex shrink-0 flex-wrap items-center gap-2 rounded-lg border border-subtle bg-surface px-2.5 py-2"
      >
        {heading !== undefined && (
          <h1 className="mr-2 shrink-0 text-lg font-semibold leading-6 tracking-tight text-ink">
            {heading}
          </h1>
        )}
        <label className="flex h-8 items-center gap-2 text-[11px] text-dim">
          <span className="hidden sm:inline">Pair / coin</span>
          <select
            id="select-pair"
            aria-label="Dashboard pair"
            title="Choose the market pair shown by every chart"
            value={pair}
            onChange={() => undefined}
            className="h-8 min-w-32 rounded-md border border-subtle bg-workspace px-2 font-mono text-xs font-semibold text-ink outline-none transition-colors hover:border-line focus:border-accent"
          >
            <option value={pair}>{pair}</option>
          </select>
        </label>
        <div
          role="group"
          aria-label="Chart count"
          className="inline-flex h-8 items-center gap-0.5 rounded-md border border-subtle bg-workspace p-0.5"
        >
          <span className="hidden px-1.5 text-[10px] font-medium text-faint lg:inline">
            Charts
          </span>
          {([1, 2, 4] as const).map((count) => {
            const selected = slots.length === count;
            return (
              <button
                key={count}
                type="button"
                aria-label={`Show ${count} chart${count === 1 ? "" : "s"}`}
                aria-pressed={selected}
                title={`Switch to ${count} chart${count === 1 ? "" : "s"}`}
                onClick={() => onSetCount(count)}
                className={`h-6 min-w-7 rounded px-1.5 font-mono text-[11px] font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/70 active:translate-y-px ${
                  selected
                    ? "bg-accent text-white shadow-[0_2px_8px_rgba(59,130,246,0.22)]"
                    : "text-dim hover:bg-surface hover:text-ink"
                }`}
              >
                {count}
              </button>
            );
          })}
        </div>
        <button
          id="btn-add-chart"
          type="button"
          title="Add another timeframe chart"
          onClick={onAdd}
          className="inline-flex h-8 items-center gap-1.5 rounded-md bg-accent px-3 text-xs font-semibold text-white transition-all hover:bg-accent-hover active:translate-y-px"
        >
          <Plus aria-hidden="true" size={16} />
          Add chart
        </button>
        <span className="ml-auto rounded-full border border-subtle bg-workspace px-2 py-1 text-[10px] font-medium text-faint">
          {slots.length} / 4 active charts
        </span>
      </div>

      <div aria-live="polite" role="status" className="sr-only">
        {announcement}
      </div>
      {limitMessage !== undefined && (
        <div
          id="message-chart-limit"
          role="alert"
          className="mb-2 shrink-0 rounded-md border border-warn/40 bg-warn/10 px-3 py-1.5 text-xs text-warn"
        >
          {limitMessage}
        </div>
      )}

      <div
        data-testid="chart-grid"
        data-density={compact ? "compact" : "comfortable"}
        className={`grid min-h-0 min-w-0 flex-1 grid-cols-1 gap-2 ${
          slots.length === 1 ? "md:grid-cols-1" : "md:grid-cols-2"
        } ${
          compact ? "xl:grid-rows-2" : ""
        }`}
      >
        {slots.map((slot) => (
          <ChartSlot
            key={slot.slotId}
            slot={slot}
            timeframes={timeframes}
            compact={compact}
            onTimeframeChange={onTimeframeChange}
            onRemove={onRemove}
            onRetry={onRetry}
          />
        ))}
      </div>
    </div>
  );
}
