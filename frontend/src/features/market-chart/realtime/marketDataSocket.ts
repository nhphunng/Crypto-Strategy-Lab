import { marketDataEventSchema } from "../schemas";
import {
  MARKET_DATA_SCHEMA_VERSION,
  type Candle,
  type CandleUpdatedEvent,
  type ConnectionState,
  type MarketDataCommand,
  type MarketDataErrorPayload,
  type MarketDataEvent,
  type MarketDataRealtimeErrorCode,
  type MarketSelection,
} from "../types";

export type MarketDataSlotSnapshot = {
  slotId: string;
  generation: number;
  selection: MarketSelection;
  candles: Candle[];
  connectionState: ConnectionState;
  attempt?: number;
  retryAfterMs?: number;
  lastEventAt?: string;
  reasonCode?: string;
  error?: MarketDataErrorPayload;
};

export type MarketDataSlotSubscription = {
  acceptHistory(candles: readonly Candle[]): boolean;
  release(): void;
};

export type SubscribeMarketDataSlot = {
  slotId: string;
  generation: number;
  selection: MarketSelection;
  onSnapshot(snapshot: MarketDataSlotSnapshot): void;
};

export type CreateMarketDataSocketOptions = {
  url: string;
  createSocket?: (url: string) => WebSocket;
  maxCandles?: number;
  now?: () => string;
  createRequestId?: () => string;
  maxRememberedEventIds?: number;
};

type SlotRuntime = {
  snapshot: MarketDataSlotSnapshot;
  onSnapshot(snapshot: MarketDataSlotSnapshot): void;
  bootstrapping: boolean;
  bufferedEvents: CandleUpdatedEvent[];
  revisions: Map<string, number>;
};

function selectionKey(selection: MarketSelection): string {
  return `${selection.provider}:${selection.pair}:${selection.timeframe}`;
}

function sameSelection(left: MarketSelection, right: MarketSelection): boolean {
  return selectionKey(left) === selectionKey(right);
}

function sameCandleValues(left: Candle, right: Candle): boolean {
  return (
    left.provider === right.provider &&
    left.pair === right.pair &&
    left.timeframe === right.timeframe &&
    left.openTime === right.openTime &&
    left.closeTime === right.closeTime &&
    left.open === right.open &&
    left.high === right.high &&
    left.low === right.low &&
    left.close === right.close &&
    left.volume === right.volume &&
    left.closed === right.closed
  );
}

function boundedHistory(
  candles: readonly Candle[],
  selection: MarketSelection,
  limit: number,
): Candle[] {
  const byIdentity = new Map<string, Candle>();
  for (const candle of candles) {
    if (sameSelection(candle, selection)) {
      byIdentity.set(candle.openTime, candle);
    }
  }
  return [...byIdentity.values()]
    .sort((left, right) => left.openTime.localeCompare(right.openTime))
    .slice(-limit);
}

function isRecovering(state: ConnectionState): boolean {
  return state === "STALE" || state === "RECONNECTING";
}

const RECOVERY_REASON_MESSAGES: Record<string, string> = {
  MARKET_RECOVERY_EXHAUSTED:
    "Automatic recovery exhausted. Retry to resume live data.",
  MARKET_GAP_RECOVERY_FAILED:
    "Gap recovery failed. The next automatic attempt will retry.",
  PROVIDER_DISCONNECTED: "The market provider disconnected.",
  PROVIDER_RATE_LIMITED: "The market provider is rate limited.",
};

function recoveryError(reasonCode?: string): MarketDataErrorPayload {
  const code = (reasonCode ?? "MARKET_RECOVERY_EXHAUSTED") as MarketDataRealtimeErrorCode;
  return {
    code,
    message: RECOVERY_REASON_MESSAGES[code] ?? code,
    retryable: true,
  };
}

export function parseMarketDataSocketMessage(message: string): MarketDataEvent {
  let decoded: unknown;
  try {
    decoded = JSON.parse(message) as unknown;
  } catch (error) {
    throw new Error("Market-data WebSocket message is not valid JSON", { cause: error });
  }
  return marketDataEventSchema.parse(decoded);
}

export class MarketDataSocket {
  private readonly url: string;
  private readonly createSocket: (url: string) => WebSocket;
  private readonly maxCandles: number;
  private readonly now: () => string;
  private readonly createRequestId: () => string;
  private readonly maxRememberedEventIds: number;
  private readonly slots = new Map<string, SlotRuntime>();
  private readonly outbound: MarketDataCommand[] = [];
  private readonly seenEventIds = new Set<string>();
  private readonly eventIdOrder: string[] = [];
  private socket: WebSocket | null = null;

