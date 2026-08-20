import type { QueryClient, QueryKey } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  createMarketHistoryQueryOptions,
  type MarketDataApi,
} from "../api/marketDataApi";
import { useMarketDataConnection } from "./useMarketDataConnection";
import type {
  MarketDataSlotSubscription,
  MarketDataSocket,
} from "../realtime/marketDataSocket";
import type {
  Candle,
  ConnectionState,
  MarketDataErrorPayload,
  MarketSelection,
  Provider,
  TimeRange,
  Timeframe,
} from "../types";

export const MAX_CHART_SLOTS = 4;
export const CHART_SLOT_LIMIT_MESSAGE =
  "A dashboard can use at most four chart slots.";
export type ChartSlotPreset = 1 | 2 | 4;

export type ChartSlotState = {
  slotId: string;
  pair: string;
  timeframe: Timeframe;
  generation: number;
  candles: Candle[];
  connectionState: ConnectionState;
  lastEventAt?: string;
  attempt?: number;
  retryAfterMs?: number;
  reasonCode?: string;
  error?: MarketDataErrorPayload;
  retrySequence: number;
  viewport?: unknown;
};

export type UseChartSlotsOptions = {
  provider: Provider;
  pair: string;
  defaultTimeframe: Timeframe;
  initialTimeframes: readonly Timeframe[];
  createSlotId?: () => string;
  marketData?: ChartMarketDataLifecycle;
};

export type ChartMarketDataLifecycle = {
  api: Pick<MarketDataApi, "getCandles">;
  socket: Pick<MarketDataSocket, "subscribe" | "retry">;
  queryClient: QueryClient;
  historyRange: TimeRange | ((selection: MarketSelection) => TimeRange);
  historyLimit: number;
};

type ActiveSlotLifecycle = {
  generation: number;
  selection: MarketSelection;
  queryClient: QueryClient;
  queryKey: QueryKey;
  queryHash: string;
  subscription: MarketDataSlotSubscription;
};

function defaultSlotIdFactory(): () => string {
  let sequence = 0;
  return () => `slot-${++sequence}`;
}

