import { expect, test, type Page, type WebSocketRoute } from "@playwright/test";

const chartSlots = (page: Page) =>
  page.locator('section[id^="chart-btcusdt-"]');

test("adds one to four stable keyboard-operable chart slots and rejects a fifth", async ({
  page,
}) => {
  await page.goto("/market");
  await expect(chartSlots(page)).toHaveCount(1);
  await expect(chartSlots(page).first()).toHaveAttribute(
    "id",
    "chart-btcusdt-5m-slot-1",
  );

  const add = page.locator("#btn-add-chart");
  for (let count = 2; count <= 4; count += 1) {
    await add.focus();
    await expect(add).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(chartSlots(page)).toHaveCount(count);
    await expect(page.locator(`#chart-btcusdt-5m-slot-${count}`)).toBeVisible();
    await expect(chartSlots(page).first()).toHaveAttribute(
      "id",
      "chart-btcusdt-5m-slot-1",
    );
  }

  await add.focus();
  await page.keyboard.press("Enter");
  await expect(chartSlots(page)).toHaveCount(4);
  await expect(page.locator("#message-chart-limit")).toHaveRole("alert");
  await expect(page.locator("#message-chart-limit")).toContainText(
    "A dashboard can use at most four chart slots.",
  );

  for (let index = 1; index <= 4; index += 1) {
    const slotId = `slot-${index}`;
    const slot = page.locator(`section[id$="-${slotId}"]`);
    await expect(slot.locator(`#select-timeframe-${slotId}`)).toBeVisible();
    await expect(slot.locator(`#status-chart-${slotId}`)).toContainText(
      /Loading|Live|Stale|Reconnecting|Error/,
    );
    await expect(slot.locator(`#btn-remove-chart-${slotId}`)).toBeVisible();
  }

  const secondTimeframe = page.locator("#select-timeframe-slot-2");
  await secondTimeframe.focus();
  await expect(secondTimeframe).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await expect(secondTimeframe).toHaveValue("15m");
  await expect(page.locator("#chart-btcusdt-15m-slot-2")).toBeVisible();
  await expect(chartSlots(page).first()).toHaveAttribute(
    "id",
    "chart-btcusdt-5m-slot-1",
  );

  const removeFourth = page.locator("#btn-remove-chart-slot-4");
  await removeFourth.focus();
  await expect(removeFourth).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(chartSlots(page)).toHaveCount(3);
  await expect(page.locator('[id$="-slot-4"]')).toHaveCount(0);
});

test("uses two columns when wide and one column without overflow when narrow", async ({
  page,
}) => {
  await page.goto("/market");
  await page.setViewportSize({ width: 1280, height: 800 });
  const add = page.locator("#btn-add-chart");
  for (let count = 2; count <= 4; count += 1) await add.click();
  const wideFirst = await chartSlots(page).nth(0).boundingBox();
  const wideSecond = await chartSlots(page).nth(1).boundingBox();
  expect(wideFirst).not.toBeNull();
  expect(wideSecond).not.toBeNull();
  expect(wideSecond?.x).toBeGreaterThan((wideFirst?.x ?? 0) + 1);
  const wideBoxes = await chartSlots(page).evaluateAll((slots) =>
    slots.map((slot) => slot.getBoundingClientRect().toJSON()),
  );
  expect(Math.max(...wideBoxes.map((box) => box.bottom))).toBeLessThanOrEqual(800);
  await expect(page.getByTestId("chart-grid")).toHaveAttribute(
    "data-density",
    "compact",
  );

  await page.setViewportSize({ width: 390, height: 844 });
  const narrowFirst = await chartSlots(page).nth(0).boundingBox();
  const narrowSecond = await chartSlots(page).nth(1).boundingBox();
  expect(Math.abs((narrowSecond?.x ?? 0) - (narrowFirst?.x ?? 0))).toBeLessThan(2);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});

