import {
  CANDLE_RANGE_COMPLETENESS,
  CONNECTION_STATES,
  MARKET_DATA_COMMAND_TYPES,
  MARKET_DATA_EVENT_TYPES,
  MARKET_DATA_PROVIDERS,
  MARKET_DATA_REALTIME_ERROR_CODES,
  MARKET_DATA_REST_ERROR_CODES,
  MARKET_DATA_SCHEMA_VERSION,
  MARKET_DATA_TIMEFRAMES,
  MARKET_DATA_WIRE_STATES,
  type Candle,
  type CandleRange,
  type CandleRangeEnvelope,
  type Completeness,
  type ConnectionState,
  type DecimalString,
  type MarketDataCommand,
  type MarketDataCommandType,
  type MarketDataErrorEvent,
  type MarketDataEvent,
  type MarketDataEventType,
  type MarketDataRealtimeErrorCode,
  type MarketDataRestErrorCode,
  type MarketDataRestErrorEnvelope,
  type MarketDataWireState,
  type MarketDimensions,
  type MarketDimensionsEnvelope,
  type MarketSelection,
  type Provider,
  type SubscriptionStateChangedEvent,
  type SuccessEnvelope,
  type Timeframe,
  type TimeRange,
  type UtcTimestamp,
  type UppercaseReasonCode,
} from "./types";

export type SafeParseResult<T> =
  | { success: true; data: T }
  | { success: false; error: MarketDataSchemaError };

export type RuntimeSchema<T> = {
  parse(value: unknown): T;
  safeParse(value: unknown): SafeParseResult<T>;
  is(value: unknown): value is T;
};

export class MarketDataSchemaError extends Error {
  readonly path: string;

  constructor(path: string, reason: string) {
    super(`${path}: ${reason}`);
    this.name = "MarketDataSchemaError";
    this.path = path;
  }
}

type JsonObject = Record<string, unknown>;

const DECIMAL_PATTERN = /^(0|[1-9][0-9]*)(\.[0-9]+)?$/;
const PAIR_PATTERN = /^[A-Z0-9]{5,20}$/;
const UPPERCASE_CODE_PATTERN = /^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*$/;
const UTC_TIMESTAMP_PATTERN =
  /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?Z$/;

function schema<T>(parser: (value: unknown) => T): RuntimeSchema<T> {
  return {
    parse: parser,
    safeParse(value) {
      try {
        return { success: true, data: parser(value) };
      } catch (error) {
        return {
          success: false,
          error:
            error instanceof MarketDataSchemaError
              ? error
              : new MarketDataSchemaError("$", "validation failed"),
        };
      }
    },
    is(value): value is T {
      try {
        parser(value);
        return true;
      } catch {
        return false;
      }
    },
  };
}

function fail(path: string, reason: string): never {
  throw new MarketDataSchemaError(path, reason);
}

function readObject(value: unknown, path: string): JsonObject {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return fail(path, "expected an object");
  }
  return value as JsonObject;
}

function assertExactKeys(value: JsonObject, keys: readonly string[], path: string): void {
  const allowed = new Set(keys);
  const unexpected = Object.keys(value).filter((key) => !allowed.has(key));
  if (unexpected.length > 0) {
    fail(path, `unexpected field${unexpected.length === 1 ? "" : "s"}: ${unexpected.join(", ")}`);
  }
}

function readString(value: unknown, path: string): string {
  if (typeof value !== "string") {
    return fail(path, "expected a string");
  }
  return value;
}

function readNonEmptyString(value: unknown, path: string): string {
  const parsed = readString(value, path);
  if (parsed.trim().length === 0) {
    return fail(path, "expected a non-empty string");
  }
  return parsed;
}

function readBoolean(value: unknown, path: string): boolean {
  if (typeof value !== "boolean") {
    return fail(path, "expected a boolean");
  }
  return value;
}

function readInteger(
  value: unknown,
  path: string,
  minimum = Number.MIN_SAFE_INTEGER,
  maximum = Number.MAX_SAFE_INTEGER,
): number {
  if (!Number.isSafeInteger(value) || (value as number) < minimum || (value as number) > maximum) {
    return fail(path, `expected an integer from ${minimum} to ${maximum}`);
  }
  return value as number;
}