export function useChartSlots(options: UseChartSlotsOptions) {
  if (options.initialTimeframes.length < 1) {
    throw new Error("A dashboard requires at least one chart slot.");
  }
  if (options.initialTimeframes.length > MAX_CHART_SLOTS) {
    throw new Error(CHART_SLOT_LIMIT_MESSAGE);
  }
  const createSlotId = useRef(options.createSlotId ?? defaultSlotIdFactory());
  const initialSlots = useRef<ChartSlotState[] | null>(null);
  if (initialSlots.current === null) {
    initialSlots.current = options.initialTimeframes.map((timeframe) => ({
      slotId: createSlotId.current(),
      pair: options.pair,
      timeframe,
      generation: 1,
      candles: [],
      connectionState: "LOADING",
      retrySequence: 0,
    }));
  }
  const [slots, setSlots] = useState<ChartSlotState[]>(initialSlots.current);
  const slotsRef = useRef(slots);
  slotsRef.current = slots;
  const [limitMessage, setLimitMessage] = useState<string>();
  const [announcement, setAnnouncement] = useState(
    `${options.initialTimeframes.length} chart slot${
      options.initialTimeframes.length === 1 ? "" : "s"
    } ready.`,
  );
  const activeLifecycles = useRef(new Map<string, ActiveSlotLifecycle>());

  const getSlots = useCallback(() => slotsRef.current, []);
  const setSlotsNow = useCallback(
    (update: (slots: ChartSlotState[]) => ChartSlotState[]) => {
      const next = update(slotsRef.current);
      slotsRef.current = next;
      setSlots(next);
    },
    [],
  );
  const isActive = useCallback(
    (slotId: string, generation: number, selection: MarketSelection) => {
      const active = activeLifecycles.current.get(slotId);
      return (
        active !== undefined &&
        active.generation === generation &&
        sameSelection(active.selection, selection)
      );
    },
    [],
  );
  const { applySnapshot, retrySlot } = useMarketDataConnection({
    socket: options.marketData?.socket,
    getSlots,
    setSlots: setSlotsNow,
    isActive,
    setAnnouncement,
  });

  const addSlot = useCallback(() => {
    const current = slotsRef.current;
    if (current.length >= MAX_CHART_SLOTS) {
      setLimitMessage(CHART_SLOT_LIMIT_MESSAGE);
      setAnnouncement(CHART_SLOT_LIMIT_MESSAGE);
      return;
    }
    const slot: ChartSlotState = {
      slotId: createSlotId.current(),
      pair: options.pair,
      timeframe: options.defaultTimeframe,
      generation: 1,
      candles: [],
      connectionState: "LOADING",
      retrySequence: 0,
    };
    const updated = [...current, slot];
    slotsRef.current = updated;
    setSlots(updated);
    setLimitMessage(undefined);
    setAnnouncement(`Chart ${slot.slotId} added.`);
  }, [options.defaultTimeframe, options.pair]);

  const removeSlot = useCallback((slotId: string) => {
    const current = slotsRef.current;
    if (current.length === 1) {
      setAnnouncement("A dashboard requires at least one chart slot.");
      return;
    }
    const updated = current.filter((slot) => slot.slotId !== slotId);
    if (updated.length === current.length) return;
    slotsRef.current = updated;
    setSlots(updated);
    setLimitMessage(undefined);
    setAnnouncement(`Chart ${slotId} removed.`);
  }, []);

  const setSlotCount = useCallback(
    (targetCount: ChartSlotPreset) => {
      const current = slotsRef.current;
      if (current.length === targetCount) {
        setAnnouncement(
          `${targetCount} chart slot${targetCount === 1 ? " is" : "s are"} already active.`,
        );
        return;
      }

      const updated = current.slice(0, targetCount);
      while (updated.length < targetCount) {
        updated.push({
          slotId: createSlotId.current(),
          pair: options.pair,
          timeframe: options.defaultTimeframe,
          generation: 1,
          candles: [],
          connectionState: "LOADING",
          retrySequence: 0,
        });
      }
      slotsRef.current = updated;
      setSlots(updated);
      setLimitMessage(undefined);
      setAnnouncement(
        `Dashboard now shows ${targetCount} chart slot${targetCount === 1 ? "" : "s"}.`,
      );
    },
    [options.defaultTimeframe, options.pair],
  );

  const changeTimeframe = useCallback((slotId: string, timeframe: Timeframe) => {
    const current = slotsRef.current;
    const updated: ChartSlotState[] = current.map((slot) =>
        slot.slotId !== slotId || slot.timeframe === timeframe
          ? slot
          : {
              ...slot,
              timeframe,
              generation: slot.generation + 1,
              candles: [],
              connectionState: "LOADING",
              error: undefined,
            },
    );
    if (updated.some((slot, index) => slot !== current[index])) {
      slotsRef.current = updated;
      setSlots(updated);
    }
    setAnnouncement(`Chart ${slotId} timeframe changed to ${timeframe}.`);
  }, []);

  useEffect(() => {
    const marketData = options.marketData;
    const activeSlotIds = new Set(slots.map((slot) => slot.slotId));

    for (const [slotId, active] of activeLifecycles.current) {
      const slot = slots.find((candidate) => candidate.slotId === slotId);
      const selection =
        slot === undefined
          ? undefined
          : toSelection(options.provider, options.pair, slot.timeframe);
      if (
        marketData !== undefined &&
        slot !== undefined &&
        slot.generation === active.generation &&
        selection !== undefined &&
        sameSelection(selection, active.selection)
      ) {
        continue;
      }
      activeLifecycles.current.delete(slotId);
      releaseLifecycle(active);
    }

    if (marketData === undefined) return;

    for (const slot of slots) {
      if (!activeSlotIds.has(slot.slotId) || activeLifecycles.current.has(slot.slotId)) {
        continue;
      }
      const selection = toSelection(options.provider, options.pair, slot.timeframe);
      const range =
        typeof marketData.historyRange === "function"
          ? marketData.historyRange(selection)
          : marketData.historyRange;
      const query = createMarketHistoryQueryOptions({
        api: marketData.api,
        selection,
        range,
        limit: marketData.historyLimit,
        generation: slot.generation,
      });
      const subscription = marketData.socket.subscribe({
        slotId: slot.slotId,
        generation: slot.generation,
        selection,
        onSnapshot: applySnapshot,
      });
      const active: ActiveSlotLifecycle = {
        generation: slot.generation,
        selection,
        queryClient: marketData.queryClient,
        queryKey: query.queryKey,
        queryHash: JSON.stringify(query.queryKey),
        subscription,
      };
      activeLifecycles.current.set(slot.slotId, active);
      void marketData.queryClient
        .fetchQuery(query)
        .then((history) => {
          if (activeLifecycles.current.get(slot.slotId) !== active) return;
          active.subscription.acceptHistory(history.candles);
        })
        .catch(() => undefined);
    }
  }, [applySnapshot, options.marketData, options.pair, options.provider, slots]);

  useEffect(
    () => () => {
      const active = [...activeLifecycles.current.values()];
      activeLifecycles.current.clear();
      for (const lifecycle of active) releaseLifecycle(lifecycle);
    },
    [],
  );

  return {
    provider: options.provider,
    pair: options.pair,
    slots,
    limitMessage,
    announcement,
    addSlot,
    setSlotCount,
    removeSlot,
    changeTimeframe,
    retrySlot,
  };

  function releaseLifecycle(active: ActiveSlotLifecycle) {
    active.subscription.release();
    const shared = [...activeLifecycles.current.values()].some(
      (candidate) => candidate.queryHash === active.queryHash,
    );
    if (!shared) {
      void active.queryClient.cancelQueries({ queryKey: active.queryKey, exact: true });
      active.queryClient.removeQueries({ queryKey: active.queryKey, exact: true });
    }
  }
}

function toSelection(
  provider: Provider,
  pair: string,
  timeframe: Timeframe,
): MarketSelection {
  return { provider, pair, timeframe };
}

function sameSelection(left: MarketSelection, right: MarketSelection) {
  return (
    left.provider === right.provider &&
    left.pair === right.pair &&
    left.timeframe === right.timeframe
  );
}