test("changes one timeframe without accepting late old-generation work", async ({
  page,
}) => {
  const commands: Array<Record<string, unknown>> = [];
  const bindings = new Map<string, string>();
  const historyOpenTimes = new Map<string, string>();
  const liveOpenTimes = new Map<string, string>();
  let socket: WebSocketRoute | undefined;
  let eventSequence = 0;
  let releaseOneHourHistory!: () => void;
  let markOneHourRequested!: () => void;
  const oneHourGate = new Promise<void>((resolve) => {
    releaseOneHourHistory = resolve;
  });
  const oneHourRequested = new Promise<void>((resolve) => {
    markOneHourRequested = resolve;
  });

  const selection = (timeframe: string) => ({
    provider: "BINANCE",
    pair: "BTCUSDT",
    timeframe,
  });
  const candle = (timeframe: string, close: string, openTime: string) => {
    const interval = timeframe === "1h" ? 60 * 60_000 : 5 * 60_000;
    return {
      ...selection(timeframe),
      openTime,
      closeTime: new Date(Date.parse(openTime) + interval - 1).toISOString(),
      open: "100.00",
      high: close,
      low: "99.00",
      close,
      volume: "12.50",
      closed: true,
      receivedAt: "2026-08-13T10:00:01Z",
    };
  };
  const sendState = (timeframe: string, state: "LOADING" | "LIVE") => {
    const slotIds = [...bindings]
      .filter(([, value]) => value === timeframe)
      .map(([slotId]) => slotId)
      .sort();
    socket?.send(
      JSON.stringify({
        eventType: "SUBSCRIPTION_STATE_CHANGED",
        version: "1",
        eventId: `e2e-state-${++eventSequence}`,
        occurredAt: "2026-08-13T10:00:01Z",
        payload: {
          slotIds,
          selection: selection(timeframe),
          state,
          attempt: 0,
        },
      }),
    );
  };
  const sendCandle = (
    timeframe: string,
    close: string,
    openTime: string,
    revision: number,
  ) => {
    socket?.send(
      JSON.stringify({
        eventType: "CANDLE_UPDATED",
        version: "1",
        eventId: `e2e-candle-${++eventSequence}`,
        occurredAt: "2026-08-13T10:00:01Z",
        payload: {
          selection: selection(timeframe),
          revision,
          candle: candle(timeframe, close, openTime),
        },
      }),
    );
  };

  await page.route("**/api/v1/market-data/candles?**", async (route) => {
    const url = new URL(route.request().url());
    const timeframe = url.searchParams.get("timeframe") ?? "5m";
    const range = {
      startTime: url.searchParams.get("startTime"),
      endTime: url.searchParams.get("endTime"),
    };
    const interval = timeframe === "1h" ? 60 * 60_000 : 5 * 60_000;
    const historyOpenTime = new Date(
      Date.parse(range.endTime ?? "") - interval,
    ).toISOString();
    historyOpenTimes.set(timeframe, historyOpenTime);
    liveOpenTimes.set(timeframe, range.endTime ?? "");
    if (timeframe === "1h") {
      markOneHourRequested();
      await oneHourGate;
    }
    await route.fulfill({
      json: {
        success: true,
        message: "Historical Candles loaded.",
        timestamp: "2026-08-13T10:00:01Z",
        requestId: `history-${timeframe}`,
        data: {
          schemaVersion: "1",
          selection: selection(timeframe),
          range,
          completeness: "COMPLETE",
          missingRanges: [],
          candles: [
            candle(
              timeframe,
              timeframe === "1h" ? "200.00" : "101.00",
              historyOpenTime,
            ),
          ],
        },
      },
    });
  });

  await page.routeWebSocket("**/ws/v1/market-data", (webSocket) => {
    socket = webSocket;
    webSocket.onMessage((message) => {
      const command = JSON.parse(String(message)) as Record<string, unknown>;
      commands.push(command);
      const payload = command.payload as
        | { slotId?: string; selection?: { timeframe?: string } }
        | undefined;
      const slotId = payload?.slotId;
      if (typeof slotId !== "string") return;
      if (command.eventType === "UNSUBSCRIBE_MARKET_DATA") {
        bindings.delete(slotId);
        return;
      }
      if (command.eventType === "SUBSCRIBE_MARKET_DATA") {
        const timeframe = payload.selection?.timeframe;
        if (typeof timeframe !== "string") return;
        bindings.set(slotId, timeframe);
        queueMicrotask(() => {
          sendState(timeframe, "LOADING");
          if (timeframe === "5m") sendState(timeframe, "LIVE");
        });
      }
    });
  });

  await page.goto("/market");
  await expect.poll(() => (socket === undefined ? 0 : 1)).toBe(1);
  await expect(page.locator("#status-chart-slot-1")).toContainText("Live");
  await expect(
    page.locator("#chart-btcusdt-5m-slot-1 [aria-label='Latest Candle summary']"),
  ).toContainText("C 101.00");

  await page.locator("#btn-add-chart").click();
  await expect(page.locator("#status-chart-slot-2")).toContainText("Live");
  const sibling = page.locator("#chart-btcusdt-5m-slot-2");
  await sibling.evaluate((node) => {
    (node as HTMLElement).dataset.identityProbe = "stable";
  });
  const commandCheckpoint = commands.length;

  await page.locator("#select-timeframe-slot-1").selectOption("1h");
  await expect(page.locator("#chart-btcusdt-1h-slot-1")).toBeVisible();
  await expect(page.locator("#status-chart-slot-1")).toContainText("Loading");
  await expect(sibling).toHaveAttribute("data-identity-probe", "stable");
  await expect(page.locator("#select-timeframe-slot-2")).toHaveValue("5m");
  await oneHourRequested;

  const slotOneCommands = commands.slice(commandCheckpoint).filter((command) => {
    const payload = command.payload as { slotId?: string } | undefined;
    return payload?.slotId === "slot-1";
  });
  expect(slotOneCommands.map((command) => command.eventType)).toEqual([
    "UNSUBSCRIBE_MARKET_DATA",
    "SUBSCRIBE_MARKET_DATA",
  ]);

  sendCandle("1h", "205.00", liveOpenTimes.get("1h") ?? "", 1);
  await page.waitForTimeout(50);
  releaseOneHourHistory();
  sendState("1h", "LIVE");
  const slotOneSummary = page.locator(
    "#chart-btcusdt-1h-slot-1 [aria-label='Latest Candle summary']",
  );
  await expect(slotOneSummary).toContainText("C 205.00");
  const currentSummary = await slotOneSummary.textContent();

  sendCandle("5m", "109.00", liveOpenTimes.get("5m") ?? "", 2);
  await expect(
    page.locator("#chart-btcusdt-5m-slot-2 [aria-label='Latest Candle summary']"),
  ).toContainText("C 109.00");
  await expect(slotOneSummary).toHaveText(currentSummary ?? "");
  expect([...bindings.entries()].sort()).toEqual([
    ["slot-1", "1h"],
    ["slot-2", "5m"],
  ]);
  expect(
    commands.filter((command) => {
      const payload = command.payload as
        | { slotId?: string; selection?: { timeframe?: string } }
        | undefined;
      return (
        command.eventType === "SUBSCRIBE_MARKET_DATA" &&
        payload?.slotId === "slot-1" &&
        payload.selection?.timeframe === "1h"
      );
    }),
  ).toHaveLength(1);
});

