/** Public market-data contract version accepted by TV1 and TV2. */
export const MARKET_DATA_SCHEMA_VERSION = "1" as const;
export const MARKET_DATA_VERSION = MARKET_DATA_SCHEMA_VERSION;

export const MARKET_DATA_PROVIDERS = ["BINANCE"] as const;
export const PROVIDERS = MARKET_DATA_PROVIDERS;
export type Provider = (typeof MARKET_DATA_PROVIDERS)[number];

export const MARKET_DATA_TIMEFRAMES = [
  "1m",
  "5m",
  "15m",
  "30m",
  "1h",
  "2h",
  "4h",
  "1d",
] as const;
export const TIMEFRAMES = MARKET_DATA_TIMEFRAMES;
export type Timeframe = (typeof MARKET_DATA_TIMEFRAMES)[number];

export const CANDLE_RANGE_COMPLETENESS = ["COMPLETE", "PARTIAL", "EMPTY"] as const;
export const COMPLETENESS_VALUES = CANDLE_RANGE_COMPLETENESS;
export type Completeness = (typeof CANDLE_RANGE_COMPLETENESS)[number];

/** States sent in SUBSCRIPTION_STATE_CHANGED events. */
export const MARKET_DATA_WIRE_STATES = [
  "LOADING",
  "LIVE",
  "STALE",
  "RECONNECTING",
  "ERROR",
] as const;
export type MarketDataWireState = (typeof MARKET_DATA_WIRE_STATES)[number];
export type SubscriptionState = MarketDataWireState;

/** RELEASED is client/server lifecycle state and is never serialized as a wire state. */
export const CONNECTION_STATES = [...MARKET_DATA_WIRE_STATES, "RELEASED"] as const;
export type ConnectionState = (typeof CONNECTION_STATES)[number];
export type ConnectionStatus = ConnectionState;

export const MARKET_DATA_REST_ERROR_CODES = [
  "MARKET_REQUEST_MALFORMED",
  "MARKET_PAIR_UNSUPPORTED",
  "MARKET_TIMEFRAME_UNSUPPORTED",
  "MARKET_RANGE_INVALID",
  "MARKET_RANGE_TOO_LARGE",
  "PROVIDER_RATE_LIMITED",
  "MARKET_PROVIDER_UNAVAILABLE",
] as const;
export type MarketDataRestErrorCode = (typeof MARKET_DATA_REST_ERROR_CODES)[number];

export const MARKET_DATA_REALTIME_ERROR_CODES = [
  "MARKET_SUBSCRIPTION_LIMIT_REACHED",
  "MARKET_PAIR_UNSUPPORTED",
  "MARKET_TIMEFRAME_UNSUPPORTED",
  "MARKET_EVENT_VERSION_UNSUPPORTED",
  "PROVIDER_RATE_LIMITED",
  "PROVIDER_DISCONNECTED",
  "MARKET_GAP_RECOVERY_FAILED",
  "MARKET_RECOVERY_EXHAUSTED",
] as const;
export type MarketDataRealtimeErrorCode =
  (typeof MARKET_DATA_REALTIME_ERROR_CODES)[number];
export type MarketDataErrorCode =
  | MarketDataRestErrorCode
  | MarketDataRealtimeErrorCode;

export const MARKET_DATA_COMMAND_TYPES = [
  "SUBSCRIBE_MARKET_DATA",
  "UNSUBSCRIBE_MARKET_DATA",
  "RETRY_MARKET_DATA",
] as const;
export type MarketDataCommandType = (typeof MARKET_DATA_COMMAND_TYPES)[number];

export const MARKET_DATA_EVENT_TYPES = [
  "SUBSCRIPTION_STATE_CHANGED",
  "CANDLE_UPDATED",
  "MARKET_DATA_ERROR",
] as const;
export type MarketDataEventType = (typeof MARKET_DATA_EVENT_TYPES)[number];

/** Validated non-negative base-10 value serialized without exponent notation. */
export type DecimalString = string;
/** Validated RFC 3339 UTC instant serialized with a trailing Z. */
export type UtcTimestamp = string;
/** Validated stable uppercase code such as PROVIDER_DISCONNECTED. */
export type UppercaseReasonCode = string;

