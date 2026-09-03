import { expect, test, type WebSocketRoute } from "@playwright/test";

type Selection = {
  provider: "BINANCE";
  pair: string;
  timeframe: string;
};

test("propagates pair and timeframe context across realtime chart lifecycles", async ({
  page,
}) => {
  const commands: Array<Record<string, unknown>> = [];
  const bindings = new Map<string, Selection>();
  const generations = new Map<string, number>();
  const firstBtcGenerations: Record<string, number> = {};
  const historyRequests: Selection[] = [];
  const historyOpenTimes = new Map<string, string>();
  const sockets = new Set<WebSocketRoute>();
  let eventSequence = 0;

  const selection = (pair: string, timeframe: string): Selection => ({
    provider: "BINANCE",
    pair,
    timeframe,
  });
  const intervalFor = (timeframe: string) =>
    timeframe === "1h" ? 60 * 60_000 : 5 * 60_000;
  const candle = (selected: Selection, close: string, openTime: string) => ({
    ...selected,
    openTime,
    closeTime: new Date(
      Date.parse(openTime) + intervalFor(selected.timeframe) - 1,
    ).toISOString(),
    open: "100.00",
    high: close,
    low: "99.00",
    close,
    volume: "12.50",
    closed: true,
    receivedAt: "2026-08-13T10:00:01Z",
  });
  const sameSelection = (left: Selection, right: Selection) =>
    left.provider === right.provider &&
    left.pair === right.pair &&
    left.timeframe === right.timeframe;
  const sendState = (selected: Selection) => {
    const slotIds = [...bindings]
      .filter(([, bound]) => sameSelection(bound, selected))
      .map(([slotId]) => slotId)
      .sort();
    if (slotIds.length === 0) return;
    const message = JSON.stringify({
        eventType: "SUBSCRIPTION_STATE_CHANGED",
        version: "1",
        eventId: `pair-e2e-state-${++eventSequence}`,
        occurredAt: "2026-08-13T10:00:01Z",
        payload: {
          slotIds,
          slotGenerations: Object.fromEntries(
            slotIds.map((slotId) => [slotId, generations.get(slotId) ?? 0]),
          ),
          selection: selected,
          state: "LIVE",
          attempt: 0,
        },
      });
    for (const activeSocket of sockets) activeSocket.send(message);
  };
  const sendCandle = (
    selected: Selection,
    close: string,
    openTime: string,
    revision: number,
    slotGenerations = Object.fromEntries(
      [...bindings]
        .filter(([, bound]) => sameSelection(bound, selected))
        .map(([slotId]) => [slotId, generations.get(slotId) ?? 0]),
    ),
  ) => {
    const message = JSON.stringify({
        eventType: "CANDLE_UPDATED",
        version: "1",
        eventId: `pair-e2e-candle-${++eventSequence}`,
        occurredAt: "2026-08-13T10:00:01Z",
        payload: {
          slotGenerations,
          selection: selected,
          revision,
          candle: candle(selected, close, openTime),
        },
      });
    for (const activeSocket of sockets) activeSocket.send(message);
  };
  const subscribeCommands = () =>
    commands.filter((command) => command.eventType === "SUBSCRIBE_MARKET_DATA");
  const commandSelection = (
    command: Record<string, unknown>,
  ): Selection | undefined => {
    const payload = command.payload as { selection?: Selection } | undefined;
    return payload?.selection;
  };
  const historyCount = (pair: string, timeframe?: string) =>
    historyRequests.filter(
      (item) =>
        item.pair === pair &&
        (timeframe === undefined || item.timeframe === timeframe),
    ).length;

  await page.route("**/api/v1/market-data/dimensions", async (route) => {
    await route.fulfill({
      json: {
        success: true,
        message: "Market dimensions loaded.",
        timestamp: "2026-08-13T10:00:01Z",
        requestId: "pair-dimensions",
        data: {
          schemaVersion: "1",
          providers: ["BINANCE"],
          pairs: ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
          timeframes: ["5m", "15m", "1h", "4h"],
        },
      },
    });
  });
  await page.route("**/api/v1/market-data/candles?**", async (route) => {
    const url = new URL(route.request().url());
    const pair = url.searchParams.get("pair") ?? "BTCUSDT";
    const timeframe = url.searchParams.get("timeframe") ?? "5m";
    const selected = selection(pair, timeframe);
    const endTime = url.searchParams.get("endTime") ?? "2026-08-13T10:00:00Z";
    const openTime = new Date(
      Date.parse(endTime) - intervalFor(timeframe),
    ).toISOString();
    historyRequests.push(selected);
    historyOpenTimes.set(`${pair}:${timeframe}`, openTime);
    await route.fulfill({
      json: {
        success: true,
        message: "Historical Candles loaded.",
        timestamp: "2026-08-13T10:00:01Z",
        requestId: `pair-history-${pair}-${timeframe}`,
        data: {
          schemaVersion: "1",
          selection: selected,
          range: {
            startTime: url.searchParams.get("startTime"),
            endTime,
          },
          completeness: "COMPLETE",
          missingRanges: [],
          candles: [candle(selected, "101.00", openTime)],
        },
      },
    });
  });
  await page.routeWebSocket("**/ws/v1/market-data", (webSocket) => {
    sockets.add(webSocket);
    webSocket.onMessage((message) => {
      const command = JSON.parse(String(message)) as Record<string, unknown>;
      commands.push(command);
      const payload = command.payload as
        | { slotId?: string; generation?: number; selection?: Selection }
        | undefined;
      if (typeof payload?.slotId !== "string") return;
      if (command.eventType === "UNSUBSCRIBE_MARKET_DATA") {
        bindings.delete(payload.slotId);
        generations.delete(payload.slotId);
        return;
      }
      if (command.eventType !== "SUBSCRIBE_MARKET_DATA" || payload.selection === undefined) {
        return;
      }
      if (typeof payload.generation !== "number") return;
      bindings.set(payload.slotId, payload.selection);
      generations.set(payload.slotId, payload.generation);
      if (
        payload.selection.pair === "BTCUSDT" &&
        firstBtcGenerations[payload.slotId] === undefined
      ) {
        firstBtcGenerations[payload.slotId] = payload.generation;
      }
      queueMicrotask(() => sendState(payload.selection as Selection));
    });
  });

  await page.goto("/market");
  await expect.poll(() => sockets.size).toBe(2);
  await expect(page.locator("#status-chart-slot-1")).toContainText("Live");
  await page.locator("#btn-add-chart").click();
  await expect(page.locator("#status-chart-slot-2")).toContainText("Live");

  const dashboardPair = page.getByRole("combobox", { name: "Dashboard pair" });
  await expect(dashboardPair.locator("option")).toHaveCount(3);
  await dashboardPair.selectOption("ETHUSDT");
  await expect(page.locator("#chart-ethusdt-5m-slot-1")).toBeVisible();
  await expect(page.locator("#chart-ethusdt-5m-slot-2")).toBeVisible();
  // The two dashboard slots share one history query. The independently scoped
  // Topbar summary owns a second 5m history query for its rolling 24h window.
  await expect.poll(() => historyCount("ETHUSDT", "5m")).toBe(2);
  await expect.poll(
    () =>
      subscribeCommands().filter((command) => {
        const selected = commandSelection(command);
        return selected?.pair === "ETHUSDT" && selected.timeframe === "5m";
      }).length,
  ).toBe(3);
  expect([...bindings.values()]).toEqual([
    selection("ETHUSDT", "5m"),
    selection("ETHUSDT", "5m"),
    selection("ETHUSDT", "5m"),
  ]);

  const siblingSummary = page.locator(
    "#chart-ethusdt-5m-slot-2 [aria-label='Latest Candle summary']",
  );
  const siblingText = await siblingSummary.textContent();
  const timeframeCheckpoint = commands.length;
  await page.locator("#select-timeframe-slot-1").selectOption("1h");
  await expect(page.locator("#chart-ethusdt-1h-slot-1")).toBeVisible();
  await expect(page.locator("#select-timeframe-slot-2")).toHaveValue("5m");
  await expect(siblingSummary).toHaveText(siblingText ?? "");
  await expect.poll(() => historyCount("ETHUSDT", "1h")).toBe(1);
  expect(commands.slice(timeframeCheckpoint).map((command) => command.eventType)).toEqual([
    "UNSUBSCRIBE_MARKET_DATA",
    "SUBSCRIBE_MARKET_DATA",
  ]);

  const oneHourSummary = page.locator(
    "#chart-ethusdt-1h-slot-1 [aria-label='Latest Candle summary']",
  );
  const oneHourOpenTime =
    historyOpenTimes.get("ETHUSDT:1h") ?? "2026-08-13T09:00:00.000Z";
  const oneHourEventTime = new Date(
    Date.parse(oneHourOpenTime) + intervalFor("1h"),
  ).toISOString();
  const beforeStale = await oneHourSummary.textContent();
  sendCandle(selection("BTCUSDT", "1h"), "999.00", oneHourEventTime, 1);
  await expect(oneHourSummary).toHaveText(beforeStale ?? "");
  sendCandle(selection("ETHUSDT", "1h"), "205.00", oneHourEventTime, 2);
  await expect(oneHourSummary).toContainText("C 205.00");

  await dashboardPair.selectOption("SOLUSDT");
  await expect(page.locator("#chart-solusdt-1h-slot-1")).toBeVisible();
  await expect(page.locator("#chart-solusdt-5m-slot-2")).toBeVisible();
  await expect.poll(() => historyCount("SOLUSDT")).toBe(3);
  await expect.poll(
    () =>
      subscribeCommands().filter((command) => commandSelection(command)?.pair === "SOLUSDT")
        .length,
  ).toBe(3);
  const solSummary = page.locator(
    "#chart-solusdt-1h-slot-1 [aria-label='Latest Candle summary']",
  );
  const solOpenTime =
    historyOpenTimes.get("SOLUSDT:1h") ?? "2026-08-13T09:00:00.000Z";
  const solEventTime = new Date(
    Date.parse(solOpenTime) + intervalFor("1h"),
  ).toISOString();
  const solBeforeStale = await solSummary.textContent();
  sendCandle(selection("ETHUSDT", "1h"), "888.00", solEventTime, 3);
  await expect(solSummary).toHaveText(solBeforeStale ?? "");
  sendCandle(selection("SOLUSDT", "1h"), "305.00", solEventTime, 4);
  await expect(solSummary).toContainText("C 305.00");

  await dashboardPair.selectOption("BTCUSDT");
  await expect(page.locator("#chart-btcusdt-1h-slot-1")).toBeVisible();
  await expect(page.locator("#chart-btcusdt-5m-slot-2")).toBeVisible();
  await expect.poll(() => historyCount("BTCUSDT")).toBeGreaterThan(1);
  const btcSummary = page.locator(
    "#chart-btcusdt-1h-slot-1 [aria-label='Latest Candle summary']",
  );
  const btcOpenTime =
    historyOpenTimes.get("BTCUSDT:1h") ?? "2026-08-13T09:00:00.000Z";
  const btcEventTime = new Date(
    Date.parse(btcOpenTime) + intervalFor("1h"),
  ).toISOString();
  const btcBeforeStale = await btcSummary.textContent();
  sendCandle(
    selection("BTCUSDT", "1h"),
    "777.00",
    btcEventTime,
    5,
    firstBtcGenerations,
  );
  await expect(btcSummary).toHaveText(btcBeforeStale ?? "");
  sendCandle(selection("BTCUSDT", "1h"), "707.00", btcEventTime, 6);
  await expect(btcSummary).toContainText("C 707.00");
});