test("recovers a disconnected slot with missed closed candles before LIVE and leaves a healthy sibling alone", async ({
  page,
}) => {
  const bindings = new Map<string, string>();
  const liveOpenTimes = new Map<string, string>();
  let socket: WebSocketRoute | undefined;
  let eventSequence = 0;

  const selection = (timeframe: string) => ({
    provider: "BINANCE",
    pair: "BTCUSDT",
    timeframe,
  });
  const intervalFor = (timeframe: string) =>
    timeframe === "1h" ? 60 * 60_000 : 5 * 60_000;
  const candle = (
    timeframe: string,
    close: string,
    openTime: string,
    closed: boolean,
  ) => {
    const interval = intervalFor(timeframe);
    return {
      ...selection(timeframe),
      openTime,
      closeTime: new Date(Date.parse(openTime) + interval - 1).toISOString(),
      open: "100.00",
      high: closed ? close : "105.00",
      low: "99.00",
      close,
      volume: "12.50",
      closed,
      receivedAt: "2026-08-13T10:00:01Z",
    };
  };
  const sendState = (
    timeframe: string,
    state: string,
    extra: Record<string, unknown> = {},
  ) => {
    const slotIds = [...bindings]
      .filter(([, value]) => value === timeframe)
      .map(([slotId]) => slotId)
      .sort();
    socket?.send(
      JSON.stringify({
        eventType: "SUBSCRIPTION_STATE_CHANGED",
        version: "1",
        eventId: `e2e-state-${++eventSequence}`,
        occurredAt: "2026-08-13T10:00:01Z",
        payload: {
          slotIds,
          selection: selection(timeframe),
          state,
          attempt: 0,
          ...extra,
        },
      }),
    );
  };
  const sendCandle = (
    timeframe: string,
    close: string,
    openTime: string,
    revision: number,
    closed = true,
  ) => {
    socket?.send(
      JSON.stringify({
        eventType: "CANDLE_UPDATED",
        version: "1",
        eventId: `e2e-candle-${++eventSequence}`,
        occurredAt: "2026-08-13T10:00:01Z",
        payload: {
          selection: selection(timeframe),
          revision,
          candle: candle(timeframe, close, openTime, closed),
        },
      }),
    );
  };

  await page.route("**/api/v1/market-data/candles?**", async (route) => {
    const url = new URL(route.request().url());
    const timeframe = url.searchParams.get("timeframe") ?? "5m";
    const range = {
      startTime: url.searchParams.get("startTime"),
      endTime: url.searchParams.get("endTime"),
    };
    const interval = intervalFor(timeframe);
    const historyOpenTime = new Date(
      Date.parse(range.endTime ?? "") - interval,
    ).toISOString();
    liveOpenTimes.set(timeframe, range.endTime ?? "");
    await route.fulfill({
      json: {
        success: true,
        message: "Historical Candles loaded.",
        timestamp: "2026-08-13T10:00:01Z",
        requestId: `history-${timeframe}`,
        data: {
          schemaVersion: "1",
          selection: selection(timeframe),
          range,
          completeness: "COMPLETE",
          missingRanges: [],
          candles: [candle(timeframe, "101.00", historyOpenTime, true)],
        },
      },
    });
  });

  await page.routeWebSocket("**/ws/v1/market-data", (webSocket) => {
    socket = webSocket;
    webSocket.onMessage((message) => {
      const command = JSON.parse(String(message)) as Record<string, unknown>;
      const payload = command.payload as
        | { slotId?: string; selection?: { timeframe?: string } }
        | undefined;
      const slotId = payload?.slotId;
      if (typeof slotId !== "string") return;
      if (command.eventType === "UNSUBSCRIBE_MARKET_DATA") {
        bindings.delete(slotId);
        return;
      }
      if (command.eventType === "SUBSCRIBE_MARKET_DATA") {
        const timeframe = payload.selection?.timeframe;
        if (typeof timeframe !== "string") return;
        bindings.set(slotId, timeframe);
        queueMicrotask(() => {
          sendState(timeframe, "LOADING");
          sendState(timeframe, "LIVE");
        });
      }
    });
  });

  await page.goto("/market");
  await expect.poll(() => (socket === undefined ? 0 : 1)).toBe(1);
  await expect(page.locator("#status-chart-slot-1")).toContainText("Live");

  await page.locator("#btn-add-chart").click();
  await page.locator("#select-timeframe-slot-2").selectOption("1h");
  await expect(page.locator("#status-chart-slot-2")).toContainText("Live");
  await expect(page.locator("#status-chart-slot-1")).toContainText("Live");

  const liveTail = liveOpenTimes.get("5m") ?? "";
  sendCandle("5m", "104.00", liveTail, 1, false);
  const series = page.locator(
    "#chart-btcusdt-5m-slot-1 [data-series-length]",
  );
  await expect(series).toHaveAttribute("data-series-length", "2");

  sendState("5m", "STALE", {
    attempt: 1,
    reasonCode: "PROVIDER_DISCONNECTED",
    lastEventAt: "2026-08-13T09:59:30Z",
  });
  await expect(page.locator("#status-chart-slot-1")).toContainText("Stale");
  await expect(page.locator("#status-chart-slot-1")).toContainText(
    "2026-08-13T09:59:30Z",
  );
  await expect(page.locator("#status-chart-slot-2")).toContainText("Live");

  sendState("5m", "RECONNECTING", {
    attempt: 2,
    retryAfterMs: 2034,
    lastEventAt: "2026-08-13T09:59:30Z",
    reasonCode: "PROVIDER_DISCONNECTED",
  });
  await expect(page.locator("#status-chart-slot-1")).toContainText(
    "Reconnecting",
  );
  await expect(page.locator("#status-chart-slot-1")).toContainText(
    "attempt 2",
  );

  sendCandle("5m", "103.00", liveTail, 2, true);
  const recoveredTail = new Date(Date.parse(liveTail) + 5 * 60_000).toISOString();
  sendCandle("5m", "103.50", recoveredTail, 3, true);
  await expect(series).toHaveAttribute("data-series-length", "3");
  await expect(
    page.locator(
      "#chart-btcusdt-5m-slot-1 [aria-label='Latest Candle summary']",
    ),
  ).toContainText("C 103.50");
  await expect(page.locator("#status-chart-slot-1")).toContainText(
    "Reconnecting",
  );
  await expect(page.locator("#status-chart-slot-2")).toContainText("Live");

  sendState("5m", "LIVE", { attempt: 3 });
  await expect(page.locator("#status-chart-slot-1")).toContainText("Live");
  await expect(page.locator("#status-chart-slot-2")).toContainText("Live");

  const olderThanTail = new Date(Date.parse(liveTail) - 10 * 60_000).toISOString();
  sendCandle("5m", "102.00", olderThanTail, 4, true);
  await expect(series).toHaveAttribute("data-series-length", "3");
});