function readEnum<const T extends readonly string[]>(
  value: unknown,
  allowed: T,
  path: string,
): T[number] {
  if (typeof value !== "string" || !(allowed as readonly string[]).includes(value)) {
    return fail(path, `expected one of ${allowed.join(", ")}`);
  }
  return value as T[number];
}

function hasOwn(value: JsonObject, key: string): boolean {
  return Object.prototype.hasOwnProperty.call(value, key);
}

function parseProviderAt(value: unknown, path: string): Provider {
  return readEnum(value, MARKET_DATA_PROVIDERS, path);
}

export function parseProvider(value: unknown): Provider {
  return parseProviderAt(value, "$" );
}

function parseTimeframeAt(value: unknown, path: string): Timeframe {
  return readEnum(value, MARKET_DATA_TIMEFRAMES, path);
}

export function parseTimeframe(value: unknown): Timeframe {
  return parseTimeframeAt(value, "$" );
}

function parseCompletenessAt(value: unknown, path: string): Completeness {
  return readEnum(value, CANDLE_RANGE_COMPLETENESS, path);
}

export function parseCompleteness(value: unknown): Completeness {
  return parseCompletenessAt(value, "$" );
}

function parsePairAt(value: unknown, path: string): string {
  const parsed = readString(value, path);
  if (!PAIR_PATTERN.test(parsed)) {
    return fail(path, "expected a canonical uppercase pair containing 5 to 20 letters or digits");
  }
  return parsed;
}

export function parsePair(value: unknown): string {
  return parsePairAt(value, "$" );
}

function parseUtcTimestampAt(value: unknown, path: string): UtcTimestamp {
  const parsed = readString(value, path);
  const match = UTC_TIMESTAMP_PATTERN.exec(parsed);
  if (!match) {
    return fail(path, "expected an RFC 3339 UTC timestamp ending in Z");
  }

  const epoch = Date.parse(parsed);
  if (!Number.isFinite(epoch)) {
    return fail(path, "expected a valid UTC timestamp");
  }

  const date = new Date(epoch);
  const parts = match.slice(1, 7).map(Number);
  const actual = [
    date.getUTCFullYear(),
    date.getUTCMonth() + 1,
    date.getUTCDate(),
    date.getUTCHours(),
    date.getUTCMinutes(),
    date.getUTCSeconds(),
  ];
  if (parts.some((part, index) => part !== actual[index])) {
    return fail(path, "expected a valid calendar date and time");
  }

  return parsed;
}

export function parseUtcTimestamp(value: unknown): UtcTimestamp {
  return parseUtcTimestampAt(value, "$" );
}

function parseDecimalAt(value: unknown, path: string, positive: boolean): DecimalString {
  const parsed = readString(value, path);
  if (!DECIMAL_PATTERN.test(parsed)) {
    return fail(path, "expected a non-negative base-10 decimal string without exponent notation");
  }
  if (positive && compareDecimals(parsed, "0") <= 0) {
    return fail(path, "expected a positive decimal string");
  }
  return parsed;
}

export function parseDecimalString(value: unknown): DecimalString {
  return parseDecimalAt(value, "$", false);
}

export function parsePositiveDecimalString(value: unknown): DecimalString {
  return parseDecimalAt(value, "$", true);
}

function compareDecimals(left: DecimalString, right: DecimalString): number {
  const [leftInteger, leftFraction = ""] = left.split(".");
  const [rightInteger, rightFraction = ""] = right.split(".");

  if (leftInteger.length !== rightInteger.length) {
    return leftInteger.length < rightInteger.length ? -1 : 1;
  }
  if (leftInteger !== rightInteger) {
    return leftInteger < rightInteger ? -1 : 1;
  }

  const width = Math.max(leftFraction.length, rightFraction.length);
  const paddedLeft = leftFraction.padEnd(width, "0");
  const paddedRight = rightFraction.padEnd(width, "0");
  if (paddedLeft === paddedRight) {
    return 0;
  }
  return paddedLeft < paddedRight ? -1 : 1;
}

function parseSelectionAt(value: unknown, path: string): MarketSelection {
  const object = readObject(value, path);
  assertExactKeys(object, ["provider", "pair", "timeframe"], path);
  return {
    provider: parseProviderAt(object.provider, `${path}.provider`),
    pair: parsePairAt(object.pair, `${path}.pair`),
    timeframe: parseTimeframeAt(object.timeframe, `${path}.timeframe`),
  };
}