export type MarketSelection = {
  provider: Provider;
  pair: string;
  timeframe: Timeframe;
};

/** Shared TV1-owned Candle boundary consumed by the chart feature. */
export type Candle = MarketSelection & {
  openTime: UtcTimestamp;
  closeTime: UtcTimestamp;
  open: DecimalString;
  high: DecimalString;
  low: DecimalString;
  close: DecimalString;
  volume: DecimalString;
  closed: boolean;
  receivedAt: UtcTimestamp;
};

export type TimeRange = {
  startTime: UtcTimestamp;
  endTime: UtcTimestamp;
};

export type CandleRange = {
  schemaVersion: typeof MARKET_DATA_SCHEMA_VERSION;
  selection: MarketSelection;
  range: TimeRange;
  completeness: Completeness;
  missingRanges: TimeRange[];
  candles: Candle[];
};

export type MarketDimensions = {
  schemaVersion: typeof MARKET_DATA_SCHEMA_VERSION;
  providers: Provider[];
  pairs: string[];
  timeframes: Timeframe[];
};

export type SuccessEnvelope<T> = {
  success: true;
  message: string;
  data: T;
  timestamp: UtcTimestamp;
  requestId: string;
};

export type CandleRangeEnvelope = SuccessEnvelope<CandleRange>;
export type MarketDimensionsEnvelope = SuccessEnvelope<MarketDimensions>;

export type MarketDataRestErrorDetail = {
  code: MarketDataRestErrorCode;
  retryable: boolean;
  details?: Record<string, unknown> | null;
};

export type MarketDataRestErrorEnvelope = {
  success: false;
  message: string;
  error: MarketDataRestErrorDetail;
  timestamp: UtcTimestamp;
  requestId: string;
};

export type MarketDataRestResponse<T> =
  | SuccessEnvelope<T>
  | MarketDataRestErrorEnvelope;

type ClientCommandEnvelope<TType extends MarketDataCommandType, TPayload> = {
  eventType: TType;
  version: typeof MARKET_DATA_SCHEMA_VERSION;
  requestId: string;
  occurredAt: UtcTimestamp;
  payload: TPayload;
};

export type SubscribeMarketDataCommand = ClientCommandEnvelope<
  "SUBSCRIBE_MARKET_DATA",
  { slotId: string; selection: MarketSelection }
>;

export type UnsubscribeMarketDataCommand = ClientCommandEnvelope<
  "UNSUBSCRIBE_MARKET_DATA",
  { slotId: string }
>;

export type RetryMarketDataCommand = ClientCommandEnvelope<
  "RETRY_MARKET_DATA",
  { slotId: string }
>;

export type MarketDataCommand =
  | SubscribeMarketDataCommand
  | UnsubscribeMarketDataCommand
  | RetryMarketDataCommand;

type ServerEventEnvelope<TType extends MarketDataEventType, TPayload> = {
  eventType: TType;
  version: typeof MARKET_DATA_SCHEMA_VERSION;
  eventId: string;
  requestId?: string;
  occurredAt: UtcTimestamp;
  payload: TPayload;
};

export type SubscriptionStateChangedPayload = {
  slotIds: string[];
  selection: MarketSelection;
  state: MarketDataWireState;
  attempt: number;
  retryAfterMs?: number;
  lastEventAt?: UtcTimestamp;
  reasonCode?: UppercaseReasonCode;
};

export type SubscriptionStateChangedEvent = ServerEventEnvelope<
  "SUBSCRIPTION_STATE_CHANGED",
  SubscriptionStateChangedPayload
>;

export type CandleUpdatedPayload = {
  selection: MarketSelection;
  revision: number;
  candle: Candle;
};

export type CandleUpdatedEvent = ServerEventEnvelope<
  "CANDLE_UPDATED",
  CandleUpdatedPayload
>;

export type MarketDataErrorPayload = {
  slotId?: string;
  code: MarketDataRealtimeErrorCode;
  message: string;
  retryable: boolean;
};

export type MarketDataErrorEvent = ServerEventEnvelope<
  "MARKET_DATA_ERROR",
  MarketDataErrorPayload
>;

export type MarketDataEvent =
  | SubscriptionStateChangedEvent
  | CandleUpdatedEvent
  | MarketDataErrorEvent;
