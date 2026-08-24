import { useCallback } from "react";

import type {
  MarketDataSlotSnapshot,
  MarketDataSocket,
} from "../realtime/marketDataSocket";
import type { MarketSelection } from "../types";
import type { ChartSlotState } from "./useChartSlot";

export type UseMarketDataConnectionOptions = {
  socket?: Pick<MarketDataSocket, "retry">;
  getSlots(): readonly ChartSlotState[];
  setSlots(update: (slots: ChartSlotState[]) => ChartSlotState[]): void;
  isActive(slotId: string, generation: number, selection: MarketSelection): boolean;
  setAnnouncement(message: string): void;
};

export type MarketDataConnectionController = {
  applySnapshot(snapshot: MarketDataSlotSnapshot): void;
  retrySlot(slotId: string): void;
};

/**
 * Dispatches socket connection snapshots into slot state and owns the manual
 * retry command. Each snapshot is guarded by the slot's current lifecycle so
 * stale generations and unrelated selections never change a healthy slot.
 */
export function useMarketDataConnection(
  options: UseMarketDataConnectionOptions,
): MarketDataConnectionController {
  const { socket, getSlots, setSlots, isActive, setAnnouncement } = options;

  const applySnapshot = useCallback(
    (snapshot: MarketDataSlotSnapshot) => {
      if (!isActive(snapshot.slotId, snapshot.generation, snapshot.selection)) {
        return;
      }
      const current = getSlots();
      const updated = current.map((slot) =>
        slot.slotId === snapshot.slotId && slot.generation === snapshot.generation
          ? {
              ...slot,
              candles: [...snapshot.candles],
              connectionState: snapshot.connectionState,
              attempt: snapshot.attempt,
              retryAfterMs: snapshot.retryAfterMs,
              lastEventAt: snapshot.lastEventAt,
              reasonCode: snapshot.reasonCode,
              error: snapshot.error,
            }
          : slot,
      );
      if (updated.every((slot, index) => slot === current[index])) return;
      setSlots(() => updated);
    },
    [getSlots, isActive, setSlots],
  );

  const retrySlot = useCallback(
    (slotId: string) => {
      socket?.retry(slotId);
      const current = getSlots();
      const updated = current.map((slot) =>
        slot.slotId !== slotId
          ? slot
          : {
              ...slot,
              connectionState: "RECONNECTING" as const,
              error: undefined,
              retrySequence: slot.retrySequence + 1,
            },
      );
      if (updated.some((slot, index) => slot !== current[index])) {
        setSlots(() => updated);
      }
      setAnnouncement(`Retrying chart ${slotId}.`);
    },
    [getSlots, setAnnouncement, setSlots, socket],
  );

  return { applySnapshot, retrySlot };
}