export function parseMarketSelection(value: unknown): MarketSelection {
  return parseSelectionAt(value, "$" );
}

function sameSelection(left: MarketSelection, right: MarketSelection): boolean {
  return (
    left.provider === right.provider &&
    left.pair === right.pair &&
    left.timeframe === right.timeframe
  );
}

function parseCandleAt(value: unknown, path: string): Candle {
  const object = readObject(value, path);
  assertExactKeys(
    object,
    [
      "provider",
      "pair",
      "timeframe",
      "openTime",
      "closeTime",
      "open",
      "high",
      "low",
      "close",
      "volume",
      "closed",
      "receivedAt",
    ],
    path,
  );

  const parsed: Candle = {
    provider: parseProviderAt(object.provider, `${path}.provider`),
    pair: parsePairAt(object.pair, `${path}.pair`),
    timeframe: parseTimeframeAt(object.timeframe, `${path}.timeframe`),
    openTime: parseUtcTimestampAt(object.openTime, `${path}.openTime`),
    closeTime: parseUtcTimestampAt(object.closeTime, `${path}.closeTime`),
    open: parseDecimalAt(object.open, `${path}.open`, true),
    high: parseDecimalAt(object.high, `${path}.high`, true),
    low: parseDecimalAt(object.low, `${path}.low`, true),
    close: parseDecimalAt(object.close, `${path}.close`, true),
    volume: parseDecimalAt(object.volume, `${path}.volume`, false),
    closed: readBoolean(object.closed, `${path}.closed`),
    receivedAt: parseUtcTimestampAt(object.receivedAt, `${path}.receivedAt`),
  };

  if (Date.parse(parsed.closeTime) <= Date.parse(parsed.openTime)) {
    fail(`${path}.closeTime`, "must be later than openTime");
  }
  if (
    compareDecimals(parsed.high, parsed.open) < 0 ||
    compareDecimals(parsed.high, parsed.close) < 0 ||
    compareDecimals(parsed.high, parsed.low) < 0
  ) {
    fail(`${path}.high`, "must be greater than or equal to open, close, and low");
  }
  if (
    compareDecimals(parsed.low, parsed.open) > 0 ||
    compareDecimals(parsed.low, parsed.close) > 0 ||
    compareDecimals(parsed.low, parsed.high) > 0
  ) {
    fail(`${path}.low`, "must be less than or equal to open, close, and high");
  }

  return parsed;
}

export function parseCandle(value: unknown): Candle {
  return parseCandleAt(value, "$" );
}

function parseTimeRangeAt(value: unknown, path: string): TimeRange {
  const object = readObject(value, path);
  assertExactKeys(object, ["startTime", "endTime"], path);
  const parsed = {
    startTime: parseUtcTimestampAt(object.startTime, `${path}.startTime`),
    endTime: parseUtcTimestampAt(object.endTime, `${path}.endTime`),
  };
  if (Date.parse(parsed.endTime) <= Date.parse(parsed.startTime)) {
    fail(`${path}.endTime`, "must be later than startTime");
  }
  return parsed;
}

export function parseTimeRange(value: unknown): TimeRange {
  return parseTimeRangeAt(value, "$" );
}

function readArray(value: unknown, path: string, maximum: number): unknown[] {
  if (!Array.isArray(value)) {
    return fail(path, "expected an array");
  }
  if (value.length > maximum) {
    return fail(path, `must contain at most ${maximum} items`);
  }
  return value;
}