test("shows exhausted recovery as an error with a manual retry that restarts the cycle", async ({
  page,
}) => {
  const commands: Array<Record<string, unknown>> = [];
  const bindings = new Map<string, string>();
  const liveOpenTimes = new Map<string, string>();
  let socket: WebSocketRoute | undefined;
  let eventSequence = 0;

  const selection = (timeframe: string) => ({
    provider: "BINANCE",
    pair: "BTCUSDT",
    timeframe,
  });
  const candle = (timeframe: string, close: string, openTime: string) => {
    const interval = timeframe === "1h" ? 60 * 60_000 : 5 * 60_000;
    return {
      ...selection(timeframe),
      openTime,
      closeTime: new Date(Date.parse(openTime) + interval - 1).toISOString(),
      open: "100.00",
      high: close,
      low: "99.00",
      close,
      volume: "12.50",
      closed: true,
      receivedAt: "2026-08-13T10:00:01Z",
    };
  };
  const sendState = (
    timeframe: string,
    state: string,
    extra: Record<string, unknown> = {},
  ) => {
    const slotIds = [...bindings]
      .filter(([, value]) => value === timeframe)
      .map(([slotId]) => slotId)
      .sort();
    socket?.send(
      JSON.stringify({
        eventType: "SUBSCRIPTION_STATE_CHANGED",
        version: "1",
        eventId: `e2e-state-${++eventSequence}`,
        occurredAt: "2026-08-13T10:00:01Z",
        payload: {
          slotIds,
          selection: selection(timeframe),
          state,
          attempt: 0,
          ...extra,
        },
      }),
    );
  };

  await page.route("**/api/v1/market-data/candles?**", async (route) => {
    const url = new URL(route.request().url());
    const timeframe = url.searchParams.get("timeframe") ?? "5m";
    const range = {
      startTime: url.searchParams.get("startTime"),
      endTime: url.searchParams.get("endTime"),
    };
    const interval = timeframe === "1h" ? 60 * 60_000 : 5 * 60_000;
    const historyOpenTime = new Date(
      Date.parse(range.endTime ?? "") - interval,
    ).toISOString();
    liveOpenTimes.set(timeframe, range.endTime ?? "");
    await route.fulfill({
      json: {
        success: true,
        message: "Historical Candles loaded.",
        timestamp: "2026-08-13T10:00:01Z",
        requestId: `history-${timeframe}`,
        data: {
          schemaVersion: "1",
          selection: selection(timeframe),
          range,
          completeness: "COMPLETE",
          missingRanges: [],
          candles: [candle(timeframe, "101.00", historyOpenTime)],
        },
      },
    });
  });

  await page.routeWebSocket("**/ws/v1/market-data", (webSocket) => {
    socket = webSocket;
    webSocket.onMessage((message) => {
      const command = JSON.parse(String(message)) as Record<string, unknown>;
      commands.push(command);
      const payload = command.payload as
        | { slotId?: string; selection?: { timeframe?: string } }
        | undefined;
      const slotId = payload?.slotId;
      if (typeof slotId !== "string") return;
      if (command.eventType === "UNSUBSCRIBE_MARKET_DATA") {
        bindings.delete(slotId);
        return;
      }
      if (command.eventType === "SUBSCRIBE_MARKET_DATA") {
        const timeframe = payload.selection?.timeframe;
        if (typeof timeframe !== "string") return;
        bindings.set(slotId, timeframe);
        queueMicrotask(() => {
          sendState(timeframe, "LOADING");
          sendState(timeframe, "LIVE");
        });
      }
    });
  });

  await page.goto("/market");
  await expect.poll(() => (socket === undefined ? 0 : 1)).toBe(1);
  await expect(page.locator("#status-chart-slot-1")).toContainText("Live");

  await page.locator("#btn-add-chart").click();
  await page.locator("#select-timeframe-slot-2").selectOption("1h");
  await expect(page.locator("#status-chart-slot-2")).toContainText("Live");

  sendState("5m", "STALE", {
    attempt: 1,
    reasonCode: "PROVIDER_DISCONNECTED",
    lastEventAt: "2026-08-13T09:59:30Z",
  });
  await expect(page.locator("#status-chart-slot-1")).toContainText("Stale");

  sendState("5m", "ERROR", {
    attempt: 8,
    reasonCode: "MARKET_RECOVERY_EXHAUSTED",
    lastEventAt: "2026-08-13T09:59:30Z",
  });
  const status = page.locator("#status-chart-slot-1");
  await expect(status).toContainText("Error");
  await expect(status).toContainText("Automatic recovery exhausted");
  const retry = page.locator("#btn-retry-chart-slot-1");
  await expect(retry).toBeVisible();
  await expect(page.locator("#status-chart-slot-2")).toContainText("Live");

  await retry.focus();
  await expect(retry).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(status).toContainText("Reconnecting");
  expect(
    commands.filter((command) => command.eventType === "RETRY_MARKET_DATA"),
  ).toHaveLength(1);
  const retryCommand = commands.find(
    (command) => command.eventType === "RETRY_MARKET_DATA",
  );
  expect(retryCommand?.payload).toMatchObject({ slotId: "slot-1" });
  await expect(page.locator("#status-chart-slot-2")).toContainText("Live");

  sendState("5m", "STALE", {
    attempt: 1,
    reasonCode: "PROVIDER_DISCONNECTED",
  });
  sendState("5m", "LIVE", { attempt: 2 });
  await expect(status).toContainText("Live");
  await expect(page.locator("#status-chart-slot-2")).toContainText("Live");
  await expect(retry).toHaveCount(0);
});
