import { RefreshCw, Trash2 } from "lucide-react";

import type { ChartSlotState } from "../hooks/useChartSlot";
import type { Timeframe } from "../types";
import { CandlestickChart } from "./CandlestickChart";
import { ConnectionStatus } from "./ConnectionStatus";

export type ChartSlotProps = {
  slot: ChartSlotState;
  timeframes: readonly Timeframe[];
  onTimeframeChange(slotId: string, timeframe: Timeframe): void;
  onRemove(slotId: string): void;
  onRetry(slotId: string): void;
};

export function ChartSlot({
  slot,
  timeframes,
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
      className="min-w-0 overflow-hidden rounded-lg border border-line bg-surface"
    >
      <header className="flex flex-wrap items-center gap-3 border-b border-subtle px-3 py-2">
        <div className="mr-auto">
          <div className="font-mono text-xs font-semibold text-ink">{slot.pair}</div>
          <div className="text-[11px] text-faint">Chart {slot.slotId}</div>
        </div>
        <label className="flex min-h-11 items-center gap-2 text-xs text-dim">
          <span>Timeframe</span>
          <select
            id={`select-timeframe-${slot.slotId}`}
            aria-label={`Timeframe for ${slot.pair} chart ${slot.slotId}`}
            value={slot.timeframe}
            onChange={(event) =>
              onTimeframeChange(slot.slotId, event.currentTarget.value as Timeframe)
            }
            className="h-9 rounded-md border border-subtle bg-workspace px-2 font-mono text-xs text-ink"
          >
            {timeframes.map((timeframe) => (
              <option key={timeframe} value={timeframe}>
                {timeframe}
              </option>
            ))}
          </select>
        </label>
        <button
          id={`btn-remove-chart-${slot.slotId}`}
          type="button"
          aria-label={`Remove chart ${slot.slotId}`}
          onClick={() => onRemove(slot.slotId)}
          className="inline-flex h-11 min-w-11 items-center justify-center rounded-md border border-subtle text-dim hover:bg-surface-hover hover:text-neg"
        >
          <Trash2 aria-hidden="true" size={16} />
        </button>
      </header>

      <div className="flex min-h-10 flex-wrap items-center gap-3 border-b border-subtle px-3 py-1.5">
        <ConnectionStatus
          slotId={slot.slotId}
          connectionState={slot.connectionState}
          lastEventAt={slot.lastEventAt}
          attempt={slot.attempt}
          error={slot.error}
        />
        {slot.connectionState === "ERROR" && slot.error?.retryable && (
          <button
            id={`btn-retry-chart-${slot.slotId}`}
            type="button"
            onClick={() => onRetry(slot.slotId)}
            className="ml-auto inline-flex min-h-11 items-center gap-2 rounded-md border border-warn/50 px-3 text-xs font-medium text-warn hover:bg-warn/10"
          >
            <RefreshCw aria-hidden="true" size={14} />
            Retry market data
          </button>
        )}
      </div>

      <div
        className="min-h-64 p-2"
        data-chart-lifecycle={`${slot.slotId}:${slot.generation}:${slot.connectionState}`}
      >
        <CandlestickChart
          key={`${slot.slotId}:${slot.generation}`}
          candles={slot.candles}
          height={260}
          className="h-full text-dim"
        />
      </div>
    </section>
  );
}