function parseCandleRangeAt(value: unknown, path: string): CandleRange {
  const object = readObject(value, path);
  assertExactKeys(
    object,
    ["schemaVersion", "selection", "range", "completeness", "missingRanges", "candles"],
    path,
  );
  if (object.schemaVersion !== MARKET_DATA_SCHEMA_VERSION) {
    fail(`${path}.schemaVersion`, `expected ${MARKET_DATA_SCHEMA_VERSION}`);
  }

  const selection = parseSelectionAt(object.selection, `${path}.selection`);
  const range = parseTimeRangeAt(object.range, `${path}.range`);
  const completeness = parseCompletenessAt(object.completeness, `${path}.completeness`);
  const missingRanges = readArray(object.missingRanges, `${path}.missingRanges`, 500).map(
    (item, index) => parseTimeRangeAt(item, `${path}.missingRanges[${index}]`),
  );
  const candles = readArray(object.candles, `${path}.candles`, 1_000).map((item, index) =>
    parseCandleAt(item, `${path}.candles[${index}]`),
  );

  if (completeness === "COMPLETE" && missingRanges.length > 0) {
    fail(`${path}.missingRanges`, "must be empty when completeness is COMPLETE");
  }
  if (completeness === "PARTIAL" && missingRanges.length === 0) {
    fail(`${path}.missingRanges`, "must explain at least one gap when completeness is PARTIAL");
  }
  if (completeness === "EMPTY" && candles.length > 0) {
    fail(`${path}.candles`, "must be empty when completeness is EMPTY");
  }

  let previousMissingEnd = Number.NEGATIVE_INFINITY;
  for (const [index, missing] of missingRanges.entries()) {
    const start = Date.parse(missing.startTime);
    const end = Date.parse(missing.endTime);
    if (start < Date.parse(range.startTime) || end > Date.parse(range.endTime)) {
      fail(`${path}.missingRanges[${index}]`, "must be within the requested range");
    }
    if (start < previousMissingEnd) {
      fail(`${path}.missingRanges[${index}]`, "must be sorted and non-overlapping");
    }
    previousMissingEnd = end;
  }

  let previousOpenTime = Number.NEGATIVE_INFINITY;
  for (const [index, item] of candles.entries()) {
    if (!sameSelection(selection, item)) {
      fail(`${path}.candles[${index}]`, "must match the range selection");
    }
    const openTime = Date.parse(item.openTime);
    if (openTime < Date.parse(range.startTime) || openTime >= Date.parse(range.endTime)) {
      fail(`${path}.candles[${index}].openTime`, "must be inside [startTime, endTime)");
    }
    if (openTime <= previousOpenTime) {
      fail(`${path}.candles[${index}].openTime`, "must be unique and strictly chronological");
    }
    previousOpenTime = openTime;
  }

  return {
    schemaVersion: MARKET_DATA_SCHEMA_VERSION,
    selection,
    range,
    completeness,
    missingRanges,
    candles,
  };
}

export function parseCandleRange(value: unknown): CandleRange {
  return parseCandleRangeAt(value, "$" );
}

function parseMarketDimensionsAt(value: unknown, path: string): MarketDimensions {
  const object = readObject(value, path);
  if (object.schemaVersion !== MARKET_DATA_SCHEMA_VERSION) {
    fail(`${path}.schemaVersion`, `expected ${MARKET_DATA_SCHEMA_VERSION}`);
  }
  const providers = readArray(object.providers, `${path}.providers`, 100).map((item, index) =>
    parseProviderAt(item, `${path}.providers[${index}]`),
  );
  const pairs = readArray(object.pairs, `${path}.pairs`, 10_000).map((item, index) =>
    parsePairAt(item, `${path}.pairs[${index}]`),
  );
  const timeframes = readArray(object.timeframes, `${path}.timeframes`, 100).map(
    (item, index) => parseTimeframeAt(item, `${path}.timeframes[${index}]`),
  );
  return {
    schemaVersion: MARKET_DATA_SCHEMA_VERSION,
    providers,
    pairs,
    timeframes,
  };
}

export function parseMarketDimensions(value: unknown): MarketDimensions {
  return parseMarketDimensionsAt(value, "$" );
}

function parseSuccessEnvelopeAt<T>(
  value: unknown,
  dataParser: (value: unknown, path: string) => T,
  path: string,
): SuccessEnvelope<T> {
  const object = readObject(value, path);
  if (object.success !== true) {
    fail(`${path}.success`, "expected true");
  }
  return {
    success: true,
    message: readString(object.message, `${path}.message`),
    data: dataParser(object.data, `${path}.data`),
    timestamp: parseUtcTimestampAt(object.timestamp, `${path}.timestamp`),
    requestId: readNonEmptyString(object.requestId, `${path}.requestId`),
  };
}

export function parseCandleRangeEnvelope(value: unknown): CandleRangeEnvelope {
  return parseSuccessEnvelopeAt(value, parseCandleRangeAt, "$" );
}

export function parseMarketDimensionsEnvelope(value: unknown): MarketDimensionsEnvelope {
  return parseSuccessEnvelopeAt(value, parseMarketDimensionsAt, "$" );
}