  constructor(options: CreateMarketDataSocketOptions) {
    const maxCandles = options.maxCandles ?? 1_000;
    if (maxCandles < 1 || maxCandles > 1_000) {
      throw new Error("maxCandles must be between one and 1,000");
    }
    this.url = options.url;
    this.createSocket = options.createSocket ?? ((url) => new WebSocket(url));
    this.maxCandles = maxCandles;
    this.now = options.now ?? (() => new Date().toISOString());
    this.createRequestId = options.createRequestId ?? (() => crypto.randomUUID());
    this.maxRememberedEventIds = options.maxRememberedEventIds ?? 4_096;
    if (this.maxRememberedEventIds < 1) {
      throw new Error("maxRememberedEventIds must be positive");
    }
  }

  connect(): void {
    if (this.socket !== null) return;
    const socket = this.createSocket(this.url);
    this.socket = socket;
    socket.addEventListener("open", this.handleOpen);
    socket.addEventListener("message", this.handleMessage);
    socket.addEventListener("close", this.handleClose);
  }

  close(): void {
    const socket = this.socket;
    if (socket === null) return;
    socket.removeEventListener("open", this.handleOpen);
    socket.removeEventListener("message", this.handleMessage);
    socket.removeEventListener("close", this.handleClose);
    this.socket = null;
    socket.close();
  }

  subscribe(options: SubscribeMarketDataSlot): MarketDataSlotSubscription {
    if (!options.slotId || options.generation < 0) {
      throw new Error("slotId and a non-negative generation are required");
    }
    const previous = this.slots.get(options.slotId);
    if (previous !== undefined) {
      this.queueCommand({
        eventType: "UNSUBSCRIBE_MARKET_DATA",
        version: MARKET_DATA_SCHEMA_VERSION,
        requestId: this.createRequestId(),
        occurredAt: this.now(),
        payload: { slotId: options.slotId },
      });
    }

    const runtime: SlotRuntime = {
      snapshot: {
        slotId: options.slotId,
        generation: options.generation,
        selection: options.selection,
        candles: [],
        connectionState: "LOADING",
      },
      onSnapshot: options.onSnapshot,
      bootstrapping: true,
      bufferedEvents: [],
      revisions: new Map(),
    };
    this.slots.set(options.slotId, runtime);
    this.notify(runtime);
    this.queueCommand({
      eventType: "SUBSCRIBE_MARKET_DATA",
      version: MARKET_DATA_SCHEMA_VERSION,
      requestId: this.createRequestId(),
      occurredAt: this.now(),
      payload: { slotId: options.slotId, selection: options.selection },
    });

    const token = {
      slotId: options.slotId,
      generation: options.generation,
      selection: options.selection,
    };
    return {
      acceptHistory: (candles) => this.acceptHistory(token, candles),
      release: () => this.release(token),
    };
  }

  retry(slotId: string): void {
    if (!this.slots.has(slotId)) return;
    this.queueCommand({
      eventType: "RETRY_MARKET_DATA",
      version: MARKET_DATA_SCHEMA_VERSION,
      requestId: this.createRequestId(),
      occurredAt: this.now(),
      payload: { slotId },
    });
  }

  getSlotSnapshot(slotId: string): MarketDataSlotSnapshot | undefined {
    const runtime = this.slots.get(slotId);
    return runtime === undefined ? undefined : this.copySnapshot(runtime.snapshot);
  }

  private readonly handleOpen = (): void => {
    this.flushOutbound();
  };

  private readonly handleMessage = (event: MessageEvent): void => {
    if (typeof event.data !== "string") return;
    let parsed: MarketDataEvent;
    try {
      parsed = parseMarketDataSocketMessage(event.data);
    } catch {
      return;
    }
    if (!this.rememberEventId(parsed.eventId)) return;
    this.dispatch(parsed);
  };

  private readonly handleClose = (): void => {
    this.socket = null;
    for (const runtime of this.slots.values()) {
      runtime.snapshot = { ...runtime.snapshot, connectionState: "STALE" };
      this.notify(runtime);
    }
  };

  private dispatch(event: MarketDataEvent): void {
    if (event.eventType === "CANDLE_UPDATED") {
      for (const runtime of this.slots.values()) {
        if (!sameSelection(runtime.snapshot.selection, event.payload.selection)) continue;
        if (runtime.bootstrapping) {
          runtime.bufferedEvents.push(event);
        } else {
          this.applyCandleEvent(runtime, event);
        }
      }
      return;
    }
    if (event.eventType === "SUBSCRIPTION_STATE_CHANGED") {
      for (const slotId of event.payload.slotIds) {
        const runtime = this.slots.get(slotId);
        if (
          runtime !== undefined &&
          sameSelection(runtime.snapshot.selection, event.payload.selection)
        ) {
          runtime.snapshot = {
            ...runtime.snapshot,
            connectionState: event.payload.state,
            attempt: event.payload.attempt,
            ...(event.payload.retryAfterMs === undefined
              ? {}
              : { retryAfterMs: event.payload.retryAfterMs }),
            ...(event.payload.lastEventAt === undefined
              ? {}
              : { lastEventAt: event.payload.lastEventAt }),
            ...(event.payload.reasonCode === undefined
              ? {}
              : { reasonCode: event.payload.reasonCode }),
            error:
              event.payload.state === "ERROR"
                ? recoveryError(event.payload.reasonCode)
                : undefined,
          };
          this.notify(runtime);
        }
      }
      return;
    }
    const slotId = event.payload.slotId;
    if (slotId === undefined) return;
    const runtime = this.slots.get(slotId);
    if (runtime !== undefined) {
      runtime.snapshot = {
        ...runtime.snapshot,
        connectionState: "ERROR",
        error: event.payload,
      };
      this.notify(runtime);
    }
  }

