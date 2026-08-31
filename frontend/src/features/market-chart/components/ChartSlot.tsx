import { RefreshCw, Trash2 } from "lucide-react";

import type { ChartSlotState } from "../hooks/useChartSlot";
import type { Timeframe } from "../types";
import { CandlestickChart } from "./CandlestickChart";
import { ConnectionStatus } from "./ConnectionStatus";

export type ChartSlotProps = {
  slot: ChartSlotState;
  timeframes: readonly Timeframe[];
  compact?: boolean;
  onTimeframeChange(slotId: string, timeframe: Timeframe): void;
  onRemove(slotId: string): void;
  onRetry(slotId: string): void;
};

export function ChartSlot({
  slot,
  timeframes,
  compact = false,
  onTimeframeChange,
  onRemove,
  onRetry,
}: ChartSlotProps) {
  const pairSlug = slot.pair.toLowerCase();
  const label = `${slot.pair} ${slot.timeframe} chart`;
  return (
    <section
      id={`chart-${pairSlug}-${slot.timeframe}-${slot.slotId}`}
      aria-label={label}
      aria-busy={slot.connectionState === "LOADING"}
      data-generation={slot.generation}
      data-layout-density={compact ? "compact" : "comfortable"}
      className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-lg border border-line bg-surface shadow-[0_12px_28px_rgba(2,8,18,0.16)] transition-colors hover:border-slate-600"
    >
      <header className="flex min-h-11 shrink-0 items-center gap-2 border-b border-subtle px-2.5 py-1.5">
        <div className="mr-auto min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-semibold tracking-tight text-ink">
              {slot.pair}
            </span>
            <ConnectionStatus
              slotId={slot.slotId}
              connectionState={slot.connectionState}
              lastEventAt={slot.lastEventAt}
              attempt={slot.attempt}
              error={slot.error}
            />
          </div>
          <div className="truncate text-[10px] leading-3 text-faint">Chart {slot.slotId}</div>
        </div>
        <label className="flex h-8 shrink-0 items-center gap-1.5 rounded-md border border-subtle bg-workspace pl-2 text-[11px] text-dim transition-colors focus-within:border-accent hover:border-line">
          <span className="hidden sm:inline">Timeframe</span>
          <select
            id={`select-timeframe-${slot.slotId}`}
            aria-label={`Timeframe for ${slot.pair} chart ${slot.slotId}`}
            title={`Choose timeframe for ${slot.pair} chart ${slot.slotId}`}
            value={slot.timeframe}
            onChange={(event) =>
              onTimeframeChange(slot.slotId, event.currentTarget.value as Timeframe)
            }
            className="h-full rounded-r-md border-0 bg-surface px-2 font-mono text-xs font-medium text-ink outline-none"
          >
            {timeframes.map((timeframe) => (
              <option key={timeframe} value={timeframe}>
                {timeframe}
              </option>
            ))}
          </select>
        </label>
        {slot.connectionState === "ERROR" && slot.error?.retryable && (
          <button
            id={`btn-retry-chart-${slot.slotId}`}
            type="button"
            title="Retry market data for this chart"
            onClick={() => onRetry(slot.slotId)}
            className="inline-flex h-8 items-center gap-1.5 rounded-md border border-warn/50 px-2 text-[11px] font-medium text-warn transition-colors hover:bg-warn/10"
          >
            <RefreshCw aria-hidden="true" size={14} />
            Retry market data
          </button>
        )}
        <button
          id={`btn-remove-chart-${slot.slotId}`}
          type="button"
          aria-label={`Remove chart ${slot.slotId}`}
          title={`Remove chart ${slot.slotId}`}
          onClick={() => onRemove(slot.slotId)}
          className="inline-flex h-8 min-w-8 items-center justify-center rounded-md border border-subtle text-dim transition-all hover:border-neg/40 hover:bg-neg/10 hover:text-neg active:translate-y-px"
        >
          <Trash2 aria-hidden="true" size={15} />
        </button>
      </header>

      <div
        className="min-h-0 flex-1 bg-[#0b111a] p-1.5"
        data-chart-lifecycle={`${slot.slotId}:${slot.generation}:${slot.connectionState}`}
      >
        <CandlestickChart
          key={`${slot.slotId}:${slot.generation}`}
          candles={slot.candles}
          height={compact ? 200 : 360}
          className="h-full text-dim"
        />
      </div>
    </section>
  );
}