function parseRestErrorCodeAt(value: unknown, path: string): MarketDataRestErrorCode {
  return readEnum(value, MARKET_DATA_REST_ERROR_CODES, path);
}

export function parseMarketDataRestErrorEnvelope(value: unknown): MarketDataRestErrorEnvelope {
  const path = "$";
  const object = readObject(value, path);
  assertExactKeys(object, ["success", "message", "error", "timestamp", "requestId"], path);
  if (object.success !== false) {
    fail(`${path}.success`, "expected false");
  }
  const error = readObject(object.error, `${path}.error`);
  assertExactKeys(error, ["code", "retryable", "details"], `${path}.error`);

  const details = hasOwn(error, "details")
    ? error.details === null
      ? null
      : readObject(error.details, `${path}.error.details`)
    : undefined;
  return {
    success: false,
    message: readString(object.message, `${path}.message`),
    error: {
      code: parseRestErrorCodeAt(error.code, `${path}.error.code`),
      retryable: readBoolean(error.retryable, `${path}.error.retryable`),
      ...(details === undefined ? {} : { details }),
    },
    timestamp: parseUtcTimestampAt(object.timestamp, `${path}.timestamp`),
    requestId: readNonEmptyString(object.requestId, `${path}.requestId`),
  };
}

export function parseMarketDataRestErrorCode(value: unknown): MarketDataRestErrorCode {
  return parseRestErrorCodeAt(value, "$" );
}

function parseCommandTypeAt(value: unknown, path: string): MarketDataCommandType {
  return readEnum(value, MARKET_DATA_COMMAND_TYPES, path);
}

export function parseMarketDataCommand(value: unknown): MarketDataCommand {
  const path = "$";
  const object = readObject(value, path);
  assertExactKeys(object, ["eventType", "version", "requestId", "occurredAt", "payload"], path);
  const eventType = parseCommandTypeAt(object.eventType, `${path}.eventType`);
  if (object.version !== MARKET_DATA_SCHEMA_VERSION) {
    fail(`${path}.version`, `expected ${MARKET_DATA_SCHEMA_VERSION}`);
  }
  const requestId = readNonEmptyString(object.requestId, `${path}.requestId`);
  const occurredAt = parseUtcTimestampAt(object.occurredAt, `${path}.occurredAt`);
  const payload = readObject(object.payload, `${path}.payload`);

  if (eventType === "SUBSCRIBE_MARKET_DATA") {
    assertExactKeys(payload, ["slotId", "generation", "selection"], `${path}.payload`);
    return {
      eventType,
      version: MARKET_DATA_SCHEMA_VERSION,
      requestId,
      occurredAt,
      payload: {
        slotId: readNonEmptyString(payload.slotId, `${path}.payload.slotId`),
        generation: readInteger(payload.generation, `${path}.payload.generation`, 0),
        selection: parseSelectionAt(payload.selection, `${path}.payload.selection`),
      },
    };
  }

  assertExactKeys(payload, ["slotId"], `${path}.payload`);
  return {
    eventType,
    version: MARKET_DATA_SCHEMA_VERSION,
    requestId,
    occurredAt,
    payload: { slotId: readNonEmptyString(payload.slotId, `${path}.payload.slotId`) },
  };
}

function parseEventTypeAt(value: unknown, path: string): MarketDataEventType {
  return readEnum(value, MARKET_DATA_EVENT_TYPES, path);
}

function parseEventBase(value: unknown): {
  object: JsonObject;
  eventType: MarketDataEventType;
  eventId: string;
  requestId?: string;
  occurredAt: UtcTimestamp;
  payload: JsonObject;
} {
  const path = "$";
  const object = readObject(value, path);
  const eventType = parseEventTypeAt(object.eventType, `${path}.eventType`);
  if (object.version !== MARKET_DATA_SCHEMA_VERSION) {
    fail(`${path}.version`, `expected ${MARKET_DATA_SCHEMA_VERSION}`);
  }
  const requestId = hasOwn(object, "requestId")
    ? readNonEmptyString(object.requestId, `${path}.requestId`)
    : undefined;
  return {
    object,
    eventType,
    eventId: readNonEmptyString(object.eventId, `${path}.eventId`),
    ...(requestId === undefined ? {} : { requestId }),
    occurredAt: parseUtcTimestampAt(object.occurredAt, `${path}.occurredAt`),
    payload: readObject(object.payload, `${path}.payload`),
  };
}