  private applyCandleEvent(runtime: SlotRuntime, event: CandleUpdatedEvent): void {
    const incoming = event.payload.candle;
    const identity = incoming.openTime;
    const previousRevision = runtime.revisions.get(identity) ?? 0;
    if (event.payload.revision <= previousRevision) return;

    const candles = runtime.snapshot.candles;
    const index = candles.findIndex((item) => item.openTime === identity);
    if (index >= 0) {
      const accepted = candles[index];
      if (accepted.closed && !incoming.closed) return;
      if (accepted.closed && incoming.closed && !sameCandleValues(accepted, incoming)) return;
      if (sameCandleValues(accepted, incoming)) {
        runtime.revisions.set(identity, event.payload.revision);
        return;
      }
      const updated = [...candles];
      updated[index] = incoming;
      runtime.revisions.set(identity, event.payload.revision);
      runtime.snapshot = { ...runtime.snapshot, candles: updated };
      this.notify(runtime);
      return;
    }

    const tail = candles.at(-1);
    const recovering = isRecovering(runtime.snapshot.connectionState);
    if (tail !== undefined && incoming.openTime < tail.openTime && !recovering) {
      return;
    }
    runtime.revisions.set(identity, event.payload.revision);
    const updated = recovering
      ? [...candles, incoming]
          .sort((left, right) => left.openTime.localeCompare(right.openTime))
          .slice(-this.maxCandles)
      : [...candles, incoming].slice(-this.maxCandles);
    runtime.snapshot = {
      ...runtime.snapshot,
      candles: updated,
    };
    this.notify(runtime);
  }

  private acceptHistory(
    token: { slotId: string; generation: number; selection: MarketSelection },
    candles: readonly Candle[],
  ): boolean {
    const runtime = this.currentRuntime(token);
    if (runtime === undefined) return false;
    runtime.snapshot = {
      ...runtime.snapshot,
      candles: boundedHistory(candles, token.selection, this.maxCandles),
    };
    runtime.revisions.clear();
    runtime.bootstrapping = false;
    const buffered = runtime.bufferedEvents;
    runtime.bufferedEvents = [];
    this.notify(runtime);
    for (const event of buffered) this.applyCandleEvent(runtime, event);
    return true;
  }

  private release(token: {
    slotId: string;
    generation: number;
    selection: MarketSelection;
  }): void {
    if (this.currentRuntime(token) === undefined) return;
    this.slots.delete(token.slotId);
    this.queueCommand({
      eventType: "UNSUBSCRIBE_MARKET_DATA",
      version: MARKET_DATA_SCHEMA_VERSION,
      requestId: this.createRequestId(),
      occurredAt: this.now(),
      payload: { slotId: token.slotId },
    });
  }

  private currentRuntime(token: {
    slotId: string;
    generation: number;
    selection: MarketSelection;
  }): SlotRuntime | undefined {
    const runtime = this.slots.get(token.slotId);
    return runtime !== undefined &&
      runtime.snapshot.generation === token.generation &&
      sameSelection(runtime.snapshot.selection, token.selection)
      ? runtime
      : undefined;
  }

  private queueCommand(command: MarketDataCommand): void {
    this.outbound.push(command);
    this.flushOutbound();
  }

  private flushOutbound(): void {
    const socket = this.socket;
    if (socket === null || socket.readyState !== WebSocket.OPEN) return;
    while (this.outbound.length > 0) {
      const command = this.outbound.shift();
      if (command !== undefined) socket.send(JSON.stringify(command));
    }
  }

  private rememberEventId(eventId: string): boolean {
    if (this.seenEventIds.has(eventId)) return false;
    this.seenEventIds.add(eventId);
    this.eventIdOrder.push(eventId);
    while (this.eventIdOrder.length > this.maxRememberedEventIds) {
      const expired = this.eventIdOrder.shift();
      if (expired !== undefined) this.seenEventIds.delete(expired);
    }
    return true;
  }

  private notify(runtime: SlotRuntime): void {
    runtime.onSnapshot(this.copySnapshot(runtime.snapshot));
  }

  private copySnapshot(snapshot: MarketDataSlotSnapshot): MarketDataSlotSnapshot {
    return { ...snapshot, candles: [...snapshot.candles] };
  }
}

export function createMarketDataSocket(
  options: CreateMarketDataSocketOptions,
): MarketDataSocket {
  return new MarketDataSocket(options);
}
