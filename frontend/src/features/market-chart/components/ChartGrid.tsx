import { Plus } from "lucide-react";

import type { ChartSlotState } from "../hooks/useChartSlot";
import type { Timeframe } from "../types";
import { ChartSlot } from "./ChartSlot";

export type ChartGridProps = {
  pair: string;
  slots: readonly ChartSlotState[];
  timeframes: readonly Timeframe[];
  limitMessage?: string;
  announcement: string;
  onAdd(): void;
  onRemove(slotId: string): void;
  onTimeframeChange(slotId: string, timeframe: Timeframe): void;
  onRetry(slotId: string): void;
};

export function ChartGrid({
  pair,
  slots,
  timeframes,
  limitMessage,
  announcement,
  onAdd,
  onRemove,
  onTimeframeChange,
  onRetry,
}: ChartGridProps) {
  return (
    <div className="min-w-0">
      <div className="mb-3 flex flex-wrap items-end gap-3">
        <label className="flex min-h-11 flex-col justify-center gap-1 text-xs text-dim">
          Dashboard pair
          <select
            id="select-pair"
            aria-label="Dashboard pair"
            value={pair}
            onChange={() => undefined}
            className="h-9 min-w-40 rounded-md border border-subtle bg-workspace px-2 font-mono text-sm text-ink"
          >
            <option value={pair}>{pair}</option>
          </select>
        </label>
        <button
          id="btn-add-chart"
          type="button"
          onClick={onAdd}
          className="inline-flex min-h-11 items-center gap-2 rounded-md bg-accent px-4 text-sm font-semibold text-white hover:bg-accent-hover"
        >
          <Plus aria-hidden="true" size={16} />
          Add chart
        </button>
        <span className="text-xs text-faint">{slots.length} / 4 active charts</span>
      </div>

      <div aria-live="polite" role="status" className="sr-only">
        {announcement}
      </div>
      {limitMessage !== undefined && (
        <div
          id="message-chart-limit"
          role="alert"
          className="mb-3 rounded-md border border-warn/40 bg-warn/10 px-3 py-2 text-sm text-warn"
        >
          {limitMessage}
        </div>
      )}

      <div
        data-testid="chart-grid"
        className="grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2"
      >
        {slots.map((slot) => (
          <ChartSlot
            key={slot.slotId}
            slot={slot}
            timeframes={timeframes}
            onTimeframeChange={onTimeframeChange}
            onRemove={onRemove}
            onRetry={onRetry}
          />
        ))}
      </div>
    </div>
  );
}