function eventEnvelope<T extends MarketDataEvent>(
  base: ReturnType<typeof parseEventBase>,
  event: Omit<T, "version" | "eventId" | "requestId" | "occurredAt">,
): T {
  return {
    ...event,
    version: MARKET_DATA_SCHEMA_VERSION,
    eventId: base.eventId,
    ...(base.requestId === undefined ? {} : { requestId: base.requestId }),
    occurredAt: base.occurredAt,
  } as T;
}

function parseWireStateAt(value: unknown, path: string): MarketDataWireState {
  return readEnum(value, MARKET_DATA_WIRE_STATES, path);
}

export function parseMarketDataWireState(value: unknown): MarketDataWireState {
  return parseWireStateAt(value, "$" );
}

function parseConnectionStateAt(value: unknown, path: string): ConnectionState {
  return readEnum(value, CONNECTION_STATES, path);
}

export function parseConnectionState(value: unknown): ConnectionState {
  return parseConnectionStateAt(value, "$" );
}

function parseUppercaseReasonAt(value: unknown, path: string): UppercaseReasonCode {
  const parsed = readString(value, path);
  if (!UPPERCASE_CODE_PATTERN.test(parsed)) {
    return fail(path, "expected a stable uppercase code");
  }
  return parsed;
}

function parseSlotGenerationsAt(
  value: unknown,
  path: string,
  expectedSlotIds?: readonly string[],
): Record<string, number> {
  const object = readObject(value, path);
  const slotIds = Object.keys(object);
  if (slotIds.length === 0 || slotIds.length > 4) {
    fail(path, "must contain between one and four slot generations");
  }
  if (
    expectedSlotIds !== undefined &&
    (slotIds.length !== expectedSlotIds.length ||
      expectedSlotIds.some((slotId) => !hasOwn(object, slotId)))
  ) {
    fail(path, "must contain exactly one generation for every slot ID");
  }
  return Object.fromEntries(
    slotIds.map((slotId) => [
      slotId,
      readInteger(object[slotId], `${path}.${slotId}`, 0),
    ]),
  );
}

function parseSubscriptionStateChanged(
  base: ReturnType<typeof parseEventBase>,
): SubscriptionStateChangedEvent {
  const path = "$.payload";
  const payload = base.payload;
  const rawSlotIds = readArray(payload.slotIds, `${path}.slotIds`, 4);
  if (rawSlotIds.length === 0) {
    fail(`${path}.slotIds`, "must contain at least one slot ID");
  }
  const slotIds = rawSlotIds.map((item, index) =>
    readNonEmptyString(item, `${path}.slotIds[${index}]`),
  );
  if (new Set(slotIds).size !== slotIds.length) {
    fail(`${path}.slotIds`, "must not contain duplicates");
  }
  const slotGenerations = parseSlotGenerationsAt(
    payload.slotGenerations,
    `${path}.slotGenerations`,
    slotIds,
  );

  const attempt = readInteger(payload.attempt, `${path}.attempt`, 0, 8);
  const retryAfterMs = hasOwn(payload, "retryAfterMs")
    ? readInteger(payload.retryAfterMs, `${path}.retryAfterMs`, 0)
    : undefined;
  const lastEventAt = hasOwn(payload, "lastEventAt")
    ? parseUtcTimestampAt(payload.lastEventAt, `${path}.lastEventAt`)
    : undefined;
  const reasonCode = hasOwn(payload, "reasonCode")
    ? parseUppercaseReasonAt(payload.reasonCode, `${path}.reasonCode`)
    : undefined;

  return eventEnvelope<SubscriptionStateChangedEvent>(base, {
    eventType: "SUBSCRIPTION_STATE_CHANGED",
    payload: {
      slotIds,
      slotGenerations,
      selection: parseSelectionAt(payload.selection, `${path}.selection`),
      state: parseWireStateAt(payload.state, `${path}.state`),
      attempt,
      ...(retryAfterMs === undefined ? {} : { retryAfterMs }),
      ...(lastEventAt === undefined ? {} : { lastEventAt }),
      ...(reasonCode === undefined ? {} : { reasonCode }),
    },
  });
}

function parseCandleUpdated(base: ReturnType<typeof parseEventBase>): MarketDataEvent {
  const path = "$.payload";
  const slotGenerations = parseSlotGenerationsAt(
    base.payload.slotGenerations,
    `${path}.slotGenerations`,
  );
  const selection = parseSelectionAt(base.payload.selection, `${path}.selection`);
  const candle = parseCandleAt(base.payload.candle, `${path}.candle`);
  if (!sameSelection(selection, candle)) {
    fail(`${path}.candle`, "must match the event selection");
  }
  return eventEnvelope(base, {
    eventType: "CANDLE_UPDATED",
    payload: {
      slotGenerations,
      selection,
      revision: readInteger(base.payload.revision, `${path}.revision`, 0),
      candle,
    },
  });
}

function parseRealtimeErrorCodeAt(value: unknown, path: string): MarketDataRealtimeErrorCode {
  return readEnum(value, MARKET_DATA_REALTIME_ERROR_CODES, path);
}

export function parseMarketDataRealtimeErrorCode(value: unknown): MarketDataRealtimeErrorCode {
  return parseRealtimeErrorCodeAt(value, "$" );
}

function parseMarketDataError(base: ReturnType<typeof parseEventBase>): MarketDataErrorEvent {
  const path = "$.payload";
  const slotId = hasOwn(base.payload, "slotId")
    ? readNonEmptyString(base.payload.slotId, `${path}.slotId`)
    : undefined;
  const generation = hasOwn(base.payload, "generation")
    ? readInteger(base.payload.generation, `${path}.generation`, 0)
    : undefined;
  return eventEnvelope<MarketDataErrorEvent>(base, {
    eventType: "MARKET_DATA_ERROR",
    payload: {
      ...(slotId === undefined ? {} : { slotId }),
      ...(generation === undefined ? {} : { generation }),
      code: parseRealtimeErrorCodeAt(base.payload.code, `${path}.code`),
      message: readNonEmptyString(base.payload.message, `${path}.message`),
      retryable: readBoolean(base.payload.retryable, `${path}.retryable`),
    },
  });
}

export function parseMarketDataEvent(value: unknown): MarketDataEvent {
  const base = parseEventBase(value);
  switch (base.eventType) {
    case "SUBSCRIPTION_STATE_CHANGED":
      return parseSubscriptionStateChanged(base);
    case "CANDLE_UPDATED":
      return parseCandleUpdated(base);
    case "MARKET_DATA_ERROR":
      return parseMarketDataError(base);
  }
}

export const providerSchema = schema(parseProvider);
export const timeframeSchema = schema(parseTimeframe);
export const completenessSchema = schema(parseCompleteness);
export const marketDataWireStateSchema = schema(parseMarketDataWireState);
export const connectionStateSchema = schema(parseConnectionState);
export const utcTimestampSchema = schema(parseUtcTimestamp);
export const decimalStringSchema = schema(parseDecimalString);
export const positiveDecimalStringSchema = schema(parsePositiveDecimalString);
export const marketSelectionSchema = schema(parseMarketSelection);
export const candleSchema = schema(parseCandle);
export const timeRangeSchema = schema(parseTimeRange);
export const candleRangeSchema = schema(parseCandleRange);
export const marketDimensionsSchema = schema(parseMarketDimensions);
export const candleRangeEnvelopeSchema = schema(parseCandleRangeEnvelope);
export const marketDimensionsEnvelopeSchema = schema(parseMarketDimensionsEnvelope);
export const marketDataRestErrorEnvelopeSchema = schema(parseMarketDataRestErrorEnvelope);
export const marketDataRestErrorCodeSchema = schema(parseMarketDataRestErrorCode);
export const marketDataRealtimeErrorCodeSchema = schema(parseMarketDataRealtimeErrorCode);
export const marketDataCommandSchema = schema(parseMarketDataCommand);
export const marketDataEventSchema = schema(parseMarketDataEvent);

export const isProvider = providerSchema.is;
export const isTimeframe = timeframeSchema.is;
export const isMarketSelection = marketSelectionSchema.is;
export const isCandle = candleSchema.is;
export const isMarketDataCommand = marketDataCommandSchema.is;
export const isMarketDataEvent = marketDataEventSchema.is;